"""
Interfaz abstracta para clasificadores de intención.

Permite intercambiar entre Cohere, Laya o cualquier otro modelo
sin cambiar el resto del Orquestador.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from ..contratos import ClasificacionIntencion


class ClasificadorInterface(ABC):
    """Interfaz que todos los clasificadores deben implementar."""

    @abstractmethod
    def clasificar(self, mensaje: dict) -> ClasificacionIntencion:
        """
        Clasifica un mensaje en una de las 4 categorías.

        Args:
            mensaje: dict con al menos 'mensaje_id' y 'contenido'.

        Returns:
            ClasificacionIntencion con mensaje_id, intencion, confianza y razon.
        """
        ...

    @abstractmethod
    def disponible(self) -> bool:
        """Verifica si el clasificador está operativo (API key, endpoint, etc.)."""
        ...