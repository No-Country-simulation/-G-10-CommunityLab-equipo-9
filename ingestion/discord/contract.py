"""
Contrato de ingesta v1 escrito como código (docs/CONTRACT.md).

Define con pydantic el formato en que entra cada mensaje de Discord al sistema.
Sirve para dos cosas:
- validar: si un mensaje no cumple el contrato, pydantic dice qué campo falla y por qué;
- publicar la especificación: genera el JSON Schema, el archivo estándar que
  backend (o cualquier lenguaje) usa para saber qué va a recibir.

En el código los campos se escriben al estilo Python (texto_original) y en el
JSON salen al estilo del contrato (textoOriginal): eso es el "alias".

Uso:  python contract.py   → escribe schema/contract_v1.schema.json
"""
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

VERSION_CONTRATO = "1.0"
ARCHIVO_ESQUEMA = Path(__file__).parent / "schema" / "contract_v1.schema.json"

# Los IDs de Discord van como texto: superan el entero más grande que JavaScript maneja sin perder precisión.
IdDiscord = Annotated[str, Field(pattern=r"^\d+$", examples=["1554205178671009863"])]
# Fechas en UTC, con milisegundos y terminadas en Z, como pide la regla 5 del contrato.
FechaUTC = Annotated[
    str,
    Field(
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$",
        json_schema_extra={"format": "date-time"},
        examples=["2026-09-28T18:56:30.331Z"],
    ),
]

Modo = Literal["historial", "tiempoReal"]
TipoMensaje = Literal["mensaje", "respuesta", "avisoSistema", "otro"]
TipoAutor = Literal["persona", "botPropio", "otroBot"]
RolAutor = Literal["miembro", "mentor", "staff"]


class Modelo(BaseModel):
    """Base de todos los modelos del contrato."""

    model_config = ConfigDict(
        alias_generator=to_camel,  # texto_original → textoOriginal
        validate_by_name=True,  # el código puede crear los modelos con los nombres de Python
        validate_by_alias=True,  # y también leer un JSON con los nombres del contrato
        serialize_by_alias=True,  # al convertir a JSON, siempre con los nombres del contrato
        extra="forbid",  # un campo que no está en el contrato es un error
        frozen=True,  # un mensaje ya armado no se modifica
    )


# ── Objetos dentro del mensaje (CONTRACT.md §4) ─────────────────────────────


class Canal(Modelo):
    """Canal donde se escribió el mensaje."""

    id: IdDiscord
    nombre: str = Field(examples=["dudas"])


class Hilo(Modelo):
    """Hilo o publicación de foro. En el MVP no se extraen hilos: el campo va en null (decisión 7)."""

    id: IdDiscord
    nombre: str
    etiquetas: list[str] = Field(description="Nombres de las etiquetas aplicadas; solo en foros")


class Autor(Modelo):
    """Quién escribió el mensaje."""

    id: str = Field(
        min_length=1,
        description="Identidad estable. Persona real: su ID de Discord. Simulado: 'sim-' + nombre normalizado (decisión 1)",
        examples=["sim-ana-perez"],
    )
    id_discord: IdDiscord = Field(description="author.id sin cambios. En los simulados es el ID del webhook")
    nombre_usuario: str = Field(description="author.username")
    nombre_visible: str = Field(description="author.global_name; si no existe, username")
    tipo: TipoAutor = Field(description="persona (incluye a los simulados), botPropio (nuestro bot) u otroBot")
    rol: RolAutor = Field(description="Sale de los roles de Discord del autor al momento de la ingesta (decisión 2)")


class Menciones(Modelo):
    """A quién menciona el mensaje."""

    usuarios: list[IdDiscord]
    roles: list[IdDiscord]
    todos: bool = Field(description="true si menciona a @everyone")


class Adjunto(Modelo):
    """Un archivo adjunto."""

    id: IdDiscord
    nombre: str = Field(examples=["captura.jpg"])
    tipo_contenido: str | None = Field(examples=["image/jpeg"])
    tamano_bytes: int = Field(ge=0)
    ancho: int | None = Field(description="Solo en imágenes y videos")
    alto: int | None = Field(description="Solo en imágenes y videos")
    url: str = Field(description="Temporal: no guardarla como enlace permanente (decisión 3)")
    url_expira_en: FechaUTC | None = Field(description="Cuándo deja de funcionar la url")


class Enlace(Modelo):
    """Un link escrito en el texto."""

    url: str
    dominio: str = Field(description="Sin 'www.'", examples=["github.com"])


class Reaccion(Modelo):
    """Un emoji puesto sobre el mensaje, con su cantidad."""

    emoji: str = Field(description="El emoji; en los personalizados, su nombre", examples=["🎉"])
    emoji_id: IdDiscord | None = Field(description="null si es un emoji estándar")
    cantidad: int = Field(ge=1, description="No dice quién reaccionó")


class VistaPrevia(Modelo):
    """Vista previa de un link (embed). Sin muestras reales todavía (decisión 6)."""

    tipo: str = Field(examples=["link"])
    url: str | None
    titulo: str | None
    descripcion: str | None


class OpcionEncuesta(Modelo):
    """Una opción de una encuesta."""

    texto: str | None
    votos: int = Field(ge=0)


class Encuesta(Modelo):
    """Encuesta del mensaje. Sin muestras reales todavía (decisión 6)."""

    pregunta: str
    opciones: list[OpcionEncuesta]
    finalizada: bool


# ── El mensaje (CONTRACT.md §3) ─────────────────────────────────────────────


class Mensaje(Modelo):
    """1 mensaje de Discord = 1 registro. Siempre van todos los campos."""

    id: IdDiscord = Field(description="ID del mensaje en Discord: único en todo Discord")
    canal: Canal
    hilo: Hilo | None = Field(description="En el MVP siempre null (decisión 7)")
    fecha: FechaUTC = Field(description="Cuándo se escribió")
    tipo: TipoMensaje = Field(description="mensaje (type 0), respuesta (19), avisoSistema (6, 7, 18, 46) u otro")
    tipo_discord: int = Field(description="El type original de Discord")
    es_simulado: bool = Field(description="true si lo publicó uno de nuestros webhooks de simulación")
    autor: Autor
    texto_original: str = Field(description="content sin cambios. Puede venir vacío")
    tiene_texto: bool
    tiene_bloque_codigo: bool
    enlaces: list[Enlace]
    menciones: Menciones
    menciona_al_bot: bool = Field(description="Menciona a nuestro bot o a su rol (decisión 5)")
    responde_a: IdDiscord | None = Field(description="ID del mensaje al que responde; solo en respuestas")
    adjuntos: list[Adjunto]
    reacciones: list[Reaccion]
    fijado: bool
    editado: bool
    editado_en: FechaUTC | None
    stickers: list[str] = Field(description="Nombres de los stickers")
    vistas_previas: list[VistaPrevia]
    encuesta: Encuesta | None


# ── El lote (CONTRACT.md §2) ────────────────────────────────────────────────


class Lote(Modelo):
    """El sobre que lleva los mensajes: muchos en el análisis por lotes, uno en tiempo real."""

    version_contrato: Literal["1.0"] = Field(description="Cambia si cambia el formato, no según el modo")
    lote_id: str = Field(min_length=1, description="ID del envío (UUID): sirve para rastrearlo y detectar reenvíos")
    fuente: Literal["discord"]
    modo: Modo
    servidor_id: IdDiscord
    generado_en: FechaUTC = Field(description="Cuándo se armó el lote")
    mensajes: list[Mensaje] = Field(min_length=1)


def generar_esquema() -> dict:
    """El JSON Schema del lote, con los nombres de campo del contrato."""
    esquema = Lote.model_json_schema(mode="serialization")
    esquema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    esquema["title"] = f"Contrato de ingesta de Discord v{VERSION_CONTRATO} — InsightEdu Lab"
    return esquema


def main() -> None:
    ARCHIVO_ESQUEMA.parent.mkdir(exist_ok=True)
    ARCHIVO_ESQUEMA.write_text(json.dumps(generar_esquema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ JSON Schema escrito en {ARCHIVO_ESQUEMA.relative_to(Path(__file__).parent)}")


if __name__ == "__main__":
    main()
