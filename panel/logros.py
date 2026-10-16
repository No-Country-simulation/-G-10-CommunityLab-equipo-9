"""
La lógica de la página Borradores (T13, DEC-159), sin dibujar nada: así se prueba sola.

- Juntar los borradores en tarjetas: una por logro (el post y el caso de éxito del mismo mensaje de Discord) y una
  por FAQ semanal.
- Contar como Java: los caracteres en UTF-16 (String.length()), para el tope de 3.000 de LinkedIn.
- Escapar el markdown de un nombre antes de ponerlo en una etiqueta (st.checkbox, st.success, st.button…): las
  etiquetas de Streamlit interpretan markdown, con enlaces e imágenes incluidos.
- Qué dice el botón del post según el modo de LinkedIn, y el estado guardado de cada post (M12, DEC-160).
"""
from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import ui

POST, CASO, FAQ = "POST_LINKEDIN", "CASO_EXITO", "FAQ"
MAX_LINKEDIN = 3000

NOMBRES = {POST: "Post de LinkedIn", CASO: "Caso de éxito", FAQ: "FAQ semanal"}
# Para los avisos: "Post aprobado", "Caso de éxito rechazado", "FAQ aprobada"
SUJETOS = {POST: ("Post", "o"), CASO: ("Caso de éxito", "o"), FAQ: ("FAQ", "a")}
# Para "Falta revisar el caso de éxito"
CON_ARTICULO = {POST: "el post", CASO: "el caso de éxito", FAQ: "la FAQ"}


@dataclass
class Tarjeta:
    """Un logro (sus textos, por tipo) o una FAQ semanal. textos: el resumen de cada borrador, como lo lista Java."""
    clave: str
    textos: dict[str, dict] = field(default_factory=dict)

    @property
    def es_faq(self) -> bool:
        return FAQ in self.textos

    def en_estado(self, estado: str) -> list[str]:
        """Los tipos de esta tarjeta que están en ese estado, en el orden de las pestañas (post, caso, FAQ)."""
        return [t for t in (POST, CASO, FAQ) if t in self.textos and self.textos[t]["estado"] == estado]

    @property
    def pendientes(self) -> list[str]:
        return self.en_estado("PENDIENTE")

    @property
    def tipos(self) -> list[str]:
        return [t for t in (POST, CASO, FAQ) if t in self.textos]

    @property
    def primero(self) -> dict:
        return self.textos[self.tipos[0]]

    @property
    def nombre(self) -> str:
        """El primer nombre del alumno (la primera palabra de su nombre visible). Nunca el apellido."""
        return primer_nombre(self.primero.get("autorNombre"))

    @property
    def titulo(self) -> str:
        if self.es_faq:
            return f"FAQ de la semana {self.primero.get('semana') or '—'}"
        return self.nombre

    @property
    def motivo(self) -> str | None:
        return next((b.get("motivoIa") for b in self.textos.values() if b.get("motivoIa")), None)

    @property
    def creado(self) -> str:
        return min(b["creadoEn"] for b in self.textos.values())

    def etiqueta(self, estado: str) -> str:
        """Qué textos de la tarjeta están en el estado de la cola: "Post + caso de éxito", "Solo post"…"""
        if self.es_faq:
            return "FAQ · sin consentimiento"
        tipos = self.en_estado(estado)
        if tipos == [POST, CASO]:
            return "Post + caso de éxito"
        return "Solo post" if tipos == [POST] else "Solo caso de éxito"


def primer_nombre(autor_nombre: str | None) -> str:
    partes = (autor_nombre or "").split()
    return partes[0] if partes else "Alumno sin nombre"


def agrupar(borradores: list[dict], estado: str) -> list[Tarjeta]:
    """
    Las tarjetas que tienen algún texto en `estado`. borradores: todos los que se conocen, de los tres estados (así
    una tarjeta por revisar muestra también el texto que ya se aprobó). Lo pendiente, del más antiguo al más nuevo;
    lo aprobado y lo rechazado, lo último revisado primero.
    """
    tarjetas: dict[str, Tarjeta] = {}
    for b in sorted(borradores, key=lambda x: x["id"]):
        if b["tipo"] == FAQ:
            clave = f"faq-{b['id']}"
        elif b.get("mensajeId") is not None:
            clave = f"logro-{b['mensajeId']}"
        else:
            clave = f"borrador-{b['id']}"  # un Java sin mensajeId: un borrador por tarjeta
        t = tarjetas.setdefault(clave, Tarjeta(clave))
        anterior = t.textos.get(b["tipo"])
        # Si un logro tuviera dos textos del mismo tipo, se queda el pendiente (o el más nuevo)
        if anterior is None or anterior["estado"] != "PENDIENTE" or b["estado"] == "PENDIENTE":
            t.textos[b["tipo"]] = b
    elegidas = [t for t in tarjetas.values() if t.en_estado(estado)]
    if estado == "PENDIENTE":
        return sorted(elegidas, key=lambda t: (min(t.textos[x]["creadoEn"] for x in t.pendientes),
                                               min(b["id"] for b in t.textos.values())))
    return sorted(elegidas, key=lambda t: max(t.textos[x].get("revisadoEn") or "" for x in t.en_estado(estado)),
                  reverse=True)


def contar_por_revisar(pendientes: list[dict]) -> int:
    """Cuántas tarjetas hay por revisar: el número de la barra lateral y de la píldora "Por revisar (n)"."""
    return len(agrupar(pendientes, "PENDIENTE"))


# ── Contar como Java y como la guía de voz ──

def caracteres_java(texto: str) -> int:
    """Como String.length() de Java: en unidades UTF-16. Un emoji como 🎉 cuenta 2 (len() de Python diría 1)."""
    return len(texto.encode("utf-16-le")) // 2


def palabras(texto: str) -> int:
    return len(texto.split())


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def contador(tipo: str, texto: str) -> str:
    """Las reglas de la guía de voz (agents/agent_mod/guia_de_voz.md), a la vista."""
    n = palabras(texto)
    cuantas = "1 palabra" if n == 1 else f"{n} palabras"
    if tipo == POST:
        return (f"{cuantas} (la guía pide 90 a 160) · {_miles(caracteres_java(texto))} de 3.000 caracteres "
                f"de LinkedIn")
    if tipo == CASO:
        return f"{cuantas} (la guía pide 150 a 250) · sin emojis ni hashtags"
    return cuantas


def muy_largo(tipo: str, texto: str) -> bool:
    """Un post que LinkedIn no aceptaría: no se deja aprobar (DEC-160)."""
    return tipo == POST and caracteres_java(texto) > MAX_LINKEDIN


# ── Etiquetas con datos (DEC-158) ──

_PUNTUACION = re.compile("([" + re.escape(string.punctuation) + "])")


def escapar_markdown(texto: str | None) -> str:
    """
    Un texto de un alumno listo para una etiqueta de Streamlit, que interpreta markdown: cada signo de puntuación
    lleva una barra invertida delante (así **x**, [x](http://…), ![x](…), <b> o :red[x] se ven tal cual) y los
    saltos de línea pasan a espacios.
    """
    return _PUNTUACION.sub(r"\\\1", " ".join((texto or "").split()))


# ── LinkedIn ──

def boton_post(modo: str | None) -> tuple[str, str, bool]:
    """
    Qué dice el botón del post antes de aprobar (decisión 2b): su etiqueta, la nota de debajo y si hay que confirmar.
    Sin el modo (Java no lo dijo), se confirma igual que en REAL: podría publicarse.
    """
    if modo == "APAGADO":
        return "Aprobar post", "La publicación en LinkedIn está apagada: aprobar no publica nada.", False
    if modo == "SIMULADO":
        return "Aprobar post", "LinkedIn está en modo simulado: aprobar no publica nada.", False
    if modo == "REAL":
        return ("Aprobar y publicar en LinkedIn",
                "Al aprobar, el post se publica en público en el LinkedIn de CommunityLab.", True)
    return "Aprobar post", "No se pudo saber si LinkedIn está encendido: al aprobar, podría publicarse.", True


_URN_POST = re.compile(r"urn:li:(share|ugcPost):[0-9]+")


def enlace_linkedin(post_id: str | None) -> str | None:
    """El enlace al post, solo si su URN es urn:li:share:<números> o urn:li:ugcPost:<números>."""
    if not isinstance(post_id, str) or not _URN_POST.fullmatch(post_id):
        return None
    return f"https://www.linkedin.com/feed/update/{post_id}/"


ESTADOS_CORTOS = {"PUBLICADO": "Publicado", "APAGADO": "No: apagado", "SIMULADO": "Simulado", "ERROR": "Falló"}


def en_linkedin_corto(b: dict) -> str:
    """La columna "En LinkedIn" del dashboard: Publicado, No: apagado, Simulado, Falló o Sin dato ("—" sin post)."""
    if b.get("tipo") != POST:
        return "—"
    return ESTADOS_CORTOS.get((b.get("linkedin") or {}).get("estado"), "Sin dato")


def estado_linkedin(linkedin: dict | None, aprobado_en: str | None, ahora: datetime | None = None) -> str:
    """Qué pasó con un post aprobado en LinkedIn, en una frase."""
    linkedin = linkedin or {}
    estado = linkedin.get("estado")
    if estado == "PUBLICADO":
        return f"Publicado en LinkedIn el {ui.fecha(linkedin.get('en'))}"
    if estado == "APAGADO":
        return "No publicado: la publicación en LinkedIn está apagada"
    if estado == "SIMULADO":
        return "Simulado: LinkedIn está encendido sin token"
    if estado == "ERROR":
        return f"Falló: {linkedin.get('motivo') or 'sin motivo'}"
    # Sin dato: o Java todavía lo está enviando (se aprobó hace un momento), o se aprobó antes de la V9
    ahora = ahora or datetime.now(timezone.utc)
    try:
        reciente = ahora - datetime.fromisoformat((aprobado_en or "").replace("Z", "+00:00")) < timedelta(minutes=2)
    except ValueError:
        reciente = False
    if reciente:
        return "Todavía sin resultado: Java lo está enviando. Actualiza la página en unos segundos."
    return "Sin dato (se aprobó antes de que se guardara este estado)"
