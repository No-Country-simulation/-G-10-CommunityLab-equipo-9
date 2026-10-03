"""
Servicio FastAPI del Orquestador.

Expone el endpoint POST /procesar que n8n consume.
"""
from __future__ import annotations
import logging
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .adaptador import adaptar_webhook
from .orquestador import Orquestador
from .config_http import ENDPOINT_PROCESAR, ENDPOINT_PROCESAR_V1, ENDPOINT_HEALTH, HTTP_PORT
from .contrato_ia import ErrorApi, ErrorCampo, Lote, RespuestaLote
from .nodos.invocador_faq import precargar_agente_faq, agente_faq_listo

log = logging.getLogger(__name__)


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


# Procesador de /v1/procesar: se crea una sola vez, con el primer pedido
_procesador_v1 = None
_lock_procesador_v1 = threading.Lock()


def _get_procesador_v1():
    global _procesador_v1
    if _procesador_v1 is None:
        with _lock_procesador_v1:
            if _procesador_v1 is None:
                from .clasificadores.etiquetador import construir_etiquetador
                from .grafo_v1 import ProcesadorV1
                _procesador_v1 = ProcesadorV1(construir_etiquetador())
    return _procesador_v1


def _respuesta_error(status: int, error: ErrorApi) -> JSONResponse:
    return JSONResponse(status_code=status, content=error.model_dump())


@app.exception_handler(RequestValidationError)
async def contrato_invalido(request: Request, exc: RequestValidationError):
    """422 claro para /v1/procesar, sin repetir los datos recibidos (S7)."""
    errores = [
        ErrorCampo(
            campo=".".join(str(p) for p in err.get("loc", ()) if p != "body") or "(cuerpo)",
            problema=err.get("msg", "valor inválido"),
        )
        for err in exc.errors()
    ]
    return _respuesta_error(422, ErrorApi(
        codigo="CONTRATO_INVALIDO",
        mensaje="El lote no cumple el contrato v1.",
        errores=errores,
        id_correlacion=request.headers.get("X-Id-Correlacion") or str(uuid.uuid4()),
    ))



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


@app.post(
    ENDPOINT_PROCESAR_V1,
    response_model=RespuestaLote,
    responses={422: {"model": ErrorApi}, 500: {"model": ErrorApi}},
)
def procesar_v1(lote: Lote, x_id_correlacion: str | None = Header(default=None)):
    """
    Contrato Java ↔ IA v1: recibe un lote del contrato v1 y devuelve las etiquetas de cada mensaje.
    En modo tiempoReal, además, la respuesta del Agente FAQ a las dudas.

    Es `def` (no `async def`): FastAPI la corre en otro hilo y la espera al LLM no bloquea el servidor (F6).
    """
    try:
        return _get_procesador_v1().procesar(lote)
    except Exception:
        log.exception("Error interno en /v1/procesar (lote %s)", lote.lote_id)
        return _respuesta_error(500, ErrorApi(
            codigo="ERROR_INTERNO",
            mensaje="La IA no pudo procesar el lote. Reintentar más tarde.",
            id_correlacion=x_id_correlacion or str(uuid.uuid4()),
        ))



# --- PUNTO DE ENTRADA (dev) ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agents.orquestador.api:app",
        host="0.0.0.0",
        port=HTTP_PORT,
        reload=True,
    )