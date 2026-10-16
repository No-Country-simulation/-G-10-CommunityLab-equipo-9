"""
logros.py (T13): agrupar los borradores en tarjetas, contar como Java, escapar el markdown de un nombre y lo que se
dice de LinkedIn. Sin Streamlit: funciones puras.
"""
import re
import string
from datetime import datetime, timedelta, timezone

import pytest

import logros


def _b(id_, tipo, estado="PENDIENTE", mensaje_id=None, creado="2026-10-10T10:00:00Z", revisado=None, **extra):
    return {"id": id_, "tipo": tipo, "estado": estado, "creadoEn": creado, "mensajeId": mensaje_id,
            "autorNombre": "Ana María Pérez", "motivoIa": "Contratación: consiguió su primer trabajo.",
            "semana": "2026-W41" if tipo == "FAQ" else None, "revisadoEn": revisado, **extra}


# ── Agrupar (prueba 1 de la ficha) ──

def test_el_post_y_el_caso_del_mismo_logro_son_una_tarjeta_y_la_faq_otra():
    borradores = [
        _b(1, "POST_LINKEDIN", "APROBADO", 183, "2026-10-01T10:00:00Z", revisado="2026-10-02T10:00:00Z"),
        _b(2, "CASO_EXITO", "PENDIENTE", 183, "2026-10-01T10:00:00Z"),
        _b(3, "POST_LINKEDIN", "PENDIENTE", 256, "2026-10-05T10:00:00Z"),
        _b(4, "CASO_EXITO", "PENDIENTE", 256, "2026-10-05T10:00:00Z"),
        _b(5, "FAQ", "PENDIENTE", None, "2026-10-12T10:00:00Z"),
    ]

    cola = logros.agrupar(borradores, "PENDIENTE")

    assert [t.clave for t in cola] == ["logro-183", "logro-256", "faq-5"]  # del más antiguo al más nuevo
    assert [t.etiqueta("PENDIENTE") for t in cola] == ["Solo caso de éxito", "Post + caso de éxito",
                                                       "FAQ · sin consentimiento"]
    # La tarjeta con un solo texto pendiente trae también el post ya aprobado, para mostrarlo solo para leer
    assert cola[0].tipos == ["POST_LINKEDIN", "CASO_EXITO"] and cola[0].pendientes == ["CASO_EXITO"]
    assert cola[0].nombre == "Ana" and cola[0].titulo == "Ana"  # solo el primer nombre
    assert cola[2].titulo == "FAQ de la semana 2026-W41" and cola[2].es_faq
    assert logros.contar_por_revisar(borradores) == 3  # tarjetas, no borradores (son 4 pendientes)


def test_lo_aprobado_va_primero_lo_ultimo_revisado():
    borradores = [
        _b(1, "POST_LINKEDIN", "APROBADO", 183, revisado="2026-10-02T10:00:00Z"),
        _b(2, "CASO_EXITO", "RECHAZADO", 183, revisado="2026-10-02T10:01:00Z"),
        _b(3, "POST_LINKEDIN", "APROBADO", 256, revisado="2026-10-06T10:00:00Z"),
        _b(4, "CASO_EXITO", "APROBADO", 256, revisado="2026-10-06T10:00:05Z"),
    ]

    aprobados = logros.agrupar(borradores, "APROBADO")
    rechazados = logros.agrupar(borradores, "RECHAZADO")

    assert [t.clave for t in aprobados] == ["logro-256", "logro-183"]
    assert [t.etiqueta("APROBADO") for t in aprobados] == ["Post + caso de éxito", "Solo post"]
    assert [t.clave for t in rechazados] == ["logro-183"]
    assert logros.contar_por_revisar(borradores) == 0


def test_sin_mensaje_id_cada_borrador_es_su_tarjeta():
    # Un Java de antes de T13 no manda mensajeId: el panel no junta, pero no se rompe
    borradores = [_b(1, "POST_LINKEDIN"), _b(2, "CASO_EXITO")]
    for b in borradores:
        del b["mensajeId"]

    assert [t.clave for t in logros.agrupar(borradores, "PENDIENTE")] == ["borrador-1", "borrador-2"]


@pytest.mark.parametrize("nombre, primero", [("Ana María Pérez", "Ana"), ("  Beto ", "Beto"), (None, "Alumno sin nombre"),
                                              ("", "Alumno sin nombre")])
def test_primer_nombre(nombre, primero):
    assert logros.primer_nombre(nombre) == primero


# ── Contar como Java (prueba 6) ──

def test_los_caracteres_se_cuentan_como_java():
    assert logros.caracteres_java("🎉") == 2  # len() de Python diría 1
    assert logros.caracteres_java("¡Ñandú!") == 7
    assert not logros.muy_largo("POST_LINKEDIN", "🎉" * 1500)
    assert logros.muy_largo("POST_LINKEDIN", "🎉" * 1500 + "a")
    assert not logros.muy_largo("CASO_EXITO", "a" * 5000)  # el tope es de LinkedIn


def test_el_contador_dice_las_reglas_de_la_guia_de_voz():
    post = "🎉 " + "palabra " * 99
    assert logros.contador("POST_LINKEDIN", post) == \
        "100 palabras (la guía pide 90 a 160) · 795 de 3.000 caracteres de LinkedIn"
    assert logros.contador("POST_LINKEDIN", "x" * 3001).endswith("3.001 de 3.000 caracteres de LinkedIn")
    assert logros.contador("CASO_EXITO", "una") == "1 palabra (la guía pide 150 a 250) · sin emojis ni hashtags"
    assert logros.contador("FAQ", "dos palabras") == "2 palabras"


# ── Escapar el markdown de un nombre (prueba 7) ──

PELIGROSOS = ["**x**", "[x](http://malo.example)", "![x](http://malo.example/i.png)", "<b>x</b>",
              "<script>alert('hola')</script>", ":red[x]", "$x$", "`x`", "# x", "\\*x\\*"]


def _como_lo_ve_markdown(escapado: str) -> str:
    """CommonMark: una barra invertida delante de un signo de puntuación muestra el signo tal cual."""
    return re.sub(r"\\([" + re.escape(string.punctuation) + "])", r"\1", escapado)


@pytest.mark.parametrize("texto", PELIGROSOS)
def test_un_nombre_escapado_se_ve_tal_cual(texto):
    escapado = logros.escapar_markdown(texto)

    assert _como_lo_ve_markdown(escapado) == texto
    # Ningún signo queda sin su barra: no hay negrita, enlace, imagen, HTML ni color posibles
    sin_escapar = re.sub(r"\\[" + re.escape(string.punctuation) + "]", "", escapado)
    assert not any(c in string.punctuation for c in sin_escapar)


def test_escapar_junta_las_lineas():
    assert logros.escapar_markdown("Ana\n\n# Título") == "Ana \\# Título"
    assert logros.escapar_markdown(None) == ""


# ── LinkedIn (pruebas 3 y 8) ──

@pytest.mark.parametrize("modo, etiqueta, nota, confirmar", [
    ("APAGADO", "Aprobar post", "La publicación en LinkedIn está apagada: aprobar no publica nada.", False),
    ("SIMULADO", "Aprobar post", "LinkedIn está en modo simulado: aprobar no publica nada.", False),
    ("REAL", "Aprobar y publicar en LinkedIn",
     "Al aprobar, el post se publica en público en el LinkedIn de CommunityLab.", True),
    (None, "Aprobar post", "No se pudo saber si LinkedIn está encendido: al aprobar, podría publicarse.", True),
    ("OTRO", "Aprobar post", "No se pudo saber si LinkedIn está encendido: al aprobar, podría publicarse.", True),
])
def test_el_boton_del_post_dice_que_pasara_en_linkedin(modo, etiqueta, nota, confirmar):
    assert logros.boton_post(modo) == (etiqueta, nota, confirmar)


@pytest.mark.parametrize("post_id, enlace", [
    ("urn:li:share:7251234567890123456", "https://www.linkedin.com/feed/update/urn:li:share:7251234567890123456/"),
    ("urn:li:ugcPost:12345", "https://www.linkedin.com/feed/update/urn:li:ugcPost:12345/"),
    ("urn:li:share:abc", None),
    ("urn:li:post:desconocido", None),
    ("urn:li:share:123/../../evil", None),
    ("javascript:alert(1)", None),
    ("https://malo.example/urn:li:share:1", None),
    ("", None),
    (None, None),
    (123, None),
])
def test_el_enlace_a_linkedin_solo_se_arma_con_un_urn_de_post(post_id, enlace):
    assert logros.enlace_linkedin(post_id) == enlace


def test_el_estado_en_linkedin_en_una_frase():
    ahora = datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc)
    hace_un_rato = (ahora - timedelta(seconds=30)).isoformat()
    hace_dias = (ahora - timedelta(days=3)).isoformat()

    assert logros.estado_linkedin({"estado": "PUBLICADO", "en": "2026-10-15T19:00:00Z"}, hace_dias, ahora) == \
        "Publicado en LinkedIn el 2026-10-15 14:00"
    assert logros.estado_linkedin({"estado": "APAGADO"}, hace_dias, ahora) == \
        "No publicado: la publicación en LinkedIn está apagada"
    assert logros.estado_linkedin({"estado": "SIMULADO"}, hace_dias, ahora) == \
        "Simulado: LinkedIn está encendido sin token"
    assert logros.estado_linkedin({"estado": "ERROR", "motivo": "LinkedIn respondió HTTP 401"}, hace_dias, ahora) == \
        "Falló: LinkedIn respondió HTTP 401"
    assert logros.estado_linkedin({"estado": None}, hace_dias, ahora) == \
        "Sin dato (se aprobó antes de que se guardara este estado)"
    assert logros.estado_linkedin(None, None, ahora) == "Sin dato (se aprobó antes de que se guardara este estado)"
    assert logros.estado_linkedin({"estado": None}, hace_un_rato, ahora).startswith("Todavía sin resultado")


@pytest.mark.parametrize("borrador, texto", [
    ({"tipo": "POST_LINKEDIN", "linkedin": {"estado": "PUBLICADO"}}, "Publicado"),
    ({"tipo": "POST_LINKEDIN", "linkedin": {"estado": "APAGADO"}}, "No: apagado"),
    ({"tipo": "POST_LINKEDIN", "linkedin": {"estado": "SIMULADO"}}, "Simulado"),
    ({"tipo": "POST_LINKEDIN", "linkedin": {"estado": "ERROR"}}, "Falló"),
    ({"tipo": "POST_LINKEDIN", "linkedin": {"estado": None}}, "Sin dato"),
    ({"tipo": "POST_LINKEDIN"}, "Sin dato"),  # un Java de antes de T13
    ({"tipo": "CASO_EXITO", "linkedin": None}, "—"),
    ({"tipo": "FAQ", "linkedin": None}, "—"),
])
def test_en_linkedin_corto(borrador, texto):
    assert logros.en_linkedin_corto(borrador) == texto
