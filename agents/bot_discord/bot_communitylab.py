import os
import json
import discord
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv()

# =====================================================
# 1. CONFIGURACIÓN
# =====================================================

# Token del bot guardado en una variable de entorno.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ID del canal que quieres escuchar.
# Déjalo como "" para escuchar todos los canales accesibles.
CANAL_PERMITIDO = ""

# Se agrega URL del Orquestador para implementar FastAPI).
ORQUESTADOR_URL = os.getenv(
    "ORQUESTADOR_URL", "http://localhost:8000/procesar"
)

# =====================================================
# 2. AGENTE EVALUADOR DE SENTIMIENTO
# =====================================================

# La función original `evaluar_sentimiento` corresponde al agente que evalua comentairo, 
# se tomo la caracterticas de clasifiacion hardcodeada keyword como fallback
# Además no medía intensidad (score) y no diferenciaba entre comentarios neutrales y frustración.
# Ahora esta lógica vive en el Orquestador (clasificador Cohere) y
# en el Agente de testimonio (análisis de sentimiento).


# =====================================================
# 3. AGENTE EXTRACTOR DE TESTIMONIOS
# =====================================================

# La función original `extraer_testimonio` simulaba la extracción de datos de un testimonio.
# Estas son funciones que corresponden al Agente-Testimonio

# =====================================================
# 4. AGENTE GENERADOR DE PUBLICACIONES
# =====================================================

# La función original `generar_publicacion` tambien correspondea funciones del 
# agente testnimonio que genera plbicaciones a partir de los datos extraidos del testimonio.
# el orquestador solo recibe la respuesta del testimonio para devolver la publicacion generada 
# al bot de discord para que este la publique en linkedin.


# =====================================================
# 5. FLUJO DE SOPORTE
# =====================================================

# La funcion `gestionar_soporte` simula la gestión de un mensaje que no es un testimonio.
# no hay un agente de soporte, solo se devuelve un dict con la información del mensaje y la acción a tomar.

# =====================================================
# 6. ORQUESTADOR PRINCIPAL
# =====================================================

# La funcion `procesar_mensaje` es el orquestador principal que recibe un mensaje de Discord,
# lo evalua, decide el flujo a seguir (testimonio o soporte), y devuelve la respuesta correspondiente.
# pero no hay una logica de langgraph que gestione la orquestacion de los agentes, solo se simula la logica de orquestacion con funciones hardcodeadas.

# =====================================================
# 7. NUEVA CAPA DE COMUNICACIÓN HTTP
# =====================================================

# Reemplaza toda la lógica de `procesar_mensaje` del bot original.
# El Orquestador se encarga de clasificar, invocar sub-agentes
# y devolver la respuesta lista para Discord.

async def enviar_al_orquestador(payload: dict) -> dict:
    """
    Envía el mensaje crudo de Discord al Orquestador vía HTTP.

    Args:
        payload: dict con la estructura {origen, servidor, mensajes[]}.

    Returns:
        dict con {lote_id, respuesta_discord, paquete_final, log_ejecucion}
        o {"error": "..."} si hay fallo.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ORQUESTADOR_URL, json=payload, timeout=60) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"[Bot] Error HTTP {resp.status}: {error_text[:200]}")
                    return {"error": f"HTTP {resp.status}"}
        except aiohttp.ClientConnectorError:
            print(f"[Bot] No se pudo conectar al Orquestador en {ORQUESTADOR_URL}")
            return {"error": "conexion_rechazada"}
        except Exception as e:
            print(f"[Bot] Error inesperado: {e}")
            return {"error": str(e)}


# Mantiene los campos originales de Discord (author con id, username,
#  bot, channel_id, content, timestamp) para que el adaptador del Orquestador los filtre.

def construir_payload_discord(message: discord.Message) -> dict:
    """
    Construye el payload crudo estilo Discord para el Orquestador.
    """
    return {
        "origen": "discord",
        "servidor": message.guild.name if message.guild else "DM",
        "mensajes": [
            {
                "id": str(message.id),
                "channel_id": str(message.channel.id),
                "author": {
                    "id": str(message.author.id),
                    "username": message.author.display_name,
                    "bot": message.author.bot,
                    # Campos crudos que el adaptador descartará:
                    "avatar": str(message.author.avatar) if message.author.avatar else None,
                    "discriminator": message.author.discriminator,
                },
                "content": message.content.strip(),
                "timestamp": message.created_at.isoformat(),
                "type": 0,
            }
        ],
    }

# =====================================================
# 8. CONEXIÓN CON DISCORD
# =====================================================

intents = discord.Intents.default()

# Necesario para recibir el contenido de los mensajes.
intents.message_content = True


# Cambios:
# - `on_ready`: añade log de la URL del Orquestador.
# - `on_message`: delega al Orquestador vía HTTP en lugar de llamar a `procesar_mensaje` localmente.

class BotCommunityLab(discord.Client):

    async def on_ready(self):

        print("\n" + "=" * 50)
        print("BOT DE COMMUNITYLAB CONECTADO")
        print("=" * 50)
        print(f"Bot: {self.user}")
        print(f"ID del bot: {self.user.id}")

        if CANAL_PERMITIDO:
            print(f"Canal configurado: {CANAL_PERMITIDO}")
        else:
            print("Escuchando todos los canales accesibles.")

        # Log de la URL del Orquestador
        print(f"Orquestador URL: {ORQUESTADOR_URL}")
        print("Esperando mensajes...\n")

    async def on_message(self, message):

        # Ignorar mensajes enviados por bots.
        if message.author.bot:
            return

        # Solo procesar mensajes de servidores.
        if not message.guild:
            return

        # Filtrar por canal si se configuró un ID.
        if CANAL_PERMITIDO:
            if str(message.channel.id) != CANAL_PERMITIDO:
                return

        texto = message.content.strip()

        # Ignorar mensajes sin texto.
        if not texto:
            return


        usuario = message.author.display_name
        canal = getattr(message.channel, "name", "desconocido")

        # Registrar la recepción del mensaje.
        print("\nMensaje recibido desde Discord.")

        print(f"\n[Bot] Mensaje recibido de {usuario} en canal {canal} (ID: {message.channel.id})")
        print(f"[Bot] Contenido: {texto[:80]}...")

        # [NUEVO] Construir payload estilo Discord
        payload = construir_payload_discord(message)

        # [NUEVO] Enviar al Orquestador
        print(f"[Bot] Enviando al Orquestador ({ORQUESTADOR_URL})...")
        respuesta = await enviar_al_orquestador(payload)

        if "error" in respuesta:
            print(f"[Bot] Error del Orquestador: {respuesta['error']}")
            return


        # --- PROCESAR RESPUESTA Y RESPONDER EN DISCORD ---

        respuesta_discord = respuesta.get("respuesta_discord", {})
        respuestas = respuesta_discord.get("respuestas", [])

        if not respuestas:
            print("[Bot] El Orquestador no devolvió respuestas.")
            return

        for r in respuestas:
            mensaje_id = r.get("mensaje_id", "")
            texto_respuesta = r.get("texto_respuesta", "")
            requiere_humano = r.get("requiere_humano", False)
            intencion = r.get("intencion", "DESCONOCIDO")

            print(f"[Bot] Intención: {intencion}")
            print(f"[Bot] Requiere humano: {requiere_humano}")

            # [NUEVO] Responder al usuario en Discord
            if texto_respuesta:
                try:
                    await message.reply(texto_respuesta)
                    print(f"[Bot] ✅ Respuesta enviada a Discord.")
                except discord.Forbidden:
                    print(f"[Bot] ❌ Sin permisos para responder.")
                except Exception as e:
                    print(f"[Bot] ❌ Error enviando respuesta: {e}")
            elif requiere_humano:
                # [NUEVO] Mensaje para casos derivados a humano
                await message.reply(
                    "Tu consulta fue registrada y será revisada por un mentor. "
                    "Te responderemos lo antes posible. 🙏"
                )

            # [NUEVO] Log del reporte interno
            resumen = respuesta.get("paquete_final", {}).get("resumen_lote", {})
            if resumen:
                print(
                    f"[Bot] Resumen del lote: "
                    f"{resumen.get('procesados', 0)} procesados, "
                    f"{resumen.get('requieren_humano', 0)} requieren humano."
                )


# =====================================================
# 8. INICIAR EL BOT
# =====================================================

if __name__ == "__main__":

    if not DISCORD_TOKEN:
        raise RuntimeError(
            "No se encontró DISCORD_TOKEN. "
            "Configura la variable de entorno antes de ejecutar."
        )

    bot = BotCommunityLab(intents=intents)
    bot.run(DISCORD_TOKEN)