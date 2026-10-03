"""
Servicio FastAPI del Orquestador.

Expone el endpoint POST /procesar que n8n consume.
"""
from __future__ import annotations
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from .adaptador import adaptar_webhook
from .orquestador import Orquestador
from .config_http import ENDPOINT_PROCESAR, ENDPOINT_HEALTH, HTTP_PORT
from .nodos.invocador_faq import precargar_agente_faq, agente_faq_listo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Precarga el Agente FAQ en segundo plano (~16 s): el servicio atiende /health
    # mientras tanto y la primera pregunta ya no espera la carga de modelos.
    threading.Thread(target=precargar_agente_faq, daemon=True).start()
    yield


app = FastAPI(
    title="InsightEdu Lab — Orquestador",
    description="Motor inteligente de transformación y distribución para comunidades digitales.",
    version="1.0.0",
    lifespan=lifespan,
)

# Instancia única del Orquestador (compartida entre requests)
_orquestador: Orquestador | None = None


def _get_orquestador() -> Orquestador:
    """Lazy initialization del Orquestador."""
    global _orquestador
    if _orquestador is None:
        print("[API] Inicializando Orquestador...")
        _orquestador = Orquestador()
        print("[API] Orquestador listo.")
    return _orquestador



# --- ENDPOINTS ---
@app.get(ENDPOINT_HEALTH)
async def health():
    """Endpoint de salud."""
    return {"status": "ok", "service": "orquestador", "port": HTTP_PORT, "faq_listo": agente_faq_listo()}


@app.post(ENDPOINT_PROCESAR)
async def procesar(request: Request):
    """
    Procesa un lote de mensajes de Discord.

    Recibe el webhook crudo de Discord y devuelve:
    - respuesta_discord: respuestas listas para enviar a Discord.
    - paquete_final: auditoría interna.
    - log_ejecucion: métricas y trazabilidad.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {e}")

    if not payload:
        raise HTTPException(status_code=400, detail="Payload vacío.")

    try:
        # Adaptar webhook crudo → InputOrquestador
        input_orq = adaptar_webhook(payload)

        if not input_orq.mensajes:
            raise HTTPException(
                status_code=400,
                detail="No se detectaron mensajes válidos en el payload.",
            )

        # Procesar en un hilo aparte: procesar_lote espera al LLM y, si corriera
        # aquí, bloquearía el servidor y ningún otro pedido (ni /health) se atendería.
        orquestador = _get_orquestador()
        output = await run_in_threadpool(orquestador.procesar_lote, input_orq)

        return JSONResponse(content=output.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")



# --- PUNTO DE ENTRADA (dev) ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agents.orquestador.api:app",
        host="0.0.0.0",
        port=HTTP_PORT,
        reload=True,
    )