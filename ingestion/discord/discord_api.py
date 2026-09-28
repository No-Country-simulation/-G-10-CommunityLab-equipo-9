"""
Cliente mínimo para la API REST de Discord.

Reúne lo que necesita toda petición: la dirección base, la autenticación del
bot, un tiempo máximo de espera y el respeto de los límites de velocidad
(rate limits) que impone Discord.
"""
import time

import httpx

API_BASE = "https://discord.com/api/v10"
# Discord exige que los bots se identifiquen con este formato de User-Agent.
USER_AGENT = "DiscordBot (https://github.com/No-Country-simulation/-G-10-CommunityLab-equipo-9, 0.1.0)"
TIMEOUT_SEGUNDOS = 10.0
MAX_INTENTOS = 3


class DiscordAPIError(Exception):
    """Discord respondió con un error que reintentar no resuelve."""

    def __init__(self, status: int, detalle: str):
        super().__init__(f"HTTP {status}: {detalle}")
        self.status = status


class DiscordAPI:
    """Uso:
        with DiscordAPI(token) as api:
            bot = api.get("/users/@me")
    """

    def __init__(self, bot_token: str):
        self._http = httpx.Client(
            base_url=API_BASE,
            headers={"Authorization": f"Bot {bot_token}", "User-Agent": USER_AGENT},
            timeout=TIMEOUT_SEGUNDOS,
        )

    def __enter__(self) -> "DiscordAPI":
        return self

    def __exit__(self, *_) -> None:
        self._http.close()

    def get(self, ruta: str, params: dict | None = None):
        """Hace un GET y devuelve el JSON de la respuesta.

        - 429 (demasiadas peticiones): espera lo que indica Discord y reintenta.
        - 5xx (falla de Discord): espera 2, 4… segundos y reintenta.
        - Otro error (401, 403, 404…): lanza DiscordAPIError sin reintentar.
        """
        for intento in range(1, MAX_INTENTOS + 1):
            respuesta = self._http.get(ruta, params=params)

            if respuesta.status_code == 429:
                time.sleep(float(respuesta.headers.get("Retry-After", 1)))
                continue
            if respuesta.status_code >= 500:
                time.sleep(2**intento)
                continue
            if respuesta.is_error:
                raise DiscordAPIError(respuesta.status_code, respuesta.text)

            # Si ya no quedan peticiones en esta ventana, espera antes de la siguiente.
            if respuesta.headers.get("X-RateLimit-Remaining") == "0":
                time.sleep(float(respuesta.headers.get("X-RateLimit-Reset-After", 0)))
            return respuesta.json()

        raise DiscordAPIError(respuesta.status_code, f"falló tras {MAX_INTENTOS} intentos")
