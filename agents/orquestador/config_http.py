"""
Configuración HTTP del Orquestador.

Este archivo define cómo el Orquestador expone su API HTTP.
El equipo de backend debe usar estos valores para configurar
n8n, ngrok, firewall y cualquier otra infraestructura de red.

NO MODIFICAR sin coordinar con el equipo de backend.
"""


# --- 1. CONFIGURACIÓN DEL SERVIDOR HTTP ---
HTTP_HOST: str = "0.0.0.0"     # Acepta conexiones de cualquier IP
HTTP_PORT: int = 8000           # Puerto estándar de FastAPI


# --- 2. ENDPOINTS EXPUESTOS ---
ENDPOINT_PROCESAR_V1: str = "/v1/procesar"  # POST — contrato Java ↔ IA v1 (docs/contratos/JAVA_IA_v1.md)
ENDPOINT_GENERAR_V1: str = "/v1/generar"    # POST — Agente-Mod: post de LinkedIn y caso de éxito (T06)
ENDPOINT_FAQ_V1: str = "/v1/faq"            # POST — FAQ semanal con las dudas repetidas (T06b)
ENDPOINT_HEALTH: str = "/health"         # GET  — verifica salud
ENDPOINT_DOCS: str = "/docs"             # GET  — Swagger UI


# --- 3. COMANDOS DE EJECUCIÓN ---
COMANDO_EJECUCION: str = (
    "uvicorn agents.orquestador.api:app --host 0.0.0.0 --port 8000"
)
COMANDO_HEALTH: str = "curl http://localhost:8000/health"


# --- 4. NOTAS PARA EL BACKEND ---
NOTAS_BACKEND: str = """
INSTRUCCIONES PARA CONECTAR n8n CON EL ORQUESTADOR:

1. El Orquestador corre localmente en el puerto 8000.
2. n8n está en la nube y NO puede acceder a "localhost".
3. Opciones para exponer el Orquestador:

   OPCIÓN A (MVP - rápido):
   - Usar ngrok: ngrok http 8000
   - Copiar la URL pública (ej. https://abc123.ngrok.io)
   - En n8n, configurar nodo HTTP Request:
     Method: POST
     URL: https://abc123.ngrok.io/procesar
     Body Content Type: JSON
     Body: {{ $json }} (webhook crudo de Discord)

   OPCIÓN B (Fase 2 - permanente):
   - Desplegar en OCI Compute VM (Always Free)
   - Exponer puerto 8000 con IP pública
   - Configurar n8n con la IP pública

4. Verificar salud antes de conectar:
   curl http://localhost:8000/health
   → Debe responder: {"status": "ok"}

5. Si el puerto 8000 está ocupado:
   - Cambiar HTTP_PORT en este archivo
   - Ejecutar uvicorn con el nuevo puerto
   - Actualizar la URL en n8n
"""


# --- 5. CONTRATO DE ENTRADA ---
EJEMPLO_ENTRADA: dict = {
    "origen": "discord",
    "servidor": "Discord_ONE_G10",
    "mensajes": [
        {
            "id": "1553613486452383815",
            "channel_id": "1553596454248124467",
            "author": {
                "id": "1553598997250318336",
                "username": "Gabriel Lopez",
                "bot": False,
            },
            "content": "Hola, quisiera saber cuándo comienzan las inscripciones...",
            "timestamp": "2026-09-27T03:45:19.913000+00:00",
        }
    ],
}


# --- 6. CONTRATO DE SALIDA ---
EJEMPLO_SALIDA: dict = {
    "lote_id": "lote_20260930_143022_a3f5b8",
    "respuesta_discord": {
        "lote_id": "lote_20260930_143022_a3f5b8",
        "respuestas": [
            {
                "mensaje_id": "1553613486452383815",
                "channel_id": "1553596454248124467",
                "texto_respuesta": "📚 ¡Hola Gabriel! Las inscripciones...",
                "requiere_humano": False,
                "intencion": "PREGUNTA_FAQ",
            }
        ],
    },
}