"""Reglas de la transformación: cada prueba es un caso del contrato (docs/CONTRACT.md)."""
from datos_prueba import (
    BOT_ID,
    PERSONA_REAL_ID,
    ROL_BOT_ID,
    ROL_MENTOR_ID,
    ROL_STAFF_ID,
    WEBHOOK_AJENO,
    WEBHOOK_DUDAS,
    contexto,
    crudo,
    crudo_real,
)
from transform import a_contrato


def test_duda_simulada():
    m = a_contrato(crudo(), "dudas", contexto())
    assert m.es_simulado is True
    assert m.autor.id == "sim-ana-perez"  # decisión 1: la identidad sale del nombre
    assert m.autor.id_discord == WEBHOOK_DUDAS  # el ID original es el del webhook
    assert m.autor.tipo == "persona"
    assert m.autor.rol == "miembro"
    assert m.tipo == "mensaje"
    assert m.fecha == "2026-09-28T18:56:30.331Z"  # UTC, milisegundos y Z
    assert m.canal.nombre == "dudas"
    assert m.hilo is None  # decisión 7
    assert m.reacciones == [] and m.responde_a is None and m.encuesta is None


def test_mentor_simulado_usa_la_lista_de_respaldo():
    m = a_contrato(crudo(author={"id": WEBHOOK_DUDAS, "username": "Andrés (Mentor)", "bot": True}), "dudas", contexto())
    assert m.autor.id == "sim-andres-mentor"
    assert m.autor.rol == "mentor"


def test_respuesta_real_editada():
    m = a_contrato(
        crudo_real(
            type=19,
            content="Que necesitas @Ana Pérez ?",
            message_reference={"type": 0, "channel_id": "1554158212742127821", "message_id": "1554205273621667853"},
            edited_timestamp="2026-09-28T21:25:19.495000+00:00",
        ),
        "dudas",
        contexto(),
    )
    assert m.es_simulado is False
    assert m.autor.id == PERSONA_REAL_ID  # una persona real conserva su ID de Discord
    assert m.autor.nombre_visible == "Persona Real"  # global_name
    assert m.autor.rol == "mentor"  # decisión 2: sale de sus roles de Discord
    assert m.tipo == "respuesta"
    assert m.responde_a == "1554205273621667853"
    assert m.editado is True
    assert m.editado_en == "2026-09-28T21:25:19.495Z"


def test_staff_gana_sobre_mentor():
    ctx = contexto(roles_por_autor={PERSONA_REAL_ID: [ROL_MENTOR_ID, ROL_STAFF_ID]})
    assert a_contrato(crudo_real(), "dudas", ctx).autor.rol == "staff"


def test_persona_sin_roles_es_miembro():
    ctx = contexto(roles_por_autor={})
    assert a_contrato(crudo_real(), "dudas", ctx).autor.rol == "miembro"


def test_imagen_sin_texto_fijada():
    adjunto = {
        "id": "1554243551888416798",
        "filename": "captura.jpg",
        "size": 97526,
        "url": "https://cdn.discordapp.com/attachments/1/2/captura.jpg?ex=6abc2d9b&is=6abadc1b&hm=abc",
        "width": 831,
        "height": 1080,
        "content_type": "image/jpeg",
    }
    m = a_contrato(crudo_real(content="", attachments=[adjunto], pinned=True), "dudas", contexto())
    assert m.tiene_texto is False
    assert m.fijado is True
    assert m.adjuntos[0].nombre == "captura.jpg"
    # decisión 3: ex=6abc2d9b es la fecha de vencimiento en hexadecimal
    assert m.adjuntos[0].url_expira_en == "2026-09-29T21:28:59.000Z"


def test_aviso_de_fijado_no_es_una_respuesta():
    m = a_contrato(
        crudo_real(type=6, content="", message_reference={"channel_id": "1554158212742127821", "message_id": "1"}),
        "dudas",
        contexto(),
    )
    assert m.tipo == "avisoSistema"  # decisión 4: se envía marcado, sin filtrarlo
    assert m.responde_a is None


def test_tipo_desconocido_es_otro():
    m = a_contrato(crudo(type=99), "dudas", contexto())
    assert m.tipo == "otro" and m.tipo_discord == 99


def test_menciona_al_rol_del_bot():
    # decisión 5: al escribir @ es fácil elegir el rol del bot en lugar del bot
    assert a_contrato(crudo_real(mention_roles=[ROL_BOT_ID]), "dudas", contexto()).menciona_al_bot is True


def test_menciona_al_bot():
    m = a_contrato(crudo_real(mentions=[{"id": BOT_ID, "username": "InsightEdu Ingesta"}]), "dudas", contexto())
    assert m.menciona_al_bot is True
    assert m.menciones.usuarios == [BOT_ID]


def test_mencionar_otro_rol_no_llama_al_bot():
    assert a_contrato(crudo_real(mention_roles=[ROL_MENTOR_ID]), "dudas", contexto()).menciona_al_bot is False


def test_webhook_ajeno_no_es_simulado():
    m = a_contrato(
        crudo(webhook_id=WEBHOOK_AJENO, author={"id": WEBHOOK_AJENO, "username": "GitHub", "bot": True}),
        "dudas",
        contexto(),
    )
    assert m.es_simulado is False  # solo nuestros webhooks son simulación
    assert m.autor.tipo == "otroBot"
    assert m.autor.id == WEBHOOK_AJENO


def test_mensaje_de_nuestro_bot():
    m = a_contrato(crudo_real(author={"id": BOT_ID, "username": "InsightEdu Ingesta", "bot": True}), "dudas", contexto())
    assert m.autor.tipo == "botPropio"


def test_enlaces_con_dominio_y_sin_signos_finales():
    m = a_contrato(crudo(content="Acá el repo: https://www.github.com/usuario/proyecto. ¿Lo revisan?"), "dudas", contexto())
    assert [(e.url, e.dominio) for e in m.enlaces] == [("https://www.github.com/usuario/proyecto", "github.com")]


def test_bloque_de_codigo():
    assert a_contrato(crudo(content="```java\nint x = 1;\n```"), "dudas", contexto()).tiene_bloque_codigo is True


def test_reacciones():
    m = a_contrato(crudo(reactions=[{"emoji": {"id": None, "name": "🎉"}, "count": 5}]), "logros", contexto())
    assert [(r.emoji, r.emoji_id, r.cantidad) for r in m.reacciones] == [("🎉", None, 5)]


def test_el_json_usa_los_nombres_del_contrato():
    datos = a_contrato(crudo(), "dudas", contexto()).model_dump(mode="json")
    assert "textoOriginal" in datos and "esSimulado" in datos and "mencionaAlBot" in datos
    assert "idDiscord" in datos["autor"]
    assert "texto_original" not in datos
