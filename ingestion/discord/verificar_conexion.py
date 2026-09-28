"""
Paso 2 · Verifica la conexión del bot con Discord.

Comprueba, en orden:
  1. Que el token es válido (quién es el bot).
  2. Que Message Content Intent está activado.
  3. En qué servidores está el bot y qué canales de texto ve.
  4. Que puede leer el historial de cada canal.

Solo hace peticiones GET: no escribe nada en Discord.
Uso:  python verificar_conexion.py
"""
import sys

import httpx

from config import ConfigError, cargar_config
from discord_api import DiscordAPI, DiscordAPIError

# Flags de la aplicación que indican Message Content Intent activo:
# 1<<18 en apps verificadas, 1<<19 en apps no verificadas (menos de 100 servidores).
INTENT_MESSAGE_CONTENT = (1 << 18) | (1 << 19)
CANAL_DE_TEXTO = 0
VARIABLE_POR_CANAL = {
    "dudas": "DISCORD_CHANNEL_DUDAS_ID",
    "logros": "DISCORD_CHANNEL_LOGROS_ID",
}


def main() -> int:
    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1

    with DiscordAPI(config.bot_token) as api:
        # 1. GET /users/@me devuelve el usuario del bot dueño del token.
        try:
            bot = api.get("/users/@me")
        except DiscordAPIError as e:
            if e.status == 401:
                print("❌ Token inválido. Genera uno nuevo con Reset Token y actualiza el .env.")
                return 1
            raise
        print(f"✅ Conectado como {bot['username']} (id {bot['id']})")

        # 2. Sin este intent, Discord entrega los mensajes con el texto vacío.
        app = api.get("/applications/@me")
        if app.get("flags", 0) & INTENT_MESSAGE_CONTENT:
            print("✅ Message Content Intent activado")
        else:
            print("⚠️  Message Content Intent desactivado: los mensajes llegarán sin texto.")

        # 3. Servidores y canales de texto que ve el bot.
        servidores = api.get("/users/@me/guilds")
        if not servidores:
            print("⚠️  El bot no está en ningún servidor. Revisa el paso 1.B.4.")
            return 1

        for servidor in servidores:
            print(f"\nServidor: {servidor['name']}")
            print(f"  DISCORD_GUILD_ID={servidor['id']}")
            for canal in api.get(f"/guilds/{servidor['id']}/channels"):
                if canal["type"] != CANAL_DE_TEXTO:
                    continue
                # 4. Pide un solo mensaje para comprobar el permiso de lectura.
                try:
                    api.get(f"/channels/{canal['id']}/messages", params={"limit": 1})
                    lectura = "✅ lectura OK"
                except DiscordAPIError as e:
                    lectura = f"❌ sin permiso de lectura (HTTP {e.status})"
                print(f"  #{canal['name']:<12} {lectura}")
                if canal["name"] in VARIABLE_POR_CANAL:
                    print(f"    {VARIABLE_POR_CANAL[canal['name']]}={canal['id']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.TransportError as e:
        print(f"❌ No se pudo conectar con Discord: {e}")
        sys.exit(1)
