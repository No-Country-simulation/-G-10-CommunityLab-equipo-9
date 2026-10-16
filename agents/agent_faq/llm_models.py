"""
Se configra un listado de modelos de llm con sus varaibles de configuración 
para brindar verstailidad a la configuracion del agente
"""
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from agents.reintento_llm import ReintentoEnVivo
from .config import (
    FAQ_PROVIDER, FAQ_MODEL_NAME, FAQ_TEMPERATURE, FAQ_LLM_TIMEOUT_S, FAQ_MODELO_RESPALDO,
    GEMINI_API_KEY, OPENAI_API_KEY, COHERE_API_KEY,
)


def select_llm() -> Runnable:
    """
    Permite configurar cada modelo de acuerdo al LLM_PROVIDER seleccionado
    """
    if FAQ_PROVIDER == "google":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no encontrada en .env")
        from langchain_google_genai import ChatGoogleGenerativeAI

        def gemini(nombre: str) -> BaseChatModel:
            return ChatGoogleGenerativeAI(
                model=nombre,
                temperature=FAQ_TEMPERATURE,
                google_api_key=GEMINI_API_KEY,
                # Sin esto Gemini espera sin límite y reintenta 6 veces por su cuenta (F8)
                timeout=FAQ_LLM_TIMEOUT_S,
                max_retries=0,
            )

        llm = gemini(FAQ_MODEL_NAME)
        if FAQ_MODELO_RESPALDO and FAQ_MODELO_RESPALDO != FAQ_MODEL_NAME:
            # DEC-165: la respuesta y la revisión anti-alucinación pasan al respaldo si el principal falla.
            # with_structured_output y bind_tools siguen funcionando: LangChain los aplica a los dos modelos
            llm = llm.with_fallbacks([gemini(FAQ_MODELO_RESPALDO)])
        # DEC-170: en vivo, si los dos dieron 503 o 504, reintenta mientras quede tiempo del tope. Fuera de vivo
        # (la FAQ semanal) no cambia nada
        return ReintentoEnVivo(llm, FAQ_LLM_TIMEOUT_S)

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