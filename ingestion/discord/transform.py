"""
Transforma un mensaje de Discord, tal como lo entrega la API, al contrato de ingesta v1.

Son funciones puras: no se conectan a internet ni leen archivos. Todo lo que
necesitan de afuera (nuestros webhooks, el ID del bot, los roles de cada autor)
llega en un Contexto. Así se pueden probar con mensajes de ejemplo y siempre
dan el mismo resultado.

La misma función sirve para los dos modos: el análisis por lotes y el bot en vivo.
"""
import re
import unicodedata
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from contract import (
    VERSION_CONTRATO,
    Adjunto,
    Autor,
    Canal,
    Encuesta,
    Enlace,
    Lote,
    Menciones,
    Mensaje,
    Modo,
    OpcionEncuesta,
    Reaccion,
    VistaPrevia,
)

# type de Discord → tipo del contrato (CONTRACT.md §5). Cualquier otro type es "otro".
TIPOS = {0: "mensaje", 19: "respuesta", 6: "avisoSistema", 7: "avisoSistema", 18: "avisoSistema", 46: "avisoSistema"}
TIPO_RESPUESTA = 19
# Un link termina en el primer espacio; se le quitan los signos que suelen pegarse al final ("…el repo: https://x.com.").
PATRON_ENLACE = re.compile(r"https?://[^\s<>\"']+")
SIGNOS_FINALES = ".,;:!?)]}*_~"


@dataclass(frozen=True)
class Contexto:
    """Lo que la transformación necesita saber además del mensaje."""

    webhooks_propios: frozenset[str] = frozenset()
    bot_id: str | None = None
    rol_bot_id: str | None = None
    # ID de Discord del autor → IDs de sus roles. Lo guarda extract.py en data/raw/context.json.
    roles_por_autor: Mapping[str, list[str]] = field(default_factory=dict)
    roles_mentor: frozenset[str] = frozenset()
    roles_staff: frozenset[str] = frozenset()
    mentores_simulados: frozenset[str] = frozenset()


# ── Ayudas ──────────────────────────────────────────────────────────────────


def fecha_utc(iso: str | None) -> str | None:
    """'2026-09-28T18:56:30.331000+00:00' → '2026-09-28T18:56:30.331Z'."""
    if iso is None:
        return None
    fecha = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return fecha.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ahora_utc() -> str:
    return fecha_utc(datetime.now(timezone.utc).isoformat())


def normalizar(texto: str) -> str:
    """'Andrés (Mentor)' → 'andres-mentor': sin tildes, en minúsculas y con guiones."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def expiracion(url: str) -> str | None:
    """Vencimiento de la URL de un adjunto: el parámetro ex es un tiempo Unix en hexadecimal."""
    ex = parse_qs(urlparse(url).query).get("ex")
    if not ex:
        return None
    return fecha_utc(datetime.fromtimestamp(int(ex[0], 16), tz=timezone.utc).isoformat())


def extraer_enlaces(texto: str) -> list[Enlace]:
    enlaces = []
    for url in PATRON_ENLACE.findall(texto):
        url = url.rstrip(SIGNOS_FINALES)
        dominio = urlparse(url).netloc.lower().removeprefix("www.")
        if dominio:
            enlaces.append(Enlace(url=url, dominio=dominio))
    return enlaces


# ── Reglas del autor ────────────────────────────────────────────────────────


def es_simulado(crudo: dict, ctx: Contexto) -> bool:
    """Solo nuestros webhooks son simulación. Un webhook ajeno (por ejemplo, de GitHub) no lo es."""
    return crudo.get("webhook_id") in ctx.webhooks_propios


def tipo_de_autor(crudo: dict, simulado: bool, ctx: Contexto) -> str:
    autor = crudo["author"]
    if simulado:
        return "persona"  # un alumno simulado representa a una persona
    if ctx.bot_id and autor["id"] == ctx.bot_id:
        return "botPropio"
    if autor.get("bot") or crudo.get("webhook_id"):
        return "otroBot"
    return "persona"


def rol_de_autor(autor_id: str, id_discord: str, simulado: bool, ctx: Contexto) -> str:
    """Staff gana sobre mentor. Los simulados no tienen roles: usan la lista de respaldo."""
    if simulado:
        return "mentor" if autor_id in ctx.mentores_simulados else "miembro"
    roles = set(ctx.roles_por_autor.get(id_discord, []))
    if roles & ctx.roles_staff:
        return "staff"
    if roles & ctx.roles_mentor:
        return "mentor"
    return "miembro"


def armar_autor(crudo: dict, simulado: bool, ctx: Contexto) -> Autor:
    autor = crudo["author"]
    # Un webhook firma todos sus mensajes con su propio ID: la identidad del simulado sale de su nombre (decisión 1).
    autor_id = f"sim-{normalizar(autor['username'])}" if simulado else autor["id"]
    return Autor(
        id=autor_id,
        id_discord=autor["id"],
        nombre_usuario=autor["username"],
        nombre_visible=autor.get("global_name") or autor["username"],
        tipo=tipo_de_autor(crudo, simulado, ctx),
        rol=rol_de_autor(autor_id, autor["id"], simulado, ctx),
    )


# ── Partes del mensaje ──────────────────────────────────────────────────────


def armar_adjuntos(crudo: dict) -> list[Adjunto]:
    return [
        Adjunto(
            id=a["id"],
            nombre=a["filename"],
            tipo_contenido=a.get("content_type"),
            tamano_bytes=a["size"],
            ancho=a.get("width"),
            alto=a.get("height"),
            url=a["url"],
            url_expira_en=expiracion(a["url"]),
        )
        for a in crudo.get("attachments", [])
    ]


def armar_reacciones(crudo: dict) -> list[Reaccion]:
    # Discord no manda "reactions" cuando nadie reaccionó: el contrato lo convierte en [].
    return [
        Reaccion(emoji=r["emoji"].get("name") or "", emoji_id=r["emoji"].get("id"), cantidad=r["count"])
        for r in crudo.get("reactions", [])
    ]


def armar_vistas_previas(crudo: dict) -> list[VistaPrevia]:
    return [
        # Si el embed no trae type, se usa "rich", el tipo genérico de Discord.
        VistaPrevia(tipo=e.get("type", "rich"), url=e.get("url"), titulo=e.get("title"), descripcion=e.get("description"))
        for e in crudo.get("embeds", [])
    ]


def armar_encuesta(crudo: dict) -> Encuesta | None:
    """Sigue la documentación de Discord: todavía no hay encuestas reales en la muestra (decisión 6)."""
    encuesta = crudo.get("poll")
    if not encuesta:
        return None
    resultados = encuesta.get("results") or {}
    votos = {c["id"]: c["count"] for c in resultados.get("answer_counts", [])}
    return Encuesta(
        pregunta=encuesta["question"].get("text") or "",
        opciones=[
            OpcionEncuesta(texto=r["poll_media"].get("text"), votos=votos.get(r["answer_id"], 0))
            for r in encuesta.get("answers", [])
        ],
        finalizada=bool(resultados.get("is_finalized", False)),
    )


def menciona_al_bot(crudo: dict, ctx: Contexto) -> bool:
    """Al escribir @ Discord sugiere el bot y su rol con el mismo nombre: valen los dos (decisión 5)."""
    usuarios = {u["id"] for u in crudo.get("mentions", [])}
    roles = set(crudo.get("mention_roles", []))
    return bool((ctx.bot_id and ctx.bot_id in usuarios) or (ctx.rol_bot_id and ctx.rol_bot_id in roles))


# ── Transformación principal ────────────────────────────────────────────────


def a_contrato(crudo: dict, canal_nombre: str, ctx: Contexto) -> Mensaje:
    """Convierte un mensaje crudo de Discord en un Mensaje del contrato.

    Si el resultado no cumple el contrato, pydantic lanza ValidationError con el detalle.
    """
    simulado = es_simulado(crudo, ctx)
    texto = crudo.get("content", "")
    referencia = crudo.get("message_reference") or {}
    return Mensaje(
        id=crudo["id"],
        canal=Canal(id=crudo["channel_id"], nombre=canal_nombre),
        hilo=None,  # MVP: los hilos no se extraen (decisión 7)
        fecha=fecha_utc(crudo["timestamp"]),
        tipo=TIPOS.get(crudo["type"], "otro"),
        tipo_discord=crudo["type"],
        es_simulado=simulado,
        autor=armar_autor(crudo, simulado, ctx),
        texto_original=texto,
        tiene_texto=bool(texto.strip()),
        tiene_bloque_codigo="```" in texto,
        enlaces=extraer_enlaces(texto),
        menciones=Menciones(
            usuarios=[u["id"] for u in crudo.get("mentions", [])],
            roles=crudo.get("mention_roles", []),
            todos=crudo.get("mention_everyone", False),
        ),
        menciona_al_bot=menciona_al_bot(crudo, ctx),
        # Solo las respuestas: un aviso de "fijó un mensaje" también trae message_reference, pero no responde a nadie.
        responde_a=referencia.get("message_id") if crudo["type"] == TIPO_RESPUESTA else None,
        adjuntos=armar_adjuntos(crudo),
        reacciones=armar_reacciones(crudo),
        fijado=crudo.get("pinned", False),
        editado=crudo.get("edited_timestamp") is not None,
        editado_en=fecha_utc(crudo.get("edited_timestamp")),
        stickers=[s["name"] for s in crudo.get("sticker_items", [])],
        vistas_previas=armar_vistas_previas(crudo),
        encuesta=armar_encuesta(crudo),
    )


def armar_lote(mensajes: list[Mensaje], modo: Modo, servidor_id: str) -> Lote:
    """Envuelve los mensajes en un lote, ordenados del más antiguo al más reciente."""
    return Lote(
        version_contrato=VERSION_CONTRATO,
        lote_id=str(uuid.uuid4()),
        fuente="discord",
        modo=modo,
        servidor_id=servidor_id,
        generado_en=ahora_utc(),
        # Los IDs de Discord crecen con el tiempo: ordenar por ID es ordenar por fecha.
        mensajes=sorted(mensajes, key=lambda m: int(m.id)),
    )
