"""
Guardrail de Laya para protección contra prompt injection.

Laya evalúa si un mensaje contiene intentos de manipular al LLM
(jailbreaks, inyecciones, filtraciones de prompt).
"""
from __future__ import annotations

from ..config import LAYA_MODEL


class LayaGuardrail:
    """Wrapper del guardrail de Laya."""

    def __init__(self):
        self.router = None
        self._inicializar()

    def _inicializar(self) -> None:
        try:
            from laya import Router, guard_questions

            self.router = Router(preload=True)
            self.guard_questions = guard_questions()
            print("[LayaGuardrail] Inicializado.")
        except ImportError:
            print("[LayaGuardrail] Laya no instalado.")
            self.router = None
        except Exception as e:
            print(f"[LayaGuardrail] Error: {e}")
            self.router = None

    def disponible(self) -> bool:
        return self.router is not None

    def es_seguro(self, mensaje: str) -> tuple[bool, float]:
        """
        Evalúa si un mensaje es seguro.

        Returns:
            (es_seguro, probabilidad_de_amenaza)
        """
        if not self.disponible():
            return True, 0.0

        try:
            resultado = self.router.predict(
                state={"prompt": mensaje},
                questions=self.guard_questions,
                model=LAYA_MODEL,
            )
            # Laya devuelve la probabilidad de que sea una amenaza
            # (jailbreak, inyección, etc.)
            amenaza_prob = resultado.get("answers", {}).get("guard", {}).get("noul", 0.0)
            return amenaza_prob < 0.5, amenaza_prob
        except Exception:
            return True, 0.0