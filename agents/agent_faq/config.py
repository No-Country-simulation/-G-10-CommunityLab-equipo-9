
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

# --- LLM (cambiar LLM_PROVIDER para alternar) ---
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # "google" | "openai" | "cohere"
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-3.5-flash-lite")
LLM_TEMPERATURE: float = 0.1

# --- Embeddings ---
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "huggingface")  # "huggingface" | "google" | "openai"
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small"
)

# --- Reranker ---
# Este modelo sirve para analizar la pregunta + cotenxto lo que ayuda a mejorar la respuesta semantica
RERANKER_MODEL: str = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# --- Umbrales de confianza ---
UMBRAL_SIMILITUD_RAG: float = 0.80      # Mínimo para considerar contexto relevante
UMBRAL_REVISION: float = 0.70           # Entre 0.70-0.84 → marcar revision_recomendada
UMBRAL_FIDELIDAD: float = 0.85          # Mínimo para aprobar respuesta sin revisión
UMBRAL_PREGUNTA_REPETIDA: float = 0.85  # Similitud para considerar pregunta repetida

# --- Chunking y recuperación ---
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200
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


