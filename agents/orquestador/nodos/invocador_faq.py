"""
Nodo 3b: invocador del Agente FAQ.

Maneja PREGUNTA_FAQ. Se carga dinámicamente vía importlib.
"""
from __future__ import annotations
import importlib
import time

from ..contratos import OutputSubAgente
from ..config import ORQ_SUBAGENTE_FAQ_PATH



def _cargar_agente_faq():
    """Carga dinámicamente el Agente FAQ."""
    modulo_path, clase_nombre = ORQ_SUBAGENTE_FAQ_PATH.rsplit(".", 1)
    modulo = importlib.import_module(modulo_path)
    return getattr(modulo, clase_nombre)


def _invocar_uno(mensaje: dict, clasificacion: dict) -> OutputSubAgente:
    """Invoca el Agente FAQ para un solo mensaje."""
    t0 = time.time()
    try:
        AgenteFAQ = _cargar_agente_faq()
        agente = AgenteFAQ()

        resultado = agente.responder(
            pregunta=mensaje["contenido"],
            metadata={
                "lote_id": mensaje.get("lote_id"),
                "autor": mensaje.get("autor_username"),
                "canal_origen": mensaje.get("channel_id"),
            },
        )

        # El Agente FAQ devuelve: {pregunta, respuesta_agente (dict), reporte (dict), metadata}
        respuesta_agente = resultado.get("respuesta_agente", {})
        reporte = resultado.get("reporte", {})

        # Extraer texto_respuesta desde el dict del BuscadorTool
        if isinstance(respuesta_agente, dict):
            texto = respuesta_agente.get("respuesta", "")
            encontrado = respuesta_agente.get("encontrado", False)
        elif isinstance(respuesta_agente, str):
            texto = respuesta_agente
            encontrado = True
        else:
            texto = ""
            encontrado = False

        return OutputSubAgente(
            mensaje_id=mensaje["mensaje_id"],
            intencion="PREGUNTA_FAQ",
            texto_respuesta=texto,
            output={
                "respuesta_agente": respuesta_agente,
                "reporte": reporte,
            },
            metadata={
                "tiempo_ms": int((time.time() - t0) * 1000),
                "encontrado": encontrado,
            },
            status="exito" if encontrado else "atencion_humano",
            motivo_atencion=None if encontrado else "FAQ sin contexto suficiente.",
        )

    except Exception as e:
        return OutputSubAgente(
            mensaje_id=mensaje["mensaje_id"],
            intencion="PREGUNTA_FAQ",
            texto_respuesta="",
            output={},
            metadata={"tiempo_ms": int((time.time() - t0) * 1000)},
            status="atencion_humano",
            motivo_atencion=f"Error al invocar Agente FAQ: {e}",
        )


def invocar_faq_lote(
    mensajes: list[dict],
    clasificaciones: list[dict],
) -> list[OutputSubAgente]:
    """Invoca el Agente FAQ para cada mensaje de PREGUNTA_FAQ."""
    resultados: list[OutputSubAgente] = []
    for msg in mensajes:
        clas = next(
            (c for c in clasificaciones if c["mensaje_id"] == msg["mensaje_id"]),
            None,
        )
        if clas and clas["intencion"] == "PREGUNTA_FAQ":
            resultados.append(_invocar_uno(msg, clas))
    return resultados