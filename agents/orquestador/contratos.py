"""
Contratos Pydantic del Orquestador.

Define los schemas de:
- Input del backend (webhook de Discord)
- Output hacia n8n (respuesta_discord)
- Contratos internos (sub-agentes, paquete final, logs)
"""
from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# -- Entradas (desde n8n / Discord) ---
class MensajeNormalizado(BaseModel):
    """Mensaje individual ya filtrado del webhook crudo de Discord."""
    mensaje_id: str
    autor_id: str
    autor_username: str
    channel_id: str
    contenido: str
    timestamp: str
    es_bot: bool = False

class InputOrquestador(BaseModel):
    """Contrato de entrada del Orquestador."""
    lote_id: str
    origen: str = "discord"
    servidor: str = "Discord_ONE_G10"
    mensajes: List[MensajeNormalizado]


# --- Clasificaciión de intenciones (nodo clasificador) ---
class ClasificacionIntencion(BaseModel):
    """Output del nodo clasificador."""
    mensaje_id: str
    intencion: Literal["TESTIMONIO", "PREGUNTA_FAQ", "COMENTARIO", "OTRO"]
    confianza: float = Field(ge=0.0, le=1.0)
    razon: str

# --- Output normalizado de sub-agentes ---
class OutputSubAgente(BaseModel):
    """Cáscara común que todos los sub-agentes deben devolver."""
    mensaje_id: str
    intencion: str
    texto_respuesta: str           # Texto listo para enviar al usuario
    output: dict = Field(default_factory=dict)      # Datos específicos
    metadata: dict = Field(default_factory=dict)    # Tokens, tiempos
    status: Literal["exito", "atencion_humano"] = "exito"
    motivo_atencion: Optional[str] = None


# --- PAQUETE FINAL (auditoría interna) ---
class ResumenLote(BaseModel):
    total_mensajes: int          # Todos los mensajes del webhook
    descartados_filtro: int      # Bots, comandos, vacíos (antes del LLM)
    
    # Clasificados (post-LLM)
    testimonios: int             # TESTIMONIO
    preguntas_faq: int           # PREGUNTA_FAQ
    comentarios: int             # COMENTARIO
    otro: int                    # OTRO (clasificados como ruido por el LLM)
    
    # Estados de procesamiento
    procesados_exito: int        # Sub-agentes que resolvieron
    requieren_humano: int        # Sub-agentes que fallaron (status=atencion_humano)

class ActivoGenerado(BaseModel):
    mensaje_id: str
    intencion: str
    output: dict
    metadata: dict

class ItemRequiereHumano(BaseModel):
    mensaje_id: str
    motivo: str
    detalle: Optional[str] = None

class PaqueteFinal(BaseModel):
    lote_id: str
    resumen_lote: ResumenLote
    activos_generados: List[ActivoGenerado] = Field(default_factory=list)
    requiere_humano: List[ItemRequiereHumano] = Field(default_factory=list)


# --- LOG DE EJECUCIÓN ---
class SublogMensaje(BaseModel):
    mensaje_id: str
    intencion: Optional[str] = None
    confianza: Optional[float] = None
    tiempo_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    status: str = "pendiente"
    error: Optional[str] = None

class LogEjecucion(BaseModel):
    lote_id: str
    timestamp_inicio: str
    timestamp_fin: str
    duracion_total_ms: int
    tokens_totales: int = 0
    sublogs: List[SublogMensaje] = Field(default_factory=list)
    errores: List[str] = Field(default_factory=list)


# --- salida (Respuesta Discord)---
class RespuestaIndividual(BaseModel):
    """Respuesta lista para enviar a Discord."""
    mensaje_id: str
    channel_id: str
    texto_respuesta: str
    requiere_humano: bool = False
    intencion: str

class RespuestaDiscord(BaseModel):
    """Bloque de respuestas para el lote."""
    lote_id: str
    respuestas: List[RespuestaIndividual] = Field(default_factory=list)


# --- Output final del Orquestador ---
class OutputOrquestador(BaseModel):
    """Contrato de salida del Orquestador hacia n8n."""
    lote_id: str
    respuesta_discord: RespuestaDiscord
    paquete_final: PaqueteFinal
    log_ejecucion: LogEjecucion