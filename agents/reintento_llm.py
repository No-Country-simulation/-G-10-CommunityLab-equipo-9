"""
Reintento ante un 503 o un 504 de Gemini en el camino en vivo de una duda (T14, DEC-170).

Lo usan el clasificador (orquestador) y el Agente FAQ (la respuesta y la revisión anti-alucinación). Envuelve al
modelo con su respaldo (DEC-165): un intento es el modelo principal y, si falla, el de respaldo, enseguida. Si los
dos dieron 503 o 504, espera un poco y vuelve a intentar, pero solo si el tiempo que queda del tope en vivo alcanza
para una llamada completa. Si no alcanza, se rinde y el bot deriva, como antes (D3).

- Solo en vivo: el orquestador marca la hora límite con `plazo_en_vivo(...)`. Sin ella (lotes de historial, la FAQ
  semanal) no reintenta nada y se comporta igual que el modelo envuelto. El Agente-Mod no lo usa.
- Nunca ante 400, 401, 403, 404 ni 429: no se arreglan reintentando, y un 429 gasta la cuota.
- El registro dice cuántos reintentos hubo y por qué código; nunca el texto de la duda.
"""
from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager

from langchain_core.runnables import Runnable

log = logging.getLogger("reintento")

# 503 UNAVAILABLE ("high demand") y 504 DEADLINE_EXCEEDED: Google no procesó el pedido y puede responder enseguida
CODIGOS_PASAJEROS = frozenset({503, 504})
ESPERA_S = 1.5
REINTENTOS_MAX = 2

# La hora límite (time.perf_counter) del pedido en vivo. None fuera del camino en vivo
_plazo: contextvars.ContextVar[float | None] = contextvars.ContextVar("plazo_en_vivo", default=None)


@contextmanager
def plazo_en_vivo(plazo: float | None):
    """Mientras dura el bloque, los modelos envueltos pueden reintentar hasta esta hora límite."""
    token = _plazo.set(plazo)
    try:
        yield
    finally:
        _plazo.reset(token)


def codigo_pasajero(error: BaseException) -> int | None:
    """503 o 504 si Google respondió eso (LangChain lo deja en .code, o en la causa); si no, None."""
    for e in (error, error.__cause__):
        codigo = getattr(e, "code", None)
        if isinstance(codigo, int) and codigo in CODIGOS_PASAJEROS:
            return codigo
    return None


class ReintentoEnVivo(Runnable):
    """El modelo (con su respaldo) más el reintento ante un 503 o un 504, mientras quede tiempo del tope en vivo.

    tiempo_llamada_s: lo que puede tardar una llamada (su tiempo máximo); hace falta tenerlo libre para reintentar.
    with_structured_output y bind_tools se aplican al modelo envuelto y el resultado sigue con reintento.
    """

    def __init__(self, envuelto: Runnable, tiempo_llamada_s: float, espera_s: float = ESPERA_S,
                 reintentos: int = REINTENTOS_MAX, reloj=time.perf_counter, dormir=time.sleep):
        self.envuelto = envuelto
        self.tiempo_llamada_s = tiempo_llamada_s
        self.espera_s = espera_s
        self.reintentos = reintentos
        self.reloj = reloj
        self.dormir = dormir

    def invoke(self, entrada, config=None, **kwargs):
        hechos = 0
        while True:
            try:
                return self.envuelto.invoke(entrada, config, **kwargs)
            except Exception as e:
                codigo = codigo_pasajero(e)
                plazo = _plazo.get()
                if codigo is None or plazo is None or hechos >= self.reintentos:
                    raise
                restante = plazo - self.reloj()
                if restante < self.espera_s + self.tiempo_llamada_s:
                    log.warning("Gemini respondió %d y quedan %.1f s del tope: no alcanza para reintentar",
                                codigo, restante)
                    raise
                hechos += 1
                log.warning("Gemini respondió %d: reintento %d de %d en %.1f s", codigo, hechos, self.reintentos,
                            self.espera_s)
                self.dormir(self.espera_s)

    def _con(self, envuelto: Runnable) -> "ReintentoEnVivo":
        return ReintentoEnVivo(envuelto, self.tiempo_llamada_s, self.espera_s, self.reintentos, self.reloj,
                               self.dormir)

    def with_structured_output(self, *args, **kwargs) -> Runnable:
        return self._con(self.envuelto.with_structured_output(*args, **kwargs))

    def bind_tools(self, *args, **kwargs) -> Runnable:
        return self._con(self.envuelto.bind_tools(*args, **kwargs))
