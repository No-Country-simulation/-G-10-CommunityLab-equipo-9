import os
import json
import discord
from datetime import datetime


# =====================================================
# 1. CONFIGURACIÓN
# =====================================================

# Token del bot guardado en una variable de entorno.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ID del canal que quieres escuchar.
# Déjalo como "" para escuchar todos los canales accesibles.
CANAL_PERMITIDO = ""

# =====================================================
# 2. AGENTE EVALUADOR DE SENTIMIENTO
# =====================================================

def evaluar_sentimiento(mensaje):

    texto = mensaje.lower()

    palabras_negativas = [
        "problema",
        "frustrado",
        "queja",
        "error",
        "no funciona",
        "molesto",
        "decepcionado",
        "sigo esperando"
    ]

    palabras_positivas = [
        "gracias",
        "excelente",
        "logré",
        "aprendí",
        "conseguí",
        "me ayudó",
        "estoy feliz",
        "terminé mi proyecto"
    ]

    # Revisar primero si hay indicios de una queja.
    for palabra in palabras_negativas:
        if palabra in texto:
            return {
                "es_testimonio_valido": False,
                "razon": "El mensaje puede expresar una queja."
            }

    # Revisar si hay indicios de un testimonio positivo.
    for palabra in palabras_positivas:
        if palabra in texto:
            return {
                "es_testimonio_valido": True,
                "razon": "El mensaje contiene indicios de una experiencia positiva."
            }

    return {
        "es_testimonio_valido": False,
        "razon": "No se identificó un testimonio positivo claro."
    }


# =====================================================
# 3. AGENTE EXTRACTOR DE TESTIMONIOS
# =====================================================

def extraer_testimonio(mensaje, usuario, canal):

    # Esta es una extracción básica.
    # Posteriormente puedes conectar un LLM para obtener
    # nombre, logro, empresa e impacto.

    return {
        "nombre": usuario,
        "logro": mensaje,
        "empresa": None,
        "impacto": None,
        "canal": canal
    }


# =====================================================
# 4. AGENTE GENERADOR DE PUBLICACIONES
# =====================================================

def generar_publicacion(datos):

    return (
        "¡Las experiencias de nuestra comunidad nos inspiran!\n\n"
        f"{datos['logro']}\n\n"
        "#CommunityLab #Comunidad #Aprendizaje"
    )


# =====================================================
# 5. FLUJO DE SOPORTE
# =====================================================

def gestionar_soporte(mensaje, usuario, canal):

    return {
        "tipo": "soporte",
        "usuario": usuario,
        "canal": canal,
        "mensaje": mensaje,
        "accion": "Revisar la consulta y determinar cómo ayudar."
    }


# =====================================================
# 6. ORQUESTADOR PRINCIPAL
# =====================================================

def procesar_mensaje(mensaje, usuario, canal, mensaje_id):

    print("\n" + "=" * 50)
    print("       ORQUESTADOR COMMUNITYLAB")
    print("=" * 50)

    print(f"ID del mensaje: {mensaje_id}")
    print(f"Usuario: {usuario}")
    print(f"Canal: {canal}")
    print(f"Mensaje: {mensaje}")

    # Paso 1: evaluar el mensaje.
    evaluacion = evaluar_sentimiento(mensaje)

    print("\nEvaluación:")
    print(f"Testimonio válido: {evaluacion['es_testimonio_valido']}")
    print(f"Razón: {evaluacion['razon']}")

    # Paso 2: decidir qué flujo ejecutar.
    if evaluacion["es_testimonio_valido"]:

        print("\nFlujo seleccionado: TESTIMONIOS")

        # Paso 3: extraer los datos.
        datos = extraer_testimonio(
            mensaje,
            usuario,
            canal
        )

        print("\nDatos del testimonio:")
        print(json.dumps(datos, ensure_ascii=False, indent=4))

        # Paso 4: generar un borrador.
        publicacion = generar_publicacion(datos)

        print("\nBorrador para LinkedIn:")
        print(publicacion)

        return {
            "id": mensaje_id,
            "tipo": "testimonio",
            "evaluacion": evaluacion,
            "datos": datos,
            "publicacion": publicacion
        }

    # Si no es un testimonio, dirigirlo a soporte.
    print("\nFlujo seleccionado: SOPORTE")

    resultado_soporte = gestionar_soporte(
        mensaje,
        usuario,
        canal
    )

    print("\nResultado:")
    print(resultado_soporte)

    return {
        "id": mensaje_id,
        "tipo": "soporte",
        "evaluacion": evaluacion,
        "resultado": resultado_soporte
    }


# =====================================================
# 7. CONEXIÓN CON DISCORD
# =====================================================

intents = discord.Intents.default()

# Necesario para recibir el contenido de los mensajes.
intents.message_content = True


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

        # Enviar el mensaje al orquestador.
        resultado = procesar_mensaje(
            mensaje=texto,
            usuario=usuario,
            canal=canal,
            mensaje_id=str(message.id)
        )

        # El resultado se imprime en la terminal.
        # No se publica automáticamente en Discord ni LinkedIn.


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