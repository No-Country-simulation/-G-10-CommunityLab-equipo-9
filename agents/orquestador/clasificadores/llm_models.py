"""Fábrica de LLM para el clasificador del Orquestador."""
from __future__ import annotations
from langchain_core.language_models import BaseChatModel

from ..config import (
    CLASIFICADOR_PROVIDER, CLASIFICADOR_MODEL, CLASIFICADOR_TEMPERATURE,
    GEMINI_API_KEY, OPENAI_API_KEY, COHERE_API_KEY, ANTHROPIC_API_KEY,
)


def build_llm() -> BaseChatModel | None:
    """Construye el LLM según CLASIFICADOR_PROVIDER."""
    provider = CLASIFICADOR_PROVIDER.lower()

    if provider == "google":
        if not GEMINI_API_KEY:
            print("[llm_factory] GEMINI_API_KEY no encontrada.")
            return None
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=CLASIFICADOR_MODEL,
            temperature=CLASIFICADOR_TEMPERATURE,
            google_api_key=GEMINI_API_KEY,
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
        )

    print(f"[llm_factory] Provider no soportado: {provider}")
    return None