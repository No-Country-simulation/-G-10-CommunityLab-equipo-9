"""
Tool 'Reporte': metadata + análisis de frecuencia.
"""

from datetime import datetime
from uuid import uuid4

from langchain_core.tools import tool

from ..contratos import ReporteFAQ, AnalisisFrecuencia
from ..vectorstore.preguntas_store import PreguntasStore


class ReporteTool:
    """
    Encapsula la lógica de la Tool 'Reporte'.
    """

    def __init__(self, preguntas_store: PreguntasStore):
        self.preguntas_store = preguntas_store

    def ejecutar(
        self,
        pregunta: str,
        resultado_buscador: dict,
        metadata: dict | None = None,
    ) -> dict:
        """Genera el reporte con análisis de frecuencia."""
        # 1. Buscar preguntas similares
        similares = self.preguntas_store.buscar_similares(pregunta)

        # 2. Analizar frecuencia
        pregunta_repetida = len(similares) > 0
        analisis = AnalisisFrecuencia(
            pregunta_repetida=pregunta_repetida,
            total_similares=len(similares),
            preguntas_similares=similares,
            temas_relacionados=[],
            accion_sugerida="publicar_faq_masiva" if pregunta_repetida else "ninguna",
            alerta_humano=pregunta_repetida,
            mensaje_alerta=(
                f"{len(similares)} estudiantes preguntaron algo similar recientemente. "
                "Considerar crear un tutorial o FAQ pública."
                if pregunta_repetida
                else None
            ),
        )

        # 3. Construir reporte
        reporte = ReporteFAQ(
            id_reporte=f"rep_faq_{uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            lote_id=(metadata or {}).get("lote_id"),
            pregunta={
                "texto_original": pregunta,
                "autor": (metadata or {}).get("autor"),
                "canal_origen": (metadata or {}).get("canal_origen"),
            },
            respuesta={
                "texto_generado": resultado_buscador.get("respuesta", ""),
                "encontrada": resultado_buscador.get("encontrado", False),
                "score_similitud": resultado_buscador.get("score_similitud", 0.0),
                "score_fidelidad": resultado_buscador.get("score_fidelidad", 0.0),
                "fuente_citada": resultado_buscador.get("fuente"),
                "alucinacion_detectada": resultado_buscador.get("alucinacion_detectada", False),
            },
            metadata_intento={
                "modelo_llm": (metadata or {}).get("modelo_llm"),
                "umbrales_aplicados": {
                    "similitud": 0.80,
                    "fidelidad": 0.85,
                },
            },
            analisis_frecuencia=analisis,
            estado_final={
                "requiere_humano": not resultado_buscador.get("encontrado", False),
                "motivo": resultado_buscador.get("motivo_fallo"),
                "accion_orquestador": (
                    "enviar_a_curaduria"
                    if resultado_buscador.get("encontrado")
                    else "derivar_a_mentor"
                ),
            },
        )

        # 4. Registrar la pregunta en el histórico
        self.preguntas_store.registrar(
            pregunta,
            metadatos={
                "lote_id": (metadata or {}).get("lote_id"),
                "autor": (metadata or {}).get("autor"),
            },
        )

        return reporte.model_dump()


def crear_tool_reporte(reporte_tool: ReporteTool):
    """
    Envuelve el ReporteTool como Tool de LangChain.
    """

    @tool
    def generar_reporte_faq(
        pregunta: str,
        resultado_buscador: dict,
    ) -> dict:
        """Genera un reporte con metadata del intento de respuesta.
        Incluye análisis de frecuencia (si la pregunta se repite).
        Devuelve un JSON con el reporte completo."""
        return reporte_tool.ejecutar(pregunta, resultado_buscador)

    return generar_reporte_faq