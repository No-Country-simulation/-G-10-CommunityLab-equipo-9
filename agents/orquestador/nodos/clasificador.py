"""
Nodo 2: clasificador de intención.

Usa la fábrica de clasificadores para elegir entre Cohere, Laya o Keyword.
Aplica fallback automático en cascada.
"""
from __future__ import annotations

from ..clasificadores.keyword_fallback import KeywordFallback
from ..clasificadores.base import ClasificadorInterface
from ..contratos import ClasificacionIntencion
from ..config import CLASIFICADOR_PROVIDER


def _construir_clasificador() -> ClasificadorInterface:
    """Cascada: LLM genérico (Gemini/OpenAI/Cohere) → Laya → Keyword."""
    provider = CLASIFICADOR_PROVIDER.lower()

    # Casos especiales primero
    if provider == "laya":
        from ..clasificadores.laya_adapter import LayaAdapter
        adaptador = LayaAdapter()
        if adaptador.disponible():
            return adaptador
        print("[clasificador] Laya no disponible. Usando KeywordFallback.")
        return KeywordFallback()

    if provider == "keyword":
        return KeywordFallback()

    # Caso general: cualquier LLM (Gemini, OpenAI, Cohere, Claude...)
    from ..clasificadores.generic_adapter import GenericLLMAdapter
    adaptador = GenericLLMAdapter()
    if adaptador.disponible():
        return adaptador

    # Fallback si el LLM falla
    print("[clasificador] LLM no disponible. Usando KeywordFallback.")
    return KeywordFallback()


class ClasificadorNodo:
    """Wrapper del clasificador con fallback."""

    def __init__(self):
        self.clasificador = _construir_clasificador()

    def clasificar_lote(self, mensajes: list[dict]) -> list[ClasificacionIntencion]:
        """Clasifica una lista de mensajes secuencialmente."""
        resultados: list[ClasificacionIntencion] = []
        for msg in mensajes:
            try:
                resultado = self.clasificador.clasificar(msg)
                resultados.append(resultado)
            except Exception as e:
                # Fallback de emergencia
                resultados.append(
                    ClasificacionIntencion(
                        mensaje_id=msg.get("mensaje_id", ""),
                        intencion="OTRO",
                        confianza=0.0,
                        razon=f"Error en clasificador: {e}",
                    )
                )
        return resultados