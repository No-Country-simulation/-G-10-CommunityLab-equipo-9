"""
Se configra un listado de modelos de llm con sus varaibles de configuración 
para brindar verstailidad a la configuracion del agente
"""
from langchain_core.language_models import BaseChatModel
from .config import (
    LLM_PROVIDER, LLM_MODEL_NAME, LLM_TEMPERATURE,
    GEMINI_API_KEY, OPENAI_API_KEY, COHERE_API_KEY,
)


def select_llm() -> BaseChatModel:
    """
    Permite configurar cada modelo de acuerdo al LLM_PROVIDER seleccionado
    """
    if LLM_PROVIDER == "google":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no encontrada en .env")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            google_api_key=GEMINI_API_KEY,
        )

    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no encontrada en .env")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            api_key=OPENAI_API_KEY,
        )

    if LLM_PROVIDER == "cohere":
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY no encontrada en .env")
        from langchain_cohere import ChatCohere
        return ChatCohere(
            model=LLM_MODEL_NAME,
            temperature=LLM_TEMPERATURE,
            cohere_api_key=COHERE_API_KEY,
        )

    raise ValueError(f"Proveedor LLM no soportado: {LLM_PROVIDER}")