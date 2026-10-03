"""
Grafo LangGraph de POST /v1/procesar (contrato Java ↔ IA v1).

    preparar ──► clasificar ──┬─► responder_faq ──► fin   (solo tiempoReal y si hay PREGUNTA_FAQ)
                              └─► fin

- preparar: los mensajes de bots, avisos del sistema o sin texto no van al LLM.
- clasificar: una llamada al LLM por mensaje; si falla, estado ERROR (F4).
- responder_faq: el Agente FAQ responde las dudas solo en tiempoReal (en historial no se gasta).
No invoca al Agente-Mod (fase 4) ni sube nada a OCI (D2: los activos los sube Java).
"""
from __future__ import annotations

import logging
import time
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

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


class EstadoV1(TypedDict, total=False):
    lote: Lote
    pendientes: list[MensajeContrato]          # los que van al LLM
    resultados: dict[str, ResultadoMensaje]     # por discord_id
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
        fuentes=[fuente] if fuente else [],
        motivo=buscador.get("motivo_fallo"),
    )


class ProcesadorV1:
    """Arma el grafo una sola vez; procesar() se puede llamar desde varios hilos a la vez."""

    def __init__(self, etiquetador, responder_faq: ResponderFaq = responder_con_agente_faq):
        self.etiquetador = etiquetador
        self.responder_faq = responder_faq
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
            etiquetado = self.etiquetador.etiquetar(m)
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
                resultados[m.id] = r.model_copy(update={"respuesta": self.responder_faq(m)})
        return {"resultados": resultados}

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
        final = self.grafo.invoke({"lote": lote})
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
