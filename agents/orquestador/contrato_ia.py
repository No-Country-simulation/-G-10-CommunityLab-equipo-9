"""
Contrato Java ↔ IA v1 (docs/contratos/JAVA_IA_v1.md).

- Entrada de POST /v1/procesar: el Lote del contrato v1 de la ingesta. Se importa de
  ingestion/discord/contract.py, la única definición: aquí no se copia.
- Salida: los modelos de este archivo, con los nombres en camelCase igual que el contrato v1.

Uso:  python -m agents.orquestador.contrato_ia   → escribe docs/contratos/JAVA_IA_v1.schema.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ingestion.discord.contract import Lote, Mensaje as MensajeContrato, Modo  # noqa: F401  (se reexportan)

VERSION_CONTRATO_IA = "1.0"
ARCHIVO_ESQUEMA = Path(__file__).resolve().parents[2] / "docs" / "contratos" / "JAVA_IA_v1.schema.json"

# Valores cerrados: Java los guarda en mensajes.intencion / sentimiento / tema y el dashboard los cuenta
Intencion = Literal["TESTIMONIO", "PREGUNTA_FAQ", "COMENTARIO", "OTRO"]
Sentimiento = Literal["MUY_POSITIVO", "POSITIVO", "NEUTRO", "NEGATIVO", "MUY_NEGATIVO"]
Tema = Literal[
    "inscripciones",         # matrícula, requisitos de ingreso, cupos
    "becas_pagos",           # becas, cuotas, pagos, descuentos
    "calendario_clases",     # horarios, clases en vivo, fechas del calendario académico
    "evaluaciones",          # challenges, entregas, plazos, notas, apelaciones
    "contenido_curso",       # dudas de teoría o de la materia (listas, recursividad, SQL...)
    "herramientas_entorno",  # instalar y configurar herramientas, errores de entorno, git
    "plataforma_acceso",     # acceso a la plataforma o a la cuenta, campus virtual
    "proyectos",             # proyectos propios, repositorios, portafolio, deploy
    "empleo",                # entrevistas, contrataciones, búsqueda laboral
    "comunidad",             # saludos, agradecimientos, motivación, apoyo entre pares
    "otro",
]
TEMAS: tuple[str, ...] = get_args(Tema)
Estado = Literal["OK", "ERROR"]
Metodo = Literal["llm", "palabrasClave", "regla"]


class ModeloIa(BaseModel):
    """Base: camelCase en el JSON y ningún campo de más, como el contrato v1."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class RespuestaFaq(ModeloIa):
    """Respuesta del Agente FAQ. Solo en modo tiempoReal y para PREGUNTA_FAQ."""

    texto: str = Field(description="Texto para publicar en Discord. Vacío si no hubo respuesta")
    encontrada: bool = Field(
        description="true solo si la respuesta tiene respaldo firme en los documentos (D3). "
        "Si es false, el bot no publica el texto y deriva a un mentor"
    )
    fuentes: list[str] = Field(description="Documento y página que respaldan la respuesta")
    motivo: str | None = Field(default=None, description="Por qué no se encontró o requiere revisión")


class ResultadoMensaje(ModeloIa):
    """Las etiquetas de un mensaje. Hay exactamente uno por cada mensaje del lote."""

    discord_id: str = Field(description="El id del mensaje en el contrato v1")
    estado: Estado = Field(description="OK: etiquetas válidas. ERROR: el LLM falló y no hay etiquetas (F4)")
    metodo: Metodo = Field(
        description="llm: lo clasificó el modelo. palabrasClave: clasificador de respaldo elegido por "
        "configuración. regla: no se envió al modelo (bot, aviso del sistema o sin texto)"
    )
    intencion: Intencion | None = Field(default=None, description="null si estado = ERROR")
    confianza: float | None = Field(default=None, ge=0.0, le=1.0, description="null si estado = ERROR")
    sentimiento: Sentimiento | None = Field(default=None, description="null si estado = ERROR o metodo = regla")
    tema: Tema | None = Field(default=None, description="null si estado = ERROR o metodo = regla")
    razon: str = Field(description="Por qué se eligió la intención, o el motivo del error o de la regla")
    respuesta: RespuestaFaq | None = Field(default=None, description="Solo en tiempoReal y para PREGUNTA_FAQ")

    @model_validator(mode="after")
    def _coherencia(self) -> "ResultadoMensaje":
        if self.estado == "ERROR":
            # F4: un error nunca trae una intención inventada
            if any(v is not None for v in (self.intencion, self.confianza, self.sentimiento, self.tema)):
                raise ValueError("Un resultado con estado ERROR no lleva etiquetas")
        elif self.intencion is None or self.confianza is None:
            raise ValueError("Un resultado con estado OK necesita intención y confianza")
        return self


class Metricas(ModeloIa):
    duracion_ms: int = Field(ge=0, description="Lo que tardó todo el lote dentro de la IA")
    tokens_in: int = Field(ge=0, description="Tokens de entrada del clasificador (no incluye al Agente FAQ)")
    tokens_out: int = Field(ge=0, description="Tokens de salida del clasificador (no incluye al Agente FAQ)")


class RespuestaLote(ModeloIa):
    """Lo que devuelve POST /v1/procesar."""

    version_contrato_ia: Literal["1.0"] = Field(description="Cambia si cambia este formato")
    lote_id: str = Field(description="El loteId recibido")
    resultados: list[ResultadoMensaje] = Field(description="Uno por mensaje, en el mismo orden del lote")
    metricas: Metricas


# ── POST /v1/generar (T06, DEC-82): el Agente-Mod redacta un post y un caso de éxito ──

MAX_RESPUESTAS_GENERAR = 20


class PedidoGenerar(ModeloIa):
    """Lo que Java envía a POST /v1/generar: un logro (TESTIMONIO) y, si las hay, las respuestas que recibió."""

    version_contrato: Literal["1.0"] = Field(description="La versión del contrato v1 de las cajas")
    pedido_id: str = Field(min_length=1, max_length=100, description="Lo pone Java; vuelve en la respuesta")
    logro: MensajeContrato = Field(description="La caja del contrato v1 del mensaje del logro, tal cual")
    respuestas: list[MensajeContrato] = Field(
        default_factory=list, max_length=MAX_RESPUESTAS_GENERAR,
        description="Las cajas de los mensajes que responden al logro (respondeA), "
        f"como máximo {MAX_RESPUESTAS_GENERAR}",
    )


class RespuestaGenerar(ModeloIa):
    """Lo que devuelve POST /v1/generar. Un fallo del LLM es ERROR, nunca un borrador vacío ni inventado (F4)."""

    version_contrato_ia: Literal["1.0"] = Field(description="Cambia si cambia este formato")
    pedido_id: str = Field(description="El pedidoId recibido")
    discord_id: str = Field(description="El id del mensaje del logro")
    estado: Estado = Field(description="OK: la IA decidió. ERROR: el LLM falló y no hay decisión ni textos")
    publicable: bool | None = Field(
        default=None, description="true si el logro vale un post (DEC-53). null si estado = ERROR")
    motivo: str = Field(description="Por qué es publicable o no, o el motivo del error")
    post_linkedin: str | None = Field(default=None, description="Borrador del post. Solo si publicable = true")
    caso_exito: str | None = Field(default=None, description="Borrador del caso de éxito. Solo si publicable = true")
    metricas: Metricas

    @model_validator(mode="after")
    def _coherencia(self) -> "RespuestaGenerar":
        textos = (self.post_linkedin, self.caso_exito)
        if self.estado == "ERROR":
            if self.publicable is not None or any(t is not None for t in textos):
                raise ValueError("Un resultado con estado ERROR no lleva decisión ni textos")
        elif self.publicable is None:
            raise ValueError("Un resultado con estado OK necesita publicable")
        elif self.publicable and not all(t and t.strip() for t in textos):
            raise ValueError("Un logro publicable necesita los dos textos")
        elif not self.publicable and any(t is not None for t in textos):
            raise ValueError("Un logro no publicable no lleva textos")
        return self


class ErrorCampo(ModeloIa):
    campo: str = Field(description="Ruta del campo, por ejemplo mensajes.0.autor.tipo")
    problema: str


class ErrorApi(ModeloIa):
    """Formato común de error (análisis §2). Nunca repite los datos recibidos ni detalles internos (S7)."""

    codigo: Literal["CONTRATO_INVALIDO", "NO_AUTORIZADO", "ERROR_INTERNO"]
    mensaje: str
    errores: list[ErrorCampo] = Field(default_factory=list)
    id_correlacion: str = Field(description="El de la cabecera X-Id-Correlacion, o uno nuevo")


def generar_esquema() -> dict:
    """JSON Schema de la respuesta y del error, generado desde los modelos."""
    esquema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"Contrato Java ↔ IA v{VERSION_CONTRATO_IA} — InsightEdu Lab",
        "description": "Salida de POST /v1/procesar. La entrada es el contrato v1 "
        "(ingestion/discord/schema/contract_v1.schema.json).",
        "respuesta": RespuestaLote.model_json_schema(mode="serialization"),
        "error": ErrorApi.model_json_schema(mode="serialization"),
        # T06: POST /v1/generar (solo agrega; /v1/procesar no cambia)
        "generar": {
            "pedido": PedidoGenerar.model_json_schema(mode="validation"),
            "respuesta": RespuestaGenerar.model_json_schema(mode="serialization"),
        },
    }
    return esquema


def esquema_como_texto() -> str:
    return json.dumps(generar_esquema(), ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    ARCHIVO_ESQUEMA.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ESQUEMA.write_text(esquema_como_texto(), encoding="utf-8")
    print(f"JSON Schema escrito en {ARCHIVO_ESQUEMA}")


if __name__ == "__main__":
    main()
