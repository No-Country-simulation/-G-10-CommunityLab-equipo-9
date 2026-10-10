"""Clasificadores de intención del Orquestador."""
from .base import ClasificadorInterface
from .keyword_fallback import KeywordFallback

__all__ = [
    "ClasificadorInterface",
    "KeywordFallback",
]