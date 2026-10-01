"""
Adaptador genérico de clasificación.

Funciona con CUALQUIER LLM que soporte structured output
(Gemini, OpenAI, Cohere, Claude, etc.). Solo cambia la variable
CLASIFICADOR_PROVIDER en .env.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from ..contratos import ClasificacionIntencion
from ..config import MAX_REINTENTOS_CLASIFICACION
from .base import ClasificadorInterface
from .llm_models import build_llm


SYSTEM_PROMPT_CLASIFICADOR = """Eres un clasificador de mensajes de una comunidad educativa digital.
Clasifica el mensaje del estudiante en UNA de estas 4 categorías:

**TESTIMONIO**: El estudiante reporta un LOGRO verificable.
Ejemplos:
- "¡Comunidad, quedé seleccionada para el puesto de Desarrolladora Junior de IA!"
- "Me contrataron como Dev Jr después del curso."
- "Aprobé mi certificación internacional."
- "Recibí una beca para estudiar en el extranjero."

**PREGUNTA_FAQ**: El estudiante hace una PREGUNTA directa.
Ejemplos:
- "¿Cuáles son los requisitos para inscribirme en el curso de Python?"
- "¿Cuándo empiezan las inscripciones?"
- "¿Hay becas para estudiantes extranjeros?"

**COMENTARIO**: Opinión o sentimiento SIN logro verificable.
Ejemplos:
- "Me gustó mucho la clase de ayer, aprendí bastante."
- "Excelente curso."
- "No puedo acceder a mi cuenta."

**OTRO**: Solo para saludos, comandos o ruido.
Ejemplos:
- "Hola", "/ayuda", "jajaja"

REGLAS:
- Si menciona un LOGRO (contratación, beca, certificación, premio), es TESTIMONIO.
- Si contiene una PREGUNTA, es PREGUNTA_FAQ.
- Si es OPINIÓN o SENTIMIENTO sin logro, es COMENTARIO.
- NUNCA uses OTRO para mensajes con logros, preguntas o comentarios.
"""


class GenericLLMAdapter(ClasificadorInterface):
    """Clasificador genérico basado en cualquier LLM con structured output."""

    def __init__(self):
        self.llm = None
        self.llm_structured = None
        self._inicializar()

    def _inicializar(self) -> None:
        try:
            self.llm = build_llm()
            if self.llm is None:
                return
            self.llm_structured = self.llm.with_structured_output(ClasificacionIntencion)
            print(f"[GenericAdapter] Inicializado ({type(self.llm).__name__}).")
        except Exception as e:
            print(f"[GenericAdapter] Error al inicializar: {e}")
            self.llm = None
            self.llm_structured = None

    def disponible(self) -> bool:
        return self.llm_structured is not None

    def clasificar(self, mensaje: dict) -> ClasificacionIntencion:
        mensaje_id = mensaje.get("mensaje_id", "")
        contenido = mensaje.get("contenido", "")

        if not self.disponible():
            return ClasificacionIntencion(
                mensaje_id=mensaje_id,
                intencion="OTRO",
                confianza=0.0,
                razon="LLM no disponible.",
            )

        for intento in range(MAX_REINTENTOS_CLASIFICACION + 1):
            try:
                resultado = self.llm_structured.invoke([
                    SystemMessage(content=SYSTEM_PROMPT_CLASIFICADOR),
                    HumanMessage(content=f"Mensaje a clasificar:\n\n{contenido}"),
                ])
                resultado.mensaje_id = mensaje_id
                return resultado
            except Exception as e:
                if intento == MAX_REINTENTOS_CLASIFICACION:
                    return ClasificacionIntencion(
                        mensaje_id=mensaje_id,
                        intencion="OTRO",
                        confianza=0.0,
                        razon=f"Error: {e}",
                    )

        return ClasificacionIntencion(
            mensaje_id=mensaje_id, intencion="OTRO", confianza=0.0, razon="Error inesperado."
        )