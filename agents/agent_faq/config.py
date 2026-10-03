
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Rutas base ---
BASE_DIR = Path(__file__).resolve().parent
RUTA_PDFS = BASE_DIR / "data" / "pdfs"          # Aqui se almacenan los documentos del agente RAG para busqueda
RUTA_FAISS_PDFS = BASE_DIR / "data" / "vectorstore" / "faiss_pdfs"
RUTA_FAISS_PREGUNTAS = BASE_DIR / "data" / "vectorstore" / "faiss_preguntas"
RUTA_HISTORIAL_PREGUNTAS = BASE_DIR / "data" / "historial_preguntas.json"

# --- LLM (cambiar FAQ_PROVIDER para alternar) ---
FAQ_PROVIDER: str = os.getenv("FAQ_PROVIDER", "google")  # "google" | "openai" | "cohere"
FAQ_MODEL_NAME: str = os.getenv("FAQ_MODEL_NAME", "gemini-3.1-flash-lite")
FAQ_TEMPERATURE: float = 0.1
# Tiempo máximo de cada llamada al LLM (D4, F8); la misma variable que usa el orquestador
FAQ_LLM_TIMEOUT_S: float = float(os.getenv("LLM_TIMEOUT_S", "20"))

# --- Embeddings ---
FAQ_EMBEDDING_PROVIDER: str = os.getenv("FAQ_EMBEDDING_PROVIDER", "huggingface")  # "huggingface" | "google" | "openai"
FAQ_EMBEDDING_MODEL_NAME: str = os.getenv(
    "FAQ_EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small"
)

# --- Reranker ---
# Este modelo sirve para analizar la pregunta + cotenxto lo que ayuda a mejorar la respuesta semantica
FAQ_RERANKER_MODEL: str = os.getenv(
    "FAQ_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# --- Umbrales de confianza ---
FAQ_UMBRAL_SIMILITUD: float = 0.80      # Mínimo para considerar contexto relevante
FAQ_UMBRAL_REVISION: float = 0.70           # Entre 0.70-0.84 → marcar revision_recomendada
FAQ_UMBRAL_FIDELIDAD: float = 0.85          # Mínimo para aprobar respuesta sin revisión
FAQ_UMBRAL_PREGUNTA_REPETIDA: float = 0.85  # Similitud para considerar pregunta repetida

# --- Chunking y recuperación ---
FAQ_CHUNK_SIZE: int = 1000
FAQ_CHUNK_OVERLAP: int = 200
TOP_K_RETRIEVAL: int = 8   # Candidatos iniciales del retriever
TOP_N_RERANK: int = 3      # Fragmentos finales tras reranking
TOP_K_PREGUNTAS: int = 5   # Preguntas similares a recuperar del histórico

# --- API Keys ---
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")

# --- IDs ---
AGENTE_NOMBRE: str = "agente_faq"
AGENTE_VERSION: str = "1.0.0"


