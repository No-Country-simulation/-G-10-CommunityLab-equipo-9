"""
Contrato Java ↔ IA v1 (docs/contratos/JAVA_IA_v1.md).

- Entrada de POST /v1/procesar: el Lote del contrato v1 de la ingesta. Se importa de
  ingestion/discord/contract.py, la única definición: aquí no se copia.
- Salida: los modelos de este archivo, con los nombres en camelCase igual que el contrato v1.

Uso:  python -m agents.orquestador.contrato_ia   → escribe docs/contratos/JAVA_IA_v1.schema.json
"""
from __future__ import annotations

import json
from datetime import date
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


# ── POST /v1/faq (T06b, DEC-97): la FAQ semanal con las dudas repetidas ──

MAX_DUDAS_FAQ = 200
MAX_TEXTO_DUDA = 4000  # el tope de Discord para un mensaje
OrigenRespuesta = Literal["bot", "agenteFaq"]


class RespuestaGuardada(ModeloIa):
    """La respuesta que el bot ya publicó para esa duda (mensajes.respuesta_texto y respuesta_fuentes, T05)."""

    texto: str = Field(min_length=1, max_length=8000, description="El texto que publicó el bot")
    fuentes: list[str] = Field(default_factory=list, max_length=20, description="Documento y página")


class DudaSemana(ModeloIa):
    """Una duda de la semana. No lleva nombres, usuarios ni IDs: el autor es una clave opaca."""

    autor: str = Field(
        pattern=r"^a[0-9]{1,6}$",
        description="Clave opaca del autor dentro de este pedido (a1, a2…). Sirve solo para contar "
        "personas distintas (DEC-98). Nunca el nombre, el usuario ni el ID de Discord",
    )
    texto: str = Field(min_length=1, max_length=MAX_TEXTO_DUDA, description="El texto de la duda")
    tema: Tema | None = Field(default=None, description="El tema que le puso el clasificador")
    respuesta: RespuestaGuardada | None = Field(
        default=None, description="Solo si el bot ya la respondió con respaldo (respuesta_estado = RESPONDIDA)")


class PedidoFaq(ModeloIa):
    """Lo que Java envía a POST /v1/faq: las dudas de los últimos días."""

    pedido_id: str = Field(min_length=1, max_length=100, description="Lo pone Java; vuelve en la respuesta")
    semana: str = Field(min_length=1, max_length=20, description="La semana de la FAQ, por ejemplo 2026-W40")
    desde: date = Field(description="Primer día de la ventana de dudas (para el título)")
    hasta: date = Field(description="Último día de la ventana de dudas (para el título)")
    dudas: list[DudaSemana] = Field(max_length=MAX_DUDAS_FAQ,
                                    description=f"Las dudas de la ventana, como máximo {MAX_DUDAS_FAQ}")

    @model_validator(mode="after")
    def _fechas(self) -> "PedidoFaq":
        if self.desde > self.hasta:
            raise ValueError("desde no puede ser posterior a hasta")
        return self


class GrupoFaq(ModeloIa):
    """Una pregunta repetida por al menos 2 personas."""

    pregunta: str = Field(description="La pregunta del grupo, escrita por la IA, sin nombres")
    personas: int = Field(ge=2, description="Cuántas personas distintas la hicieron")
    respondida: bool = Field(description="true si tiene una respuesta con respaldo en los documentos")
    origen: OrigenRespuesta | None = Field(
        default=None, description="bot: la respuesta que ya publicó el bot. agenteFaq: la buscó el Agente FAQ. "
        "null si no tiene respuesta")
    fuentes: list[str] = Field(default_factory=list, description="Solo el nombre del documento y la página")
    motivo: str | None = Field(default=None, description="Por qué no tiene respuesta")

    @model_validator(mode="after")
    def _coherencia(self) -> "GrupoFaq":
        if self.respondida != (self.origen is not None):
            raise ValueError("Un grupo respondido lleva su origen, y uno sin respuesta no")
        return self


class RespuestaFaqSemanal(ModeloIa):
    """Lo que devuelve POST /v1/faq. Un fallo es ERROR, nunca un borrador a medias (F4)."""

    version_contrato_ia: Literal["1.0"] = Field(description="Cambia si cambia este formato")
    pedido_id: str = Field(description="El pedidoId recibido")
    semana: str = Field(description="La semana recibida")
    estado: Estado = Field(description="OK: la IA terminó. ERROR: no se pudieron agrupar las dudas")
    texto: str | None = Field(
        default=None, description="El borrador de la FAQ en Markdown. null si no hubo preguntas repetidas o si ERROR")
    motivo: str = Field(description="Qué pasó: cuántas preguntas repetidas hubo, por qué no hay texto o el error")
    grupos: list[GrupoFaq] = Field(default_factory=list, description="Las preguntas repetidas, de la más repetida "
                                   "a la menos repetida")
    metricas: Metricas

    @model_validator(mode="after")
    def _coherencia(self) -> "RespuestaFaqSemanal":
        if self.estado == "ERROR":
            if self.texto is not None or self.grupos:
                raise ValueError("Un resultado con estado ERROR no lleva texto ni grupos")
        elif bool(self.grupos) != bool(self.texto and self.texto.strip()):
            raise ValueError("Hay texto si y solo si hay preguntas repetidas")
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
        # T06b: POST /v1/faq (solo agrega; /v1/procesar y /v1/generar no cambian)
        "faq": {
            "pedido": PedidoFaq.model_json_schema(mode="validation"),
            "respuesta": RespuestaFaqSemanal.model_json_schema(mode="serialization"),
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
