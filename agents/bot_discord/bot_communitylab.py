"""
Bot de Discord de InsightEdu Lab (T05): responde en vivo pasando por la API Java.

    Discord ─► bot ─► Java (POST /api/v1/mensajes/en-vivo) ─► IA ─► Java ─► bot ─► Discord

- Escucha solo #dudas y #logros (S10). Ignora sus propios mensajes y los de otros bots,
  pero no los de nuestros webhooks: son los alumnos simulados (esSimulado = true).
- Arma el contrato v1 con transform.py de la ingesta, a partir del JSON crudo que entrega
  GET /channels/{canal}/messages/{id}: el mensaje en vivo y el del lote de la hora salen iguales (C2).
- No decide nada: cumple la orden de Java (DEC-68, docs/contratos/BOT_JAVA_v1.md).
  RESPONDER y DERIVAR responden al mensaje, con las menciones desactivadas (S8); REACCIONAR pone 🎉 (F5).
- Si Java o la IA fallan, no responde nada (DEC-67): el lote de la hora rescata el mensaje.
- En los registros, solo IDs, la orden y los tiempos: nunca el texto de un alumno (S11).

Uso (dentro de Docker lo arranca compose.yml):  python agents/bot_discord/bot_communitylab.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import aiohttp
import discord

# Los módulos de la ingesta se importan como sueltos ("from contract import …"): se usa su carpeta.
# En Docker se copian a la misma ruta relativa (agents/bot_discord/Dockerfile), sin duplicarlos en git.
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "ingestion" / "discord"))

from config import ConfigError, cargar_config  # noqa: E402
from discord_api import DiscordAPI  # noqa: E402
from transform import Contexto, a_contrato, armar_lote  # noqa: E402

log = logging.getLogger("bot")

RUTA_EN_VIVO = "/api/v1/mensajes/en-vivo"
# D4 y F8: modelo 20 s < Java → IA 30 s < bot → Java 40 s
TIEMPO_JAVA_S = 40
ORDENES = frozenset({"RESPONDER", "DERIVAR", "REACCIONAR", "NADA"})
MAX_CARACTERES_DISCORD = 2000
SIN_MENCIONES = discord.AllowedMentions.none()  # ni @everyone, ni roles, ni usuarios, ni al autor (S8)


class AjustesError(Exception):
    """Falta una variable obligatoria del bot."""


@dataclass(frozen=True)
class Ajustes:
    # repr=False: que un secreto no aparezca si alguien imprime los ajustes
    token: str = field(repr=False)
    api_key: str = field(repr=False)
    url_java: str
    # ID del canal → nombre en el contrato ("dudas" o "logros", igual que build_batch.py)
    canales: dict[str, str]
    webhooks_propios: frozenset[str] = frozenset()
    roles_mentor: frozenset[str] = frozenset()
    roles_staff: frozenset[str] = frozenset()
    mentores_simulados: frozenset[str] = frozenset()


def cargar_ajustes() -> Ajustes:
    """Las variables de la ingesta (mismos nombres, M3) más API_KEY_BOT y BOT_JAVA_URL."""
    try:
        config = cargar_config()
    except ConfigError as e:
        raise AjustesError(str(e)) from e
    faltan = [nombre for nombre, valor in (("DISCORD_CHANNEL_DUDAS_ID", config.canal_dudas_id),
                                           ("DISCORD_CHANNEL_LOGROS_ID", config.canal_logros_id),
                                           ("API_KEY_BOT", os.getenv("API_KEY_BOT", "").strip())) if not valor]
    if faltan:
        raise AjustesError(f"Faltan variables: {', '.join(faltan)}. Ver .env.example de la raíz.")
    return Ajustes(
        token=config.bot_token,
        api_key=os.getenv("API_KEY_BOT", "").strip(),
        url_java=os.getenv("BOT_JAVA_URL", "http://127.0.0.1:8008").strip().rstrip("/"),
        canales={config.canal_dudas_id: "dudas", config.canal_logros_id: "logros"},
        webhooks_propios=config.webhooks_propios,
        roles_mentor=config.roles_mentor,
        roles_staff=config.roles_staff,
        mentores_simulados=config.mentores_simulados,
    )


# ── Qué mensajes se procesan ────────────────────────────────────────────────


def debe_procesar(message, bot_user_id: int, ajustes: Ajustes) -> bool:
    """Solo #dudas y #logros. Fuera los propios y los de otros bots; dentro los de nuestros webhooks.
    Los mensajes sin texto sí se envían: Java los registra y la IA les pone OTRO por regla."""
    if message.guild is None or str(message.channel.id) not in ajustes.canales:
        return False
    if message.author.id == bot_user_id:
        return False
    if message.webhook_id is not None:
        return str(message.webhook_id) in ajustes.webhooks_propios
    return not message.author.bot


# ── El contrato v1, igual que la ingesta ────────────────────────────────────


def contexto_para(message, bot_user_id: int, ajustes: Ajustes) -> Contexto:
    """El mismo Contexto que arma build_batch.py, con lo que discord.py ya sabe del mensaje.

    📘 Por REST un mensaje no trae los roles del autor; discord.py sí los trae en message.author
    (un Member). Se quita @everyone, que la ingesta tampoco tiene (GET /guilds/{id}/members/{id}).
    """
    autor = message.author
    roles = [str(r.id) for r in getattr(autor, "roles", []) if not r.is_default()]
    rol_bot = message.guild.self_role  # el rol que Discord crea para el bot
    return Contexto(
        webhooks_propios=ajustes.webhooks_propios,
        bot_id=str(bot_user_id),
        rol_bot_id=str(rol_bot.id) if rol_bot else None,
        roles_por_autor={} if message.webhook_id is not None else {str(autor.id): roles},
        roles_mentor=ajustes.roles_mentor,
        roles_staff=ajustes.roles_staff,
        mentores_simulados=ajustes.mentores_simulados,
    )


def armar_lote_en_vivo(crudo: dict, canal_nombre: str, ctx: Contexto, servidor_id: str) -> dict:
    """Un lote del contrato v1, modo tiempoReal, con un solo mensaje. Igual que send_batch.py lo envía."""
    mensaje = a_contrato(crudo, canal_nombre, ctx)
    return armar_lote([mensaje], "tiempoReal", servidor_id).model_dump(mode="json")


def leer_crudo(token: str, canal_id: str, mensaje_id: str) -> dict:
    """📘 GET /channels/{canal}/messages/{id}: el mismo JSON que lee extract.py. Bloquea: correr en otro hilo."""
    with DiscordAPI(token) as api:
        return api.get(f"/channels/{canal_id}/messages/{mensaje_id}")


# ── Java ────────────────────────────────────────────────────────────────────


async def pedir_orden(sesion: aiohttp.ClientSession, ajustes: Ajustes, lote: dict) -> dict | None:
    """La orden de Java, o None si Java no respondió bien (DEC-67: entonces el bot no hace nada)."""
    discord_id = lote["mensajes"][0]["id"]
    try:
        async with sesion.post(
            ajustes.url_java + RUTA_EN_VIVO,
            json=lote,  # con json=, aiohttp envía Content-Length (Java lo exige, observación de T03)
            headers={"X-Api-Key": ajustes.api_key, "X-Id-Correlacion": lote["loteId"]},
            timeout=aiohttp.ClientTimeout(total=TIEMPO_JAVA_S),
        ) as respuesta:
            if respuesta.status != 200:
                log.warning("Mensaje %s: Java respondió HTTP %d (lote %s)", discord_id, respuesta.status, lote["loteId"])
                return None
            orden = await respuesta.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        log.warning("Mensaje %s: no se pudo hablar con Java (%s)", discord_id, type(e).__name__)
        return None
    if not isinstance(orden, dict) or orden.get("orden") not in ORDENES:
        log.warning("Mensaje %s: Java devolvió una orden desconocida", discord_id)
        return None
    return orden


async def cumplir(message, orden: dict) -> None:
    """Cumple la orden de Java. Responder al mensaje lo enlaza: en el contrato queda con respondeA."""
    tipo = orden["orden"]
    if tipo in ("RESPONDER", "DERIVAR") and orden.get("texto"):
        await message.reply(orden["texto"][:MAX_CARACTERES_DISCORD], allowed_mentions=SIN_MENCIONES,
                            mention_author=False)
    elif tipo == "REACCIONAR":
        await message.add_reaction(orden.get("reaccion") or "🎉")


async def atender(message, ajustes: Ajustes, bot_user_id: int, sesion: aiohttp.ClientSession,
                  leer=leer_crudo) -> str:
    """Todo el recorrido de un mensaje. Devuelve la orden que se cumplió ("NADA" si algo falló)."""
    inicio = time.perf_counter()
    canal_id = str(message.channel.id)
    # "Escribiendo…" mientras se espera a Java (F8)
    async with message.channel.typing():
        crudo = await asyncio.to_thread(leer, ajustes.token, canal_id, str(message.id))
        lote = armar_lote_en_vivo(crudo, ajustes.canales[canal_id], contexto_para(message, bot_user_id, ajustes),
                                  str(message.guild.id))
        orden = await pedir_orden(sesion, ajustes, lote)
    tipo = "NADA" if orden is None else orden["orden"]
    if orden is not None:
        await cumplir(message, orden)
    log.info("Mensaje %s (#%s, lote %s): orden %s%s · %d ms", message.id, ajustes.canales[canal_id], lote["loteId"],
             tipo, "" if orden is not None else " (falló Java; lo rescata el lote de la hora)",
             (time.perf_counter() - inicio) * 1000)
    return tipo


# ── El cliente de Discord ───────────────────────────────────────────────────


class BotCommunityLab(discord.Client):

    def __init__(self, ajustes: Ajustes):
        intents = discord.Intents.default()
        intents.message_content = True  # privilegiado: sin él, content llega vacío
        # Las menciones también se desactivan por defecto para todo lo que envíe el bot (S8)
        super().__init__(intents=intents, allowed_mentions=SIN_MENCIONES)
        self.ajustes = ajustes
        self.sesion: aiohttp.ClientSession | None = None

    async def setup_hook(self) -> None:
        self.sesion = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.sesion is not None:
            await self.sesion.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("Bot conectado (id %s). Escucha %s; Java en %s", self.user.id,
                 sorted(f"#{n}" for n in self.ajustes.canales.values()), self.ajustes.url_java)

    async def on_message(self, message: discord.Message) -> None:
        if not debe_procesar(message, self.user.id, self.ajustes):
            return
        try:
            await atender(message, self.ajustes, self.user.id, self.sesion)
        except Exception as e:  # noqa: BLE001
            # Solo el tipo de error: el detalle (por ejemplo, de pydantic) podría incluir el texto (S11)
            log.error("Mensaje %s: no se pudo atender (%s). Lo rescata el lote de la hora",
                      message.id, type(e).__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        ajustes = cargar_ajustes()
    except AjustesError as e:
        log.error("%s", e)
        return 1
    # log_handler=None: discord.py usa la configuración de logging de arriba
    BotCommunityLab(ajustes).run(ajustes.token, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
