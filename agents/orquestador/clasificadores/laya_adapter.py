"""
Adaptador de Laya para clasificación de intención.

Laya es un motor de decisiones no-autorregresivo. En lugar de generar
texto, evalúa un estado (el mensaje) contra una serie de preguntas
tipadas y devuelve probabilidades calibradas para cada opción.
"""
from __future__ import annotations

from ..contratos import ClasificacionIntencion
from ..config import LAYA_MODEL, LAYA_CONFIDENCE_THRESHOLD
from .base import ClasificadorInterface


class LayaAdapter(ClasificadorInterface):
    """Clasificador basado en Laya System 1."""

    def __init__(self):
        self.router = None
        self.questions = None
        self._inicializar()

    def _inicializar(self) -> None:
        """Inicializa el Router de Laya y define las preguntas tipadas."""
        
        # Flag de activación: permite desactivar Laya sin borrar el código
        import os
        LAYA_ENABLED = os.getenv("LAYA_ENABLED", "false").lower() == "true"
        
        if not LAYA_ENABLED:
            print("[LayaAdapter] Desactivado por configuración (LAYA_ENABLED=false).")
            self.router = None
            return
        
        try:
            from laya import Router

            # El Router detecta automáticamente el idioma y elige el checkpoint
            self.router = Router(preload=True)
            print(f"[LayaAdapter] Router inicializado (modelo: {LAYA_MODEL}).")

            # Definimos las preguntas que Laya debe responder.
            # Laya devolverá una probabilidad para cada opción.
            self.questions = {
                "intencion": {
                    "type": "choice",
                    "instructions": (
                        "Clasifica el mensaje del estudiante en UNA de estas 4 categorías. "
                        "PRIORIDAD: si el mensaje menciona un logro personal verificable "
                        "(contratación, certificación, beca, reconocimiento), clasifícalo como "
                        "TESTIMONIO aunque también contenga otras frases. "
                        "Si es una pregunta directa, clasifícalo como PREGUNTA_FAQ. "
                        "Si es una opinión sin logro, clasifícalo como COMENTARIO. "
                        "Solo usa OTRO para saludos, comandos o ruido."
                    ),
                    "criteria": {
                        "TESTIMONIO": (
                            "logro personal verificable del estudiante. Ejemplos: "
                            "fui contratado/contratada, me seleccionaron, quedé seleccionada, "
                            "conseguí trabajo, aprobé una certificación, recibí una beca, "
                            "me gradué, gané un premio, mi proyecto fue destacado. "
                            "Incluye frases como 'quedé seleccionada', 'me dieron el puesto', "
                            "'gracias a lo que aprendí conseguí', 'me ayudó a conseguir trabajo'."
                        ),
                        "PREGUNTA_FAQ": (
                            "pregunta directa sobre cursos, inscripciones, requisitos, fechas, "
                            "costos, becas, horarios, certificaciones. Contiene signos de "
                            "interrogación o frases como 'cuándo', 'cómo', 'dónde', 'cuál', "
                            "'qué necesito', 'hay becas', 'cuáles son los requisitos'."
                        ),
                        "COMENTARIO": (
                            "opinión, feedback o sentimiento SIN logro verificable. Ejemplos: "
                            "'me gustó la clase', 'excelente curso', 'no puedo acceder', "
                            "'me rindo', 'estoy frustrado', 'gracias por el apoyo'. "
                            "No menciona contratación, certificación ni beca."
                        ),
                        "OTRO": (
                            "saludo simple, comando (/ayuda), spam, mensaje vacío, "
                            "o contenido sin relación con la comunidad educativa."
                        ),
                    },
                }
            }

        except ImportError:
            print("[LayaAdapter] Laya no instalado. Ejecuta: pip install 'laya[langchain]'")
            self.router = None
        except Exception as e:
            print(f"[LayaAdapter] Error al inicializar: {e}")
            self.router = None

    def disponible(self) -> bool:
        return self.router is not None

    def clasificar(self, mensaje: dict) -> ClasificacionIntencion:
        """Clasifica un mensaje usando Laya."""
        mensaje_id = mensaje.get("mensaje_id", "")
        contenido = mensaje.get("contenido", "")

        if not self.disponible():
            return ClasificacionIntencion(
                mensaje_id=mensaje_id,
                intencion="OTRO",
                confianza=0.0,
                razon="Laya no disponible.",
            )

        try:
            # Laya evalúa el estado (el texto del mensaje) y devuelve
            # la probabilidad para cada opción definida en 'criteria'.
            resultado = self.router.predict(
                state={"mensaje": contenido},
                questions=self.questions,
                model=LAYA_MODEL,
            )

            # Extraer la respuesta de la pregunta "intencion"
            intencion_data = resultado["answers"]["intencion"]
            intencion = intencion_data["choice"]
            confianza = intencion_data["confidence"]

            # Construir la razón con las probabilidades de cada opción
            razon = f"Laya: {intencion} (confianza: {confianza:.2f})"

            return ClasificacionIntencion(
                mensaje_id=mensaje_id,
                intencion=intencion,
                confianza=confianza,
                razon=razon,
            )

        except Exception as e:
            return ClasificacionIntencion(
                mensaje_id=mensaje_id,
                intencion="OTRO",
                confianza=0.0,
                razon=f"Error en Laya: {e}",
            )