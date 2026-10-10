"""
Configuración centralizada del Orquestador.

Todos los parámetros que se pueden ajustar sin tocar el código
están centralizados aquí. Los proveedores de LLM y las API keys
se leen de variables de entorno para facilitar la colaboración.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- CLASIFICADOR (ORQUESTADOR) ---
# Proveedor: "google" | "openai" | "cohere" | "anthropic" | "keyword"
CLASIFICADOR_PROVIDER: str = os.getenv("ORQ_CLASIFICADOR_PROVIDER", "google")
CLASIFICADOR_MODEL: str = os.getenv("ORQ_CLASIFICADOR_MODEL", "gemini-3.5-flash-lite")
CLASIFICADOR_TEMPERATURE: float = 0.0

# Tiempo máximo de cada llamada al LLM (D4, F8): modelo 20 s < Java → IA 30 s < bot → Java 40 s
LLM_TIMEOUT_S: float = float(os.getenv("LLM_TIMEOUT_S", "20"))
# Reintentos propios de /v1/procesar si el LLM falla (no se reintenta si se agotó el tiempo)
LLM_REINTENTOS: int = int(os.getenv("LLM_REINTENTOS", "1"))
# DEC-54: tope total de un pedido en tiempoReal (clasificar + Agente FAQ). Si se agota, la duda llega con
# respuesta.encontrada = false y el bot deriva al mentor, antes de los 30 s que espera Java. 0 = sin tope
TIEMPO_REAL_TOPE_S: float = float(os.getenv("TIEMPO_REAL_TOPE_S", "25"))

# Agente-Mod (T06): redacta posts de LinkedIn y casos de éxito en POST /v1/generar.
# DEC-85: el modelo se configura; por defecto, el mismo que clasifica. Mismo proveedor (D5).
MOD_MODEL_NAME: str = os.getenv("MOD_MODEL_NAME", "").strip() or CLASIFICADOR_MODEL
# Una sola llamada, sin reintentos: tiene que caber en los 30 s de lectura de Java (D4). Si falla, Java reintenta
MOD_TIMEOUT_S: float = float(os.getenv("MOD_TIMEOUT_S", "25"))
# Algo de creatividad para redactar (el clasificador usa 0)
MOD_TEMPERATURE: float = float(os.getenv("MOD_TEMPERATURE", "0.7"))

# FAQ semanal (T06b): POST /v1/faq agrupa las dudas repetidas y busca sus respuestas.
# Tope total del pedido: una llamada para agrupar más una consulta al Agente FAQ por cada grupo sin respuesta.
# Tiene que ser menor que el tiempo de lectura de Java para /v1/faq (150 s). Si se agota, los grupos que faltan
# van a "sin respuesta en los documentos": nunca se inventa una respuesta
FAQ_SEMANAL_TOPE_S: float = float(os.getenv("FAQ_SEMANAL_TOPE_S", "120"))
# La llamada que agrupa (una sola, sin reintento; si falla, Java reintenta). Mismo modelo que el Agente-Mod
FAQ_AGRUPAR_TIMEOUT_S: float = float(os.getenv("FAQ_AGRUPAR_TIMEOUT_S", "45"))
# Agrupar es casi una clasificación: poca creatividad
FAQ_AGRUPAR_TEMPERATURE: float = float(os.getenv("FAQ_AGRUPAR_TEMPERATURE", "0.2"))

# S2: clave que Java envía en X-Api-Key a /v1/procesar. Vacía: /v1/procesar rechaza todo con 401.
# La genera scripts/generar_api_key.py --cliente ia (sin mostrarla)
API_KEY_IA: str = os.getenv("API_KEY_IA", "").strip()


# API keys (todas disponibles, solo se usa la del provider activo)
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

# Ruta de importación dinámica del Agente FAQ (la usa nodos/invocador_faq.py)
ORQ_SUBAGENTE_FAQ_PATH: str = os.getenv(
    "ORQ_SUBAGENTE_FAQ_PATH",
    "agents.agent_faq.agente_faq.AgenteFAQ"
)
