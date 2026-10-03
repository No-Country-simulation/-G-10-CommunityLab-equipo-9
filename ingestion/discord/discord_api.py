"""
Cliente mínimo para la API REST de Discord.

Reúne lo que necesita toda petición: la dirección base, la autenticación del
bot, un tiempo máximo de espera y el respeto de los límites de velocidad
(rate limits) que impone Discord.
"""
import time
from datetime import datetime

import httpx

API_BASE = "https://discord.com/api/v10"
# 📘 Los IDs de Discord (snowflakes) guardan en sus bits 63 a 22 los milisegundos desde esta fecha (2015-01-01).
EPOCA_DISCORD_MS = 1420070400000
# Discord exige que los bots se identifiquen con este formato de User-Agent.
USER_AGENT = "DiscordBot (https://github.com/No-Country-simulation/-G-10-CommunityLab-equipo-9, 0.1.0)"
TIMEOUT_SEGUNDOS = 10.0
MAX_INTENTOS = 3


def snowflake_desde_fecha(fecha: datetime) -> int:
    """📘 Un ID "fabricado" para una fecha: sirve para pedir "los mensajes posteriores a tal día" con after."""
    return (int(fecha.timestamp() * 1000) - EPOCA_DISCORD_MS) << 22


class DiscordAPIError(Exception):
    """Discord respondió con un error que reintentar no resuelve."""

    def __init__(self, status: int, detalle: str):
        super().__init__(f"HTTP {status}: {detalle}")
        self.status = status


class DiscordAPI:
    """Uso:
        with DiscordAPI(token) as api:
            bot = api.get("/users/@me")

    Sin token sirve para los webhooks: su URL ya incluye su propia clave, así
    que no hace falta enviar el token del bot.
    """

    def __init__(self, bot_token: str | None = None):
        headers = {"User-Agent": USER_AGENT}
        if bot_token:
            headers["Authorization"] = f"Bot {bot_token}"
        self._http = httpx.Client(base_url=API_BASE, headers=headers, timeout=TIMEOUT_SEGUNDOS)

    def __enter__(self) -> "DiscordAPI":
        return self

    def __exit__(self, *_) -> None:
        self._http.close()

    def get(self, ruta: str, params: dict | None = None):
        """Hace un GET y devuelve el JSON de la respuesta."""
        return self._pedir("GET", ruta, params=params)

    def post(self, ruta: str, json: dict, params: dict | None = None):
        """Hace un POST con un cuerpo JSON y devuelve el JSON de la respuesta."""
        return self._pedir("POST", ruta, json=json, params=params)

    def _pedir(self, metodo: str, ruta: str, **opciones):
        """Envía la petición y aplica las reglas de reintento.

        - 429 (demasiadas peticiones): Discord no procesó la petición; espera lo
          que indica y reintenta.
        - 5xx (falla de Discord): reintenta solo los GET, esperando 2, 4… segundos.
          Un POST pudo guardarse antes del fallo y repetirlo lo duplicaría.
        - Otro error (401, 403, 404…): lanza DiscordAPIError sin reintentar.

        La ruta puede ser relativa a API_BASE ("/users/@me") o una URL completa,
        como la de un webhook.
        """
        for intento in range(1, MAX_INTENTOS + 1):
            respuesta = self._http.request(metodo, ruta, **opciones)

            if respuesta.status_code == 429:
                time.sleep(float(respuesta.headers.get("Retry-After", 1)))
                continue
            if respuesta.status_code >= 500 and metodo == "GET":
                time.sleep(2**intento)
                continue
            if respuesta.is_error:
                raise DiscordAPIError(respuesta.status_code, respuesta.text)

            # Si ya no quedan peticiones en esta ventana, espera antes de la siguiente.
            if respuesta.headers.get("X-RateLimit-Remaining") == "0":
                time.sleep(float(respuesta.headers.get("X-RateLimit-Reset-After", 0)))
            return respuesta.json() if respuesta.content else None

        raise DiscordAPIError(respuesta.status_code, f"falló tras {MAX_INTENTOS} intentos")
