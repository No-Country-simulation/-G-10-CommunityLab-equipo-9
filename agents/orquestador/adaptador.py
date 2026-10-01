"""
Adaptador: Webhook crudo de Discord → InputOrquestador normalizado.

El webhook de Discord llega con TODOS los campos crudos (avatar, flags,
clan, etc.). Este módulo filtra solo lo esencial y genera un lote_id
si no viene en el payload.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from uuid import uuid4

from .contratos import InputOrquestador, MensajeNormalizado



# -- PATRONES DE LIMPIEZA ---

PATRON_MENCION = re.compile(r"<@!?\d+>")
PATRON_EMOJI_CUSTOM = re.compile(r"<a?:\w+:\d+>")


def generar_lote_id() -> str:
    """Genera un ID único para el lote basado en timestamp + uuid corto."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    sufijo = uuid4().hex[:6]
    return f"lote_{timestamp}_{sufijo}"


def limpiar_contenido(texto: str) -> str:
    """Elimina menciones y emojis custom de Discord."""
    texto = PATRON_MENCION.sub("", texto)
    texto = PATRON_EMOJI_CUSTOM.sub("", texto)
    return texto.strip()


def filtrar_mensaje_crudo(mensaje: dict) -> dict:
    """
    Extrae solo los campos relevantes del webhook crudo de Discord.

    Descarta: avatar, banner, flags, clan, global_name, discriminator, etc.
    """
    author = mensaje.get("author", {}) or {}
    return {
        "mensaje_id": str(mensaje.get("id", "")),
        "autor_id": str(author.get("id", "")),
        "autor_username": str(author.get("username", "desconocido")),
        "channel_id": str(mensaje.get("channel_id", "")),
        "contenido": limpiar_contenido(mensaje.get("content", "")),
        "timestamp": str(mensaje.get("timestamp", "")),
        "es_bot": bool(author.get("bot", False)),
    }


def _detectar_mensajes_crudos(payload: dict) -> list[dict]:
    """
    Detecta el formato del payload y devuelve la lista de mensajes crudos.

    Soporta:
    - 1 mensaje individual (tiene 'id' y 'author').
    - Lote con clave 'mensajes'.
    - Lote directo (lista).
    """
    if isinstance(payload, list):
        return payload

    if "mensajes" in payload and isinstance(payload["mensajes"], list):
        return payload["mensajes"]

    if "id" in payload and "author" in payload:
        return [payload]

    return []


def adaptar_webhook(payload: dict | list) -> InputOrquestador:
    """
    Convierte el payload crudo de Discord al contrato del Orquestador.

    Args:
        payload: dict o list con 1 o varios mensajes crudos de Discord.

    Returns:
        InputOrquestador listo para el grafo.
    """
    mensajes_crudos = _detectar_mensajes_crudos(payload)
    mensajes_normalizados = [
        MensajeNormalizado(**filtrar_mensaje_crudo(m))
        for m in mensajes_crudos
    ]

    # Extraer metadata del payload si viene
    origen = "discord"
    servidor = "Discord_ONE_G10"
    lote_id = None

    if isinstance(payload, dict):
        origen = payload.get("origen", origen)
        servidor = payload.get("servidor", servidor)
        lote_id = payload.get("lote_id")

    return InputOrquestador(
        lote_id=lote_id or generar_lote_id(),
        origen=origen,
        servidor=servidor,
        mensajes=mensajes_normalizados,
    )