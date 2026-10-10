"""
Configuración de la ingesta de Discord.

Lee los valores desde ingestion/discord/.env, que Git ignora, para que ningún
secreto quede escrito en el código.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DIAS_RELECTURA_POR_DEFECTO = 7


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
    # Roles de Discord que cuentan como mentor o staff (decisión 2 del contrato).
    roles_mentor: frozenset[str] = frozenset()
    roles_staff: frozenset[str] = frozenset()
    # Mentores simulados, por su autor.id ("sim-andres-mentor"): los webhooks no tienen roles.
    mentores_simulados: frozenset[str] = frozenset()
    # Puerta de backend que recibe los lotes. Sin ella, solo se puede usar send_batch.py --prueba.
    url_backend: str | None = None
    # Clave para la cabecera X-Api-Key de la API Java (S1). La genera scripts/generar_api_key.py.
    api_key_backend: str | None = field(default=None, repr=False)
    # Cuántos días hacia atrás se releen en cada extracción, para captar reacciones y ediciones.
    dias_relectura: int = DIAS_RELECTURA_POR_DEFECTO

    @property
    def webhooks_propios(self) -> frozenset[str]:
        """IDs de nuestros webhooks de simulación: un mensaje con uno de ellos es simulado."""
        urls = (self.webhook_dudas_url, self.webhook_logros_url)
        return frozenset(i for i in map(id_de_webhook, urls) if i)


def id_de_webhook(url: str | None) -> str | None:
    """Extrae el ID de una URL de webhook: https://discord.com/api/webhooks/<ID>/<clave>."""
    if not url:
        return None
    coincidencia = re.search(r"/webhooks/(\d+)/", url)
    return coincidencia.group(1) if coincidencia else None


def _leer(nombre: str) -> str | None:
    """Devuelve la variable sin espacios, o None si está vacía o no existe."""
    valor = os.getenv(nombre, "").strip()
    return valor or None


def _leer_lista(nombre: str) -> frozenset[str]:
    """Lee una variable con valores separados por comas: "a, b" → {"a", "b"}."""
    return frozenset(v.strip() for v in (_leer(nombre) or "").split(",") if v.strip())


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
        roles_mentor=_leer_lista("DISCORD_MENTOR_ROLE_IDS"),
        roles_staff=_leer_lista("DISCORD_STAFF_ROLE_IDS"),
        mentores_simulados=_leer_lista("SIMULATED_MENTORS"),
        url_backend=_leer("BACKEND_INGEST_URL"),
        api_key_backend=_leer("BACKEND_API_KEY"),
        dias_relectura=int(_leer("INGEST_REREAD_DAYS") or DIAS_RELECTURA_POR_DEFECTO),
    )
