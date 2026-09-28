"""
Contratos de salidas del Agente FAQ. Se supone que el la entrada al Agente FAQ es una pregunta tipo string, sin estructura.
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class BuscadorOutput(BaseModel):
    """Output de la Tool 'Buscador' (RAG + Rerank + Guardrail)."""
    respuesta: str = Field(description="Respuesta generada (o vacía si no se encontró).")
    encontrado: bool = Field(description="True si hay contexto suficiente en los PDFs.")
    score_similitud: float = Field(ge=0.0, le=1.0, description="Score máximo de similitud RAG.")
    score_fidelidad: float = Field(ge=0.0, le=1.0, description="Score de fidelidad al contexto.")
    fuente: Optional[str] = Field(default=None, description="Fuente citada (archivo + página).")
    alucinacion_detectada: bool = Field(default=False, description="True si el guardrail detectó alucinación.")
    motivo_fallo: Optional[str] = Field(default=None, description="Razón si no se encontró respuesta.")


class EvaluacionFidelidad(BaseModel):
    """Output del guardrail anti-alucinación."""
    fiel_al_contexto: bool = Field(description="True si la respuesta se basa en el contexto.")
    justificacion: str = Field(description="Explicación de la auditoría.")
    score_fidelidad: float = Field(ge=0.0, le=1.0, description="Score numérico de fidelidad.")


class PreguntaSimilar(BaseModel):
    """Representa una pregunta previa similar detectada."""
    pregunta: str
    similitud: float = Field(ge=0.0, le=1.0)
    fecha: Optional[str] = None


class AnalisisFrecuencia(BaseModel):
    """Análisis de repetición de la pregunta actual."""
    pregunta_repetida: bool = False
    total_similares: int = 0
    preguntas_similares: List[PreguntaSimilar] = Field(default_factory=list)
    temas_relacionados: List[str] = Field(default_factory=list)
    accion_sugerida: str = "ninguna"
    alerta_humano: bool = False
    mensaje_alerta: Optional[str] = None


class ReporteFAQ(BaseModel):
    """Reporte completo generado por la Tool 'Reporte'."""
    id_reporte: str
    timestamp: str
    lote_id: Optional[str] = None
    pregunta: dict
    respuesta: dict
    metadata_intento: dict
    analisis_frecuencia: AnalisisFrecuencia
    estado_final: dict