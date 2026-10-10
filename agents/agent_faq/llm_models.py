"""
Se configra un listado de modelos de llm con sus varaibles de configuración 
para brindar verstailidad a la configuracion del agente
"""
from langchain_core.language_models import BaseChatModel
from .config import (
    FAQ_PROVIDER, FAQ_MODEL_NAME, FAQ_TEMPERATURE, FAQ_LLM_TIMEOUT_S,
    GEMINI_API_KEY, OPENAI_API_KEY, COHERE_API_KEY,
)


def select_llm() -> BaseChatModel:
    """
    Permite configurar cada modelo de acuerdo al LLM_PROVIDER seleccionado
    """
    if FAQ_PROVIDER == "google":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no encontrada en .env")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=FAQ_MODEL_NAME,
            temperature=FAQ_TEMPERATURE,
            google_api_key=GEMINI_API_KEY,
            # Sin esto Gemini espera sin límite y reintenta 6 veces por su cuenta (F8)
            timeout=FAQ_LLM_TIMEOUT_S,
            max_retries=0,
        )

    if FAQ_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no encontrada en .env")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=FAQ_MODEL_NAME,
            temperature=FAQ_TEMPERATURE,
            api_key=OPENAI_API_KEY,
            timeout=FAQ_LLM_TIMEOUT_S,
            max_retries=0,
        )

    if FAQ_PROVIDER == "cohere":
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY no encontrada en .env")
        from langchain_cohere import ChatCohere
        return ChatCohere(
            model=FAQ_MODEL_NAME,
            temperature=FAQ_TEMPERATURE,
            cohere_api_key=COHERE_API_KEY,
        )

    raise ValueError(f"Proveedor LLM no soportado: {FAQ_PROVIDER}")