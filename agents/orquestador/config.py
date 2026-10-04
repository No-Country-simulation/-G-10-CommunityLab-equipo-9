"""
Configuración centralizada del Orquestador.

Todos los parámetros que se pueden ajustar sin tocar el código
están centralizados aquí. Los proveedores de LLM y las API keys
se leen de variables de entorno para facilitar la colaboración.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Rutas base --- 
BASE_DIR: Path = Path(__file__).resolve().parent

# --- CLASIFICADOR (ORQUESTADOR) ---
# Proveedor: "gemini" | "openai" | "cohere" | "laya" | "keyword"
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

# S2: clave que Java envía en X-Api-Key a /v1/procesar. Vacía: /v1/procesar rechaza todo con 401.
# La genera scripts/generar_api_key.py --cliente ia (sin mostrarla)
API_KEY_IA: str = os.getenv("API_KEY_IA", "").strip()


# API keys (todas disponibles, solo se usa la del provider activo)
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

# Laya (especial)
# LAYA actualmente se encuentra en entrenamiento, por lo que no se recomienda su uso en producción.
# Para activar LAYA_ENABLED: bool = os.getenv("LAYA_ENABLED", "false")

LAYA_ENABLED: bool = False  
LAYA_MODEL: str = os.getenv("LAYA_MODEL", "multilingual")

# --- 3. SUB-AGENTES ---
# Agente FAQ (Gemini)
FAQ_PROVIDER: str = "google"
FAQ_MODEL: str = os.getenv("FAQ_MODEL", "gemini-2.0-flash-exp")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")


# Agente-Mod (ChatGPT)
MOD_PROVIDER: str = "openai"
MOD_MODEL: str = os.getenv("MOD_MODEL", "gpt-4o-mini")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# Rutas de importación dinámica de sub-agentes
ORQ_SUBAGENTE_FAQ_PATH: str = os.getenv(
    "ORQ_SUBAGENTE_FAQ_PATH",
    "agents.agent_faq.agente_faq.AgenteFAQ"
)
ORQ_SUBAGENTE_MOD_PATH: str = os.getenv(
    "ORQ_SUBAGENTE_MOD_PATH",
    "agents.agent_mod.agente_mod.AgenteMod"
)


# --- FILTROS ---
MIN_LONGITUD_CONTENIDO: int = 3
PATRON_COMANDOS: str = r"^/[a-z]+"


# --- CATEGORÍAS VÁLIDAS ---
CATEGORIAS_VALIDAS: list[str] = [
    "TESTIMONIO",
    "PREGUNTA_FAQ",
    "COMENTARIO",
    "OTRO",
]


# --- UMBRALES ---
UMBRAL_CONFIANZA_ALTA: float = 0.85
UMBRAL_CONFIANZA_MEDIA: float = 0.60
MAX_REINTENTOS_CLASIFICACION: int = 2


# --- OCI OBJECT STORAGE ---
OCI_BUCKET: str = os.getenv("OCI_BUCKET", "communitylab-activos-marketing")
OCI_NAMESPACE: str | None = os.getenv("OCI_NAMESPACE")
OCI_REGION: str = os.getenv("OCI_REGION", "us-ashburn-1")
OCI_CONFIG_PATH: str = os.getenv(
    "OCI_CONFIG_PATH", str(Path.home() / ".oci" / "config")
)

OCI_PREFIJO_ACTIVOS: str = "activos"
OCI_PREFIJO_REPORTES: str = "reportes"
OCI_PREFIJO_LOGS: str = "logs"

