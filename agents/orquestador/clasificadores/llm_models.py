"""Fábrica de LLM para el clasificador del Orquestador."""
from __future__ import annotations
from langchain_core.language_models import BaseChatModel

from ..config import (
    CLASIFICADOR_PROVIDER, CLASIFICADOR_MODEL, CLASIFICADOR_TEMPERATURE,
    GEMINI_API_KEY, OPENAI_API_KEY, COHERE_API_KEY, ANTHROPIC_API_KEY,
    LLM_TIMEOUT_S,
)


def build_llm(modelo: str | None = None, temperatura: float | None = None,
              timeout_s: float | None = None) -> BaseChatModel | None:
    """Construye el LLM según CLASIFICADOR_PROVIDER.

    Sin argumentos, el del clasificador. El Agente-Mod (T06) pasa su modelo, su temperatura y su tiempo
    máximo, pero usa el mismo proveedor y la misma clave (D5).
    """
    provider = CLASIFICADOR_PROVIDER.lower()

    if provider == "google":
        if not GEMINI_API_KEY:
            print("[llm_factory] GEMINI_API_KEY no encontrada.")
            return None
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=modelo or CLASIFICADOR_MODEL,
            temperature=CLASIFICADOR_TEMPERATURE if temperatura is None else temperatura,
            google_api_key=GEMINI_API_KEY,
            # Sin esto Gemini espera sin límite y reintenta 6 veces por su cuenta (F8)
            timeout=timeout_s or LLM_TIMEOUT_S,
            max_retries=0,
        )

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