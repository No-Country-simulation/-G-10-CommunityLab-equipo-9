"""
Configuración de la ingesta de Discord.

Lee los valores desde ingestion/discord/.env, que Git ignora, para que ningún
secreto quede escrito en el código.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class ConfigError(Exception):
    """Falta una variable obligatoria en el .env."""


@dataclass(frozen=True)
class Config:
    # repr=False evita que un secreto aparezca si alguien imprime la configuración.
    bot_token: str = field(repr=False)
    guild_id: str | None
    canal_dudas_id: str | None
    canal_logros_id: str | None
    webhook_dudas_url: str | None = field(repr=False)
    webhook_logros_url: str | None = field(repr=False)


def _leer(nombre: str) -> str | None:
    """Devuelve la variable sin espacios, o None si está vacía o no existe."""
    valor = os.getenv(nombre, "").strip()
    return valor or None


def cargar_config() -> Config:
    token = _leer("DISCORD_BOT_TOKEN")
    if token is None:
        raise ConfigError(
            "Falta DISCORD_BOT_TOKEN. Copia .env.example como .env "
            "y pega el token del bot."
        )
    return Config(
        bot_token=token,
        guild_id=_leer("DISCORD_GUILD_ID"),
        canal_dudas_id=_leer("DISCORD_CHANNEL_DUDAS_ID"),
        canal_logros_id=_leer("DISCORD_CHANNEL_LOGROS_ID"),
        webhook_dudas_url=_leer("DISCORD_WEBHOOK_DUDAS_URL"),
        webhook_logros_url=_leer("DISCORD_WEBHOOK_LOGROS_URL"),
    )
