"""
Nodo 1: filtro de ruido.

Descarta bots, comandos y mensajes vacíos antes de gastar tokens en el LLM.
"""
from __future__ import annotations
import re
from ..config import MIN_LONGITUD_CONTENIDO, PATRON_COMANDOS


def filtrar_mensajes(
    mensajes: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Separa mensajes válidos de descartados.

    Returns:
        (validos, descartados) donde cada descartado tiene 'motivo_descarte'.
    """
    validos: list[dict] = []
    descartados: list[dict] = []
    patron_cmd = re.compile(PATRON_COMANDOS)

    for msg in mensajes:
        # Filtro 1: bots
        if msg.get("es_bot", False):
            descartados.append({**msg, "motivo_descarte": "es_bot"})
            continue

        contenido = msg.get("contenido", "").strip()

        # Filtro 2: vacío o muy corto
        if len(contenido) < MIN_LONGITUD_CONTENIDO:
            descartados.append({**msg, "motivo_descarte": "contenido_vacio"})
            continue

        # Filtro 3: comandos de Discord
        if patron_cmd.match(contenido):
            descartados.append({**msg, "motivo_descarte": "comando"})
            continue

        validos.append(msg)

    return validos, descartados