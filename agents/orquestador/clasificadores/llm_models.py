"""Fábrica de LLM para el clasificador del Orquestador."""
from __future__ import annotations
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from ..config import (
    CLASIFICADOR_PROVIDER, CLASIFICADOR_MODEL, CLASIFICADOR_TEMPERATURE,
    GEMINI_API_KEY, OPENAI_API_KEY, COHERE_API_KEY, ANTHROPIC_API_KEY,
    LLM_TIMEOUT_S, MODELO_RESPALDO,
)


def con_respaldo(principal: BaseChatModel, respaldo: BaseChatModel | None) -> Runnable:
    """DEC-165: si el modelo principal falla (por ejemplo, 503 por demanda alta), la misma llamada va al respaldo.

    with_structured_output y bind_tools siguen funcionando: LangChain los aplica a los dos modelos.
    """
    return principal.with_fallbacks([respaldo]) if respaldo is not None else principal


def build_llm(modelo: str | None = None, temperatura: float | None = None,
              timeout_s: float | None = None, usar_respaldo: bool = False) -> Runnable | None:
    """Construye el LLM según CLASIFICADOR_PROVIDER.

    Sin argumentos, el del clasificador. El Agente-Mod (T06) pasa su modelo, su temperatura y su tiempo
    máximo, pero usa el mismo proveedor y la misma clave (D5).
    usar_respaldo: el clasificador lo pide (DEC-165). El Agente-Mod no: una segunda llamada no cabría en su tiempo,
    y si falla, Java reintenta.
    """
    provider = CLASIFICADOR_PROVIDER.lower()

    if provider == "google":
        if not GEMINI_API_KEY:
            print("[llm_factory] GEMINI_API_KEY no encontrada.")
            return None
        from langchain_google_genai import ChatGoogleGenerativeAI

        def gemini(nombre: str) -> BaseChatModel:
            return ChatGoogleGenerativeAI(
                model=nombre,
                temperature=CLASIFICADOR_TEMPERATURE if temperatura is None else temperatura,
                google_api_key=GEMINI_API_KEY,
                # Sin esto Gemini espera sin límite y reintenta 6 veces por su cuenta (F8)
                timeout=timeout_s or LLM_TIMEOUT_S,
                max_retries=0,
            )

        principal = modelo or CLASIFICADOR_MODEL
        respaldo = MODELO_RESPALDO if usar_respaldo and MODELO_RESPALDO not in ("", principal) else None
        return con_respaldo(gemini(principal), gemini(respaldo) if respaldo else None)

    if provider == "openai":
        if not OPENAI_API_KEY:
            print("[llm_factory] OPENAI_API_KEY no encontrada.")
            return None
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=CLASIFICADOR_MODEL,
            temperature=CLASIFICADOR_TEMPERATURE,
            api_key=OPENAI_API_KEY,
            timeout=LLM_TIMEOUT_S,
            max_retries=0,
        )

    if provider == "cohere":
        if not COHERE_API_KEY:
            print("[llm_factory] COHERE_API_KEY no encontrada.")
            return None
        from langchain_cohere import ChatCohere
        return ChatCohere(
            model=CLASIFICADOR_MODEL,
            temperature=CLASIFICADOR_TEMPERATURE,
            cohere_api_key=COHERE_API_KEY,
        )

    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            print("[llm_factory] ANTHROPIC_API_KEY no encontrada.")
            return None
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=CLASIFICADOR_MODEL,
            temperature=CLASIFICADOR_TEMPERATURE,
            api_key=ANTHROPIC_API_KEY,
            timeout=LLM_TIMEOUT_S,
            max_retries=0,
        )

    print(f"[llm_factory] Provider no soportado: {provider}")
    return None