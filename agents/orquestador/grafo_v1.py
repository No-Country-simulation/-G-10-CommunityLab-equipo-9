"""
Grafo LangGraph de POST /v1/procesar (contrato Java ↔ IA v1).

    preparar ──► clasificar ──┬─► responder_faq ──► fin   (solo tiempoReal y si hay PREGUNTA_FAQ)
                              └─► fin

- preparar: los mensajes de bots, avisos del sistema o sin texto no van al LLM.
- clasificar: una llamada al LLM por mensaje; si falla, estado ERROR (F4).
- responder_faq: el Agente FAQ responde las dudas solo en tiempoReal (en historial no se gasta).
En tiempoReal todo el pedido tiene un tope (DEC-54, TIEMPO_REAL_TOPE_S): clasificar y responder comparten
ese tiempo. Si se agota, la duda llega con sus etiquetas y respuesta.encontrada = false.
No invoca al Agente-Mod (fase 4) ni sube nada a OCI (D2: los activos los sube Java).
"""
from __future__ import annotations

import concurrent.futures
import logging
import re
import time
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import TIEMPO_REAL_TOPE_S
from .contrato_ia import (
    VERSION_CONTRATO_IA,
    Lote,
    MensajeContrato,
    Metricas,
    RespuestaFaq,
    RespuestaLote,
    ResultadoMensaje,
)

log = logging.getLogger(__name__)

ResponderFaq = Callable[[MensajeContrato], RespuestaFaq]

# Hilos para cortar al Agente FAQ cuando se agota el tope. Python no puede detener un hilo: el Agente FAQ
# termina su trabajo en segundo plano, pero su respuesta llega tarde y se descarta.
_ejecutor_faq = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="faq")


class EstadoV1(TypedDict, total=False):
    lote: Lote
    pendientes: list[MensajeContrato]          # los que van al LLM
    resultados: dict[str, ResultadoMensaje]     # por discord_id
    plazo: float | None                         # hora límite (time.perf_counter) en tiempoReal; None = sin tope
    tokens_in: int
    tokens_out: int


def motivo_para_no_clasificar(mensaje: MensajeContrato) -> str | None:
    """Reglas que no gastan el LLM. None si el mensaje hay que clasificarlo."""
    if mensaje.autor.tipo != "persona":
        return f"No se clasifica: el autor es {mensaje.autor.tipo}."
    if mensaje.tipo == "avisoSistema":
        return "No se clasifica: es un aviso del sistema."
    if not mensaje.texto_original.strip():
        return "No se clasifica: el mensaje no tiene texto."
    return None


def sin_carpetas(fuente: str) -> str:
    """Solo el nombre del archivo y la página, aunque la ruta use "/" o "\\" (T05).
    Ejemplo: una ruta de Windows que termina en ...\\pdfs\\Manual.pdf (Pág. 1) → 'Manual.pdf (Pág. 1)'.
    Nunca se publica ni se guarda la ruta de la PC donde se armó el índice."""
    return re.split(r"[\\/]", fuente)[-1].strip()


def responder_con_agente_faq(mensaje: MensajeContrato) -> RespuestaFaq:
    """Pregunta al Agente FAQ (la instancia compartida que precarga la API)."""
    from .nodos.invocador_faq import _obtener_agente_faq

    try:
        resultado = _obtener_agente_faq().responder(
            pregunta=mensaje.texto_original,
            metadata={"canal_origen": mensaje.canal.id, "autor": mensaje.autor.id},
        )
    except Exception as e:
        log.warning("El Agente FAQ falló con el mensaje %s: %r", mensaje.id, e)
        return RespuestaFaq(texto="", encontrada=False, fuentes=[], motivo=f"El Agente FAQ falló: {type(e).__name__}.")

    buscador = resultado.get("respuesta_agente") or {}
    revision = bool(buscador.get("revision_recomendada"))
    fuente = buscador.get("fuente")
    return RespuestaFaq(
        texto=buscador.get("respuesta", "") or "",
        # D3: con fidelidad media no se publica; lo ve un mentor
        encontrada=bool(buscador.get("encontrado")) and not revision,
        fuentes=[sin_carpetas(fuente)] if fuente else [],
        motivo=buscador.get("motivo_fallo"),
    )


class ProcesadorV1:
    """Arma el grafo una sola vez; procesar() se puede llamar desde varios hilos a la vez."""

    def __init__(self, etiquetador, responder_faq: ResponderFaq = responder_con_agente_faq,
                 tope_tiempo_real_s: float = TIEMPO_REAL_TOPE_S):
        self.etiquetador = etiquetador
        self.responder_faq = responder_faq
        self.tope_tiempo_real_s = tope_tiempo_real_s
        self.grafo = self._construir()

    # ── Nodos ──

    def _preparar(self, estado: EstadoV1) -> dict:
        resultados: dict[str, ResultadoMensaje] = {}
        pendientes: list[MensajeContrato] = []
        for m in estado["lote"].mensajes:
            motivo = motivo_para_no_clasificar(m)
            if motivo:
                resultados[m.id] = ResultadoMensaje(
                    discord_id=m.id, estado="OK", metodo="regla",
                    intencion="OTRO", confianza=1.0, razon=motivo,
                )
            else:
                pendientes.append(m)
        return {"pendientes": pendientes, "resultados": resultados, "tokens_in": 0, "tokens_out": 0}

    def _clasificar(self, estado: EstadoV1) -> dict:
        resultados = dict(estado["resultados"])
        tokens_in, tokens_out = estado["tokens_in"], estado["tokens_out"]
        for m in estado["pendientes"]:
            etiquetado = self.etiquetador.etiquetar(m, plazo=estado.get("plazo"))
            tokens_in += etiquetado.tokens_in
            tokens_out += etiquetado.tokens_out
            if etiquetado.etiquetas is None:
                resultados[m.id] = ResultadoMensaje(
                    discord_id=m.id, estado="ERROR", metodo=self.etiquetador.metodo, razon=etiquetado.error,
                )
                continue
            e = etiquetado.etiquetas
            resultados[m.id] = ResultadoMensaje(
                discord_id=m.id, estado="OK", metodo=self.etiquetador.metodo,
                intencion=e.intencion, confianza=e.confianza, sentimiento=e.sentimiento, tema=e.tema, razon=e.razon,
            )
        return {"resultados": resultados, "tokens_in": tokens_in, "tokens_out": tokens_out}

    def _responder_faq(self, estado: EstadoV1) -> dict:
        resultados = dict(estado["resultados"])
        for m in estado["lote"].mensajes:
            r = resultados[m.id]
            if _es_duda(r):
                resultados[m.id] = r.model_copy(update={"respuesta": self._responder_a_tiempo(m, estado.get("plazo"))})
        return {"resultados": resultados}

    def _responder_a_tiempo(self, mensaje: MensajeContrato, plazo: float | None) -> RespuestaFaq:
        """El Agente FAQ, con lo que queda del tope. Si no alcanza, encontrada = false: el bot deriva (D3)."""
        if plazo is None:
            return self.responder_faq(mensaje)
        restante = plazo - time.perf_counter()
        if restante > 0:
            futuro = _ejecutor_faq.submit(self.responder_faq, mensaje)
            try:
                return futuro.result(timeout=restante)
            except concurrent.futures.TimeoutError:
                futuro.cancel()
        log.warning("Mensaje %s: se agotó el tope de %g s antes de la respuesta del Agente FAQ",
                    mensaje.id, self.tope_tiempo_real_s)
        return RespuestaFaq(texto="", encontrada=False, fuentes=[],
                            motivo=f"Se agotó el tope de {self.tope_tiempo_real_s:g} s del pedido en tiempo real.")

    # ── Arista condicional ──

    @staticmethod
    def _siguiente(estado: EstadoV1) -> str:
        hay_dudas = any(_es_duda(r) for r in estado["resultados"].values())
        return "responder_faq" if estado["lote"].modo == "tiempoReal" and hay_dudas else END

    def _construir(self):
        grafo = StateGraph(EstadoV1)
        grafo.add_node("preparar", self._preparar)
        grafo.add_node("clasificar", self._clasificar)
        grafo.add_node("responder_faq", self._responder_faq)
        grafo.add_edge(START, "preparar")
        grafo.add_edge("preparar", "clasificar")
        grafo.add_conditional_edges("clasificar", self._siguiente, ["responder_faq", END])
        grafo.add_edge("responder_faq", END)
        return grafo.compile()

    def procesar(self, lote: Lote) -> RespuestaLote:
        t0 = time.perf_counter()
        con_tope = lote.modo == "tiempoReal" and self.tope_tiempo_real_s > 0
        final = self.grafo.invoke({"lote": lote, "plazo": t0 + self.tope_tiempo_real_s if con_tope else None})
        return RespuestaLote(
            version_contrato_ia=VERSION_CONTRATO_IA,
            lote_id=lote.lote_id,
            # Mismo orden que el lote, uno por mensaje
            resultados=[final["resultados"][m.id] for m in lote.mensajes],
            metricas=Metricas(
                duracion_ms=int((time.perf_counter() - t0) * 1000),
                tokens_in=final["tokens_in"],
                tokens_out=final["tokens_out"],
            ),
        )


def _es_duda(r: ResultadoMensaje) -> bool:
    return r.estado == "OK" and r.metodo != "regla" and r.intencion == "PREGUNTA_FAQ"
