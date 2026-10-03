"""
Paso 3 · Publica conversaciones de alumnos ficticios en #dudas y #logros.

Lee los mensajes de simulation/conversations.json y los publica, en orden,
con el webhook de cada canal. El webhook permite elegir el nombre del autor en
cada mensaje, así que uno solo basta para simular a muchos alumnos.

Cada ejecución publica todo de nuevo: si lo corres dos veces, los mensajes
quedan duplicados. Por eso pide confirmación antes de empezar.

Uso:  python simulate_students.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

from config import ConfigError, cargar_config
from discord_api import DiscordAPI, DiscordAPIError

ARCHIVO_CONVERSACIONES = Path(__file__).parent / "simulation" / "conversations.json"
# Pausa entre mensajes: conserva el orden y se mantiene lejos del límite de los webhooks.
PAUSA_SEGUNDOS = 1.5


def verificar_webhook(api: DiscordAPI, canal: str, url: str | None, canal_id: str | None) -> str | None:
    """Devuelve un mensaje de error si el webhook falta, no existe o apunta a otro canal."""
    if url is None:
        return f"Falta la URL del webhook de #{canal} en el .env."
    try:
        # Un GET a la URL del webhook devuelve a qué canal pertenece.
        webhook = api.get(url)
    except DiscordAPIError as e:
        return f"La URL del webhook de #{canal} no es válida (HTTP {e.status})."
    if canal_id and webhook["channel_id"] != canal_id:
        return f"La URL del webhook de #{canal} publica en otro canal. ¿Intercambiaste las URLs?"
    return None


def publicar(api: DiscordAPI, url: str, autor: str, texto: str) -> None:
    api.post(
        url,
        json={
            "username": autor,
            "content": texto,
            # Impide que un texto con @everyone o @usuario notifique a alguien.
            "allowed_mentions": {"parse": []},
        },
        # wait=true: Discord confirma devolviendo el mensaje creado.
        params={"wait": "true"},
    )


def main() -> int:
    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1

    canales = {
        "dudas": (config.webhook_dudas_url, config.canal_dudas_id),
        "logros": (config.webhook_logros_url, config.canal_logros_id),
    }
    conversaciones = json.loads(ARCHIVO_CONVERSACIONES.read_text(encoding="utf-8"))

    # Sin token de bot: la URL del webhook ya incluye su propia clave.
    with DiscordAPI() as api:
        errores = [
            error
            for canal, (url, canal_id) in canales.items()
            if (error := verificar_webhook(api, canal, url, canal_id))
        ]
        if errores:
            for error in errores:
                print(f"❌ {error}")
            return 1

        total = sum(len(conversaciones[canal]) for canal in canales)
        detalle = ", ".join(f"#{canal}: {len(conversaciones[canal])}" for canal in canales)
        print(f"✅ Webhooks verificados. Se publicarán {total} mensajes ({detalle}).")
        if input("¿Continuar? Si ya lo corriste antes, se duplicarán (s/N): ").strip().lower() != "s":
            print("Cancelado. No se publicó nada.")
            return 0

        for canal, (url, _) in canales.items():
            for mensaje in conversaciones[canal]:
                publicar(api, url, mensaje["autor"], mensaje["texto"])
                vista_previa = mensaje["texto"].replace("\n", " ")[:50]
                print(f"  ✅ #{canal:<7} {mensaje['autor']}: {vista_previa}")
                time.sleep(PAUSA_SEGUNDOS)

    print(f"\nListo: {total} mensajes publicados.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DiscordAPIError as e:
        print(f"❌ Discord rechazó un mensaje: {e}")
        sys.exit(1)
    except httpx.TransportError as e:
        print(f"❌ No se pudo conectar con Discord: {e}")
        sys.exit(1)
