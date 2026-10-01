"""Clasificadores de intención del Orquestador."""
from .base import ClasificadorInterface
from .generic_adapter import GenericLLMAdapter
from .keyword_fallback import KeywordFallback

# Laya se importa dinámicamente solo si está habilitado
# from .laya_adapter import LayaAdapter

__all__ = [
    "ClasificadorInterface",
    "GenericLLMAdapter",
    "KeywordFallback",
]