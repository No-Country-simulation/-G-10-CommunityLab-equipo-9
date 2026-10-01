"""
Clasificador de último recurso basado en keywords.

Se usa cuando Cohere y Laya no están disponibles.
Es rápido pero menos preciso que un LLM.
"""
from __future__ import annotations
import re
from ..contratos import ClasificacionIntencion
from .base import ClasificadorInterface


# Keywords indicadoras de cada categoría
KEYWORDS_TESTIMONIO = [
    # Contratación / empleo
    "me contrataron", "fui contratado", "fui contratada",
    "conseguí trabajo", "conseguí empleo", "trabajo en",
    "me seleccionaron", "quedé seleccionada", "quedé seleccionado",
    "fui seleccionado", "fui seleccionada", "puesto de",
    "me ofrecieron trabajo", "me ofrecieron empleo",
    # Certificaciones / educación
    "aprobé", "certificación", "certificado", "gradué",
    "me gradué", "terminé la carrera", "terminé el curso",
    # Becas / reconocimientos
    "beca", "me dieron una beca", "recibí una beca",
    "reconocimiento", "premio", "gané", "logré",
    # Genéricos de logro
    "lo logré", "cumplí mi meta", "lo conseguí",
]

KEYWORDS_PREGUNTA = [
    "cuándo", "cómo", "dónde", "cuál", "qué", "por qué",
    "requisitos", "inscripción", "fecha", "horario", "costo",
    "hay beca", "tienen beca", "puedo", "se puede",
]

KEYWORDS_COMENTARIO_NEGATIVO = [
    "no funciona", "no puedo", "problema", "error", "frustrado",
    "me rindo", "no entiendo", "no sirve", "queja", "molesto",
]

KEYWORDS_COMENTARIO_POSITIVO = [
    "me gustó", "excelente", "gracias", "buen curso", "aprendí",
    "muy bueno", "felicidades", "genial",
]


class KeywordFallback(ClasificadorInterface):
    """Clasificador simple basado en keywords."""

    def disponible(self) -> bool:
        return True  # Siempre disponible

    def clasificar(self, mensaje: dict) -> ClasificacionIntencion:
        mensaje_id = mensaje.get("mensaje_id", "")
        contenido = mensaje.get("contenido", "").lower()

        # 1. Testimonios (prioridad alta)
        for kw in KEYWORDS_TESTIMONIO:
            if kw in contenido:
                return ClasificacionIntencion(
                    mensaje_id=mensaje_id,
                    intencion="TESTIMONIO",
                    confianza=0.65,
                    razon=f"Keyword de testimonio detectada: '{kw}'",
                )

        # 2. Preguntas FAQ
        for kw in KEYWORDS_PREGUNTA:
            if kw in contenido:
                return ClasificacionIntencion(
                    mensaje_id=mensaje_id,
                    intencion="PREGUNTA_FAQ",
                    confianza=0.60,
                    razon=f"Keyword de pregunta detectada: '{kw}'",
                )

        # 3. Comentarios (negativos o positivos)
        for kw in KEYWORDS_COMENTARIO_NEGATIVO + KEYWORDS_COMENTARIO_POSITIVO:
            if kw in contenido:
                return ClasificacionIntencion(
                    mensaje_id=mensaje_id,
                    intencion="COMENTARIO",
                    confianza=0.55,
                    razon=f"Keyword de comentario detectada: '{kw}'",
                )

        # 4. Por defecto: OTRO
        return ClasificacionIntencion(
            mensaje_id=mensaje_id,
            intencion="OTRO",
            confianza=0.40,
            razon="No se detectaron keywords relevantes.",
        )