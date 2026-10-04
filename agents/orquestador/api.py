"""
Servicio FastAPI de la IA.

Expone POST /v1/procesar (contrato Java ↔ IA v1, docs/contratos/JAVA_IA_v1.md) y GET /health.
La puerta vieja POST /procesar, que usaba el bot directo, se quitó en T05: ahora el bot pasa por Java (C2).
"""
from __future__ import annotations
import hashlib
import hmac
import logging
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import config as config_orq
from .config_http import ENDPOINT_PROCESAR_V1, ENDPOINT_HEALTH, HTTP_PORT
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


def _clave_valida(recibida: str | None) -> bool:
    """S2: compara huellas SHA-256 con compare_digest, que tarda lo mismo acierte o no."""
    esperada = config_orq.API_KEY_IA
    if not esperada or not recibida:
        return False
    return hmac.compare_digest(
        hashlib.sha256(recibida.strip().encode("utf-8")).digest(),
        hashlib.sha256(esperada.encode("utf-8")).digest(),
    )


@app.middleware("http")
async def exigir_api_key(request: Request, call_next):
    """
    S2: toda ruta /v1/… exige X-Api-Key (la que envía Java). Corre antes que todo lo demás,
    así un pedido sin clave no llega ni a leer el cuerpo. /health no pide clave (lo usa Docker).
    La clave nunca se escribe en el registro.
    """
    if request.url.path.startswith("/v1/") and not _clave_valida(request.headers.get("X-Api-Key")):
        log.warning("Pedido rechazado sin API key válida: %s %s", request.method, request.url.path)
        return _respuesta_error(401, ErrorApi(
            codigo="NO_AUTORIZADO",
            mensaje="Falta la cabecera X-Api-Key o la clave no es válida.",
            id_correlacion=request.headers.get("X-Id-Correlacion") or str(uuid.uuid4()),
        ))
    return await call_next(request)


if not config_orq.API_KEY_IA:
    log.warning("API_KEY_IA está vacía: /v1/procesar rechazará todos los pedidos con 401.")


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