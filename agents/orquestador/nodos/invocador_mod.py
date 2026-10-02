"""
Nodo 3a: invocador del Agente-Mod.

Maneja TESTIMONIO y COMENTARIO. El Agente-Mod genera el post o el reporte
de clima según corresponda. Se carga dinámicamente vía importlib.
"""
from __future__ import annotations
import importlib
import time
from ..contratos import OutputSubAgente
from ..config import SUBAGENTE_MOD_PATH


def _cargar_agente_mod():
    """Carga dinámicamente el Agente-Mod."""
    modulo_path, clase_nombre = SUBAGENTE_MOD_PATH.rsplit(".", 1)
    modulo = importlib.import_module(modulo_path)
    return getattr(modulo, clase_nombre)


def _invocar_uno(mensaje: dict, clasificacion: dict) -> OutputSubAgente:
    """Invoca el Agente-Mod para un solo mensaje."""
    t0 = time.time()
    try:
        AgenteMod = _cargar_agente_mod()
        agente = AgenteMod()

        resultado = agente.procesar(
            mensaje=mensaje,
            intencion=clasificacion["intencion"],
        )

        # resultado esperado: dict con 'texto_respuesta', 'output', 'metadata', etc.
        return OutputSubAgente(
            mensaje_id=mensaje["mensaje_id"],
            intencion=clasificacion["intencion"],
            texto_respuesta=resultado.get("texto_respuesta", ""),
            output=resultado.get("output", {}),
            metadata={
                "tiempo_ms": int((time.time() - t0) * 1000),
                **resultado.get("metadata", {}),
            },
            status=resultado.get("status", "exito"),
            motivo_atencion=resultado.get("motivo_atencion"),
        )

    except Exception as e:
        return OutputSubAgente(
            mensaje_id=mensaje["mensaje_id"],
            intencion=clasificacion["intencion"],
            texto_respuesta="",
            output={},
            metadata={"tiempo_ms": int((time.time() - t0) * 1000)},
            status="atencion_humano",
            motivo_atencion=f"Error al invocar Agente-Mod: {e}",
        )


def invocar_mod_lote(
    mensajes: list[dict],
    clasificaciones: list[dict],
) -> list[OutputSubAgente]:
    """Invoca el Agente-Mod para cada mensaje de TESTIMONIO o COMENTARIO."""
    resultados: list[OutputSubAgente] = []
    for msg in mensajes:
        clas = next(
            (c for c in clasificaciones if c["mensaje_id"] == msg["mensaje_id"]),
            None,
        )
        if clas and clas["intencion"] in ("TESTIMONIO", "COMENTARIO"):
            resultados.append(_invocar_uno(msg, clas))
    return resultados