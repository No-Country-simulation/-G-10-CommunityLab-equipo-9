"""
Se configra un listado de modelos de embeddings, permite cambiar de modelo sin tener que reconfigurar variables.
Puede ser necesario revisar los parametros de configuración de cada modelo
"""

from langchain_core.embeddings import Embeddings
from ..config import (
    EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME,
    GEMINI_API_KEY, OPENAI_API_KEY,
)


def select_embeddings() -> Embeddings:
    """
    Permite configurar cada modelo de Embedding de acuerdo al EMBEDDING_PROVIDER seleccionado
    """
    if EMBEDDING_PROVIDER == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    if EMBEDDING_PROVIDER == "google":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY requerida para embeddings de Google")
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=GEMINI_API_KEY,
        )

    if EMBEDDING_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY requerida para embeddings de OpenAI")
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )

    raise ValueError(f"Proveedor embeddings no soportado: {EMBEDDING_PROVIDER}")


def requiere_prefijo_e5() -> bool:
    """Detecta si el modelo requiere prefijo 'passage:'/'query:' (protocolo E5)."""
    return EMBEDDING_PROVIDER == "huggingface" and "e5" in EMBEDDING_MODEL_NAME.lower()