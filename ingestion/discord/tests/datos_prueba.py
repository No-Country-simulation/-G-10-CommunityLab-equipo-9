"""
Mensajes de ejemplo para las pruebas, con la forma exacta que entrega Discord.

Los simulados copian la muestra de docs/DISCORD_DATA_GUIDE.md. La persona real
usa un ID inventado: las pruebas no dependen de data/ ni de datos personales.
"""
import copy

from transform import Contexto

WEBHOOK_DUDAS = "1554160711800717417"
WEBHOOK_AJENO = "999999999999999999"
CANAL_DUDAS = "1554158212742127821"
BOT_ID = "1554158872585965578"
ROL_BOT_ID = "1554160419470315653"
ROL_MENTOR_ID = "1555404352582189177"
ROL_STAFF_ID = "1555404352582189178"
PERSONA_REAL_ID = "111111111111111111"

_DUDA_SIMULADA = {
    "type": 0,
    "content": "como instalo pyhton en windows?? me sale que pip no se reconoce como comando 😭",
    "mentions": [],
    "mention_roles": [],
    "mention_everyone": False,
    "attachments": [],
    "embeds": [],
    "timestamp": "2026-09-28T18:56:30.331000+00:00",
    "edited_timestamp": None,
    "flags": 0,
    "components": [],
    "id": "1554205178671009863",
    "channel_id": CANAL_DUDAS,
    "author": {"id": WEBHOOK_DUDAS, "username": "Ana Pérez", "global_name": None, "bot": True, "discriminator": "0000"},
    "pinned": False,
    "tts": False,
    "webhook_id": WEBHOOK_DUDAS,
}

AUTOR_REAL = {"id": PERSONA_REAL_ID, "username": "persona.real", "global_name": "Persona Real", "discriminator": "0"}


def crudo(**cambios) -> dict:
    """La duda simulada de Ana, con los cambios indicados."""
    mensaje = copy.deepcopy(_DUDA_SIMULADA)
    mensaje.update(cambios)
    return mensaje


def crudo_real(**cambios) -> dict:
    """Un mensaje escrito por una persona real: sin webhook_id y sin author.bot."""
    cambios.setdefault("author", copy.deepcopy(AUTOR_REAL))
    mensaje = crudo(**cambios)
    del mensaje["webhook_id"]
    return mensaje


def contexto(**cambios) -> Contexto:
    datos = {
        "webhooks_propios": frozenset({WEBHOOK_DUDAS}),
        "bot_id": BOT_ID,
        "rol_bot_id": ROL_BOT_ID,
        "roles_por_autor": {PERSONA_REAL_ID: [ROL_MENTOR_ID]},
        "roles_mentor": frozenset({ROL_MENTOR_ID}),
        "roles_staff": frozenset({ROL_STAFF_ID}),
        "mentores_simulados": frozenset({"sim-andres-mentor"}),
    }
    datos.update(cambios)
    return Contexto(**datos)
