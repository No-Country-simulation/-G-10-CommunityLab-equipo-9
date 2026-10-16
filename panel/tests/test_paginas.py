"""
El panel completo con streamlit.testing (AppTest), sin Java real: un cliente simulado ocupa su lugar.
Inicio de sesión, la página Borradores por logro (T13: tarjetas, botones por texto, un consentimiento, el aviso de
LinkedIn y textos escapados) y la página de errores.
"""
import time
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import auth
import logros
import ui
from cliente_java import ErrorJava

APP = str(Path(__file__).resolve().parent.parent / "app.py")
CONTRASENA = "clave-de-prueba-larga"
USUARIOS = auth.con_usuario("", "harrison", auth.crear_registro(CONTRASENA))
SCRIPT = "<script>alert('hola')</script>"
TIPOS_LOGRO = ("POST_LINKEDIN", "CASO_EXITO")

# El ejemplo de la ficha: el logro 183 ya tiene el post aprobado y le falta el caso; el 256 tiene los dos por
# revisar; y una FAQ. Son 3 tarjetas por revisar (4 borradores)
LOGRO_A, LOGRO_B, FAQ = "logro-183", "logro-256", "faq-5"


def _resumen(id_, tipo, mensaje_id, creado, estado="PENDIENTE", autor="Camila Rojas", semana=None):
    return {"id": id_, "tipo": tipo, "estado": estado, "creadoEn": creado, "extracto": "…",
            "autorNombre": None if tipo == "FAQ" else autor, "canal": None if tipo == "FAQ" else "logros",
            "semana": semana, "revisadoPor": None, "revisadoEn": None, "mensajeId": mensaje_id,
            "motivoIa": "3 preguntas repetidas." if tipo == "FAQ" else "Contratación: consiguió su primer trabajo.",
            "linkedin": {"estado": None, "postId": None, "en": None, "motivo": None} if tipo == "POST_LINKEDIN"
            else None}


def _detalle(r, texto_original="me contrataron!!!"):
    faq = r["tipo"] == "FAQ"
    return {
        "id": r["id"], "tipo": r["tipo"], "estado": r["estado"], "requiereConsentimiento": not faq,
        "textoIa": f"Borrador {r['id']} de la IA", "textoFinal": None, "consentimientoConfirmado": False,
        "creadoEn": r["creadoEn"], "aprobadoPor": None, "aprobadoEn": None, "tiempoCuraduriaSeg": None,
        "rechazadoPor": None, "rechazadoEn": None, "motivoRechazo": None, "motivoIa": r["motivoIa"],
        "origen": None if faq else {"discordId": "1", "canal": "logros", "fecha": "2026-09-28T18:58:11Z",
                                    "texto": texto_original, "autorNombre": r["autorNombre"]},
        "faq": {"semana": "2026-W41", "desde": "2026-10-05T13:00:00Z", "hasta": "2026-10-12T13:00:00Z",
                "motivo": "3 repetidas."} if faq else None,
        "oci": {"generados": "SUBIDO", "aprobados": None},  # T09: solo el estado, nunca la ruta ni la PAR
        "linkedin": r["linkedin"],
    }


class JavaSimulado:
    """Hace de API Java: guarda lo que el panel le pide."""

    def __init__(self, borradores, errores=None, modo="APAGADO"):
        self.borradores = borradores
        self.detalles = {b["id"]: _detalle(b) for b in borradores}
        self.lista_errores = errores or {"clasificacion": [], "generacion": [], "faq": []}
        self.modo = modo
        self.aprobados, self.rechazados, self.ediciones, self.reintentos = [], [], [], []
        self.error_al_aprobar = None

    def listar_con_modo(self, estado="PENDIENTE", limite=100):
        respuesta = {"borradores": self.listar_borradores(estado)}
        if self.modo is not None:
            respuesta["linkedinModo"] = self.modo
        return respuesta

    def listar_borradores(self, estado="PENDIENTE", tipo=None, limite=100):
        return [dict(b) for b in self.borradores if b["estado"] == estado]

    def detalle(self, borrador_id):
        return self.detalles[borrador_id]

    def editar(self, borrador_id, usuario, texto_final):
        self.ediciones.append((borrador_id, usuario, texto_final))
        self.detalles[borrador_id] = {**self.detalles[borrador_id], "textoFinal": texto_final}
        return self.detalles[borrador_id]

    def aprobar(self, borrador_id, usuario, consentimiento, tiempo_seg, texto_final=None):
        if self.error_al_aprobar:
            raise self.error_al_aprobar
        self.aprobados.append((borrador_id, usuario, consentimiento, tiempo_seg, texto_final))
        self._revisar(borrador_id, "APROBADO", aprobadoPor=usuario, aprobadoEn="2026-10-15T20:00:00Z",
                      consentimientoConfirmado=consentimiento, tiempoCuraduriaSeg=tiempo_seg)
        return self.detalles[borrador_id]

    def rechazar(self, borrador_id, usuario, motivo, tiempo_seg):
        self.rechazados.append((borrador_id, usuario, motivo, tiempo_seg))
        self._revisar(borrador_id, "RECHAZADO", rechazadoPor=usuario, rechazadoEn="2026-10-15T20:00:00Z",
                      motivoRechazo=motivo)
        return self.detalles[borrador_id]

    def _revisar(self, borrador_id, estado, **campos):
        for b in self.borradores:
            if b["id"] == borrador_id:
                b["estado"] = estado
                b["revisadoEn"] = "2026-10-15T20:00:00Z"
        self.detalles[borrador_id] = {**self.detalles[borrador_id], "estado": estado, **campos}

    def errores(self):
        return self.lista_errores

    def reintentar(self, etapa, mensaje_id, usuario):
        self.reintentos.append((etapa, mensaje_id, usuario))
        return {"mensajeId": mensaje_id, "etapa": etapa, "estado": "PENDIENTE"}

    def reintentar_faq(self, semana, usuario):
        self.reintentos.append(("faq", semana, usuario))
        return {"semana": semana, "etapa": "faq", "estado": "PENDIENTE"}


def _ejemplo(autor="Camila Rojas", modo="APAGADO"):
    post_a = _resumen(1, "POST_LINKEDIN", 183, "2026-10-01T15:00:00Z", estado="APROBADO", autor=autor)
    post_a["revisadoEn"] = "2026-10-02T15:00:00Z"
    post_a["linkedin"] = {"estado": "APAGADO", "postId": None, "en": "2026-10-02T15:00:01Z", "motivo": None}
    java = JavaSimulado([
        post_a,
        _resumen(2, "CASO_EXITO", 183, "2026-10-01T15:00:00Z", autor=autor),
        _resumen(3, "POST_LINKEDIN", 256, "2026-10-05T15:00:00Z", autor=autor),
        _resumen(4, "CASO_EXITO", 256, "2026-10-05T15:00:00Z", autor=autor),
        _resumen(5, "FAQ", None, "2026-10-12T15:00:00Z", semana="2026-W41"),
    ], modo=modo)
    java.detalles[1] = {**java.detalles[1], "aprobadoPor": "paula", "aprobadoEn": "2026-10-02T15:00:00Z",
                        "consentimientoConfirmado": True, "tiempoCuraduriaSeg": 40, "textoFinal": "Post 1 aprobado"}
    return java


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("PANEL_USUARIOS", USUARIOS)
    monkeypatch.setenv("API_KEY_PANEL", "clave-de-prueba")
    monkeypatch.setattr(auth, "PAUSA_FALLO_S", 0)
    st.cache_resource.clear()  # que los fallos de una prueba no bloqueen a la siguiente
    yield


@pytest.fixture
def java(monkeypatch):
    simulado = _ejemplo()
    monkeypatch.setattr(ui, "obtener_cliente", lambda: simulado)
    return simulado


def _app():
    return AppTest.from_file(APP, default_timeout=30)


def _con_sesion():
    at = _app()
    at.session_state["usuario"] = "harrison"
    at.session_state["ultimo_uso"] = time.monotonic()
    return at.run()


def _entrar(at, usuario, contrasena):
    at.text_input(key="login_usuario").input(usuario)
    at.text_input(key="login_contrasena").input(contrasena)
    at.button[0].click()
    return at.run()


def _abrir(at, clave):
    at.button(key=f"abrir_{clave}").click()
    return at.run()


def _html(at) -> str:
    return "\n".join(e.proto.body for e in at.get("html"))


def _textos(at) -> list[str]:
    return [t.value for t in at.text]


# ── Inicio de sesión ──

def test_sin_usuarios_configurados_no_se_puede_entrar(monkeypatch, java):
    monkeypatch.setenv("PANEL_USUARIOS", "")

    at = _app().run()

    assert "no tiene usuarios configurados" in at.error[0].value
    assert len(at.text_input) == 0
    assert java.aprobados == [] and "usuario" not in at.session_state


def test_una_contrasena_equivocada_no_entra(java):
    at = _entrar(_app().run(), "harrison", "otra-clave-cualquiera")

    assert "incorrectos" in at.error[0].value
    assert "usuario" not in at.session_state
    assert len(at.text_area) == 0  # no se ve ningún borrador


def test_un_usuario_que_no_existe_recibe_el_mismo_mensaje(java):
    at = _entrar(_app().run(), "nadie", CONTRASENA)

    assert at.error[0].value == "Usuario o contraseña incorrectos."


def test_la_contrasena_correcta_entra_y_muestra_los_borradores(java):
    at = _app().run()
    assert at.title[0].value == "CommunityLab · Panel de curaduría"  # el título queda en el inicio de sesión

    at = _entrar(at, "harrison", CONTRASENA)

    assert not at.exception
    assert at.session_state["usuario"] == "harrison"
    assert at.session_state["tarjeta_elegida"] == LOGRO_A  # la más antigua
    assert at.sidebar.text[0].value == "Sesión: harrison"


def test_cinco_fallos_bloquean_aunque_despues_se_acierte(java):
    at = _app().run()
    for _ in range(auth.ControlIntentos.MAX_FALLOS):
        at = _entrar(at, "harrison", "equivocada-123")

    at = _entrar(at, "harrison", CONTRASENA)

    assert "Demasiados intentos" in at.error[0].value
    assert "usuario" not in at.session_state


def test_cerrar_sesion(java):
    at = _con_sesion()

    at.sidebar.button[0].click()
    at = at.run()

    assert "usuario" not in at.session_state
    assert at.text_input(key="login_usuario") is not None


# ── La barra lateral (T13) ──

def test_la_barra_lateral_tiene_el_titulo_la_navegacion_con_las_tarjetas_por_revisar_y_la_sesion(java):
    at = _con_sesion()

    assert not at.title  # el título del panel ya no va arriba de cada página
    assert [m.value for m in at.sidebar.markdown] == ["**CommunityLab**", "Panel de curaduría"]
    assert [p.proto.label for p in at.sidebar.get("page_link")] == ["Borradores :gray-badge[3]", "Dashboard",
                                                                    "Errores"]
    assert at.sidebar.text[0].value == "Sesión: harrison"


# ── Borradores: la cola (pruebas 1 y 7 de la ficha) ──

def test_la_cola_tiene_una_tarjeta_por_logro_y_cuenta_tarjetas(java):
    at = _con_sesion()

    assert not at.exception
    # Por revisar cuenta tarjetas (3), no borradores (4)
    assert at.button_group(key="filtro_estado").options == ["Por revisar (3)", "Aprobados", "Rechazados"]
    assert [b.key for b in at.button if b.key and b.key.startswith("abrir_")] == [
        f"abrir_{LOGRO_A}", f"abrir_{LOGRO_B}", f"abrir_{FAQ}"]
    html = _html(at)
    assert html.find("Solo caso de éxito") < html.find("Post + caso de éxito") < html.find("FAQ · sin consentimiento")
    assert "FAQ de la semana 2026-W41" in _textos(at)
    # El detalle de la primera: el post ya aprobado se lee, y el caso se edita
    assert "Logro de Camila" in _textos(at)
    assert [t.label for t in at.tabs] == ["Post de LinkedIn", "Caso de éxito"]
    assert at.text_area(key="leer_1").disabled
    assert at.text_area(key="texto_2").value == "Borrador 2 de la IA"
    assert "No publicado: la publicación en LinkedIn está apagada" in _textos(at)
    # El post ya se aprobó con consentimiento: la casilla viene marcada para el caso (y se puede desmarcar)
    assert at.checkbox(key=f"consentimiento_{LOGRO_A}").value


@pytest.mark.parametrize("nombre", ["**x**", "[x](http://malo.example)", "![x](http://malo.example/i.png)",
                                    "<b>x</b>", SCRIPT.replace(" ", "")])
def test_un_nombre_con_markdown_o_html_se_ve_tal_cual(monkeypatch, nombre):
    java = _ejemplo(autor=f"{nombre} Rojas")
    monkeypatch.setattr(ui, "obtener_cliente", lambda: java)
    at = _abrir(_con_sesion(), LOGRO_B)

    # En la tarjeta y el título: st.text, que no interpreta nada
    assert nombre in _textos(at) and f"Logro de {nombre}" in _textos(at)
    # En la casilla (una etiqueta interpreta markdown): escapado
    casilla = at.checkbox(key=f"consentimiento_{LOGRO_B}")
    assert casilla.label == (f"{logros.escapar_markdown(nombre)} dio su consentimiento para publicar su nombre y su "
                             f"historia. **Vale para los dos textos.**")
    # Y en el aviso de aprobado (st.success también es markdown)
    casilla.check()
    at = at.run()
    at.button(key="aprobar_3").click()
    at = at.run()
    at.button(key="aprobar_4").click()
    at = at.run()
    assert at.success[0].value == f"Aprobados los dos textos de {logros.escapar_markdown(nombre)}."
    # Nunca crudo en un markdown ni en un bloque de HTML
    assert not any(nombre in m.value for m in at.markdown)
    assert nombre not in _html(at)


def test_un_texto_con_html_se_muestra_escapado(java):
    java.detalles[3] = {**java.detalles[3], "textoIa": SCRIPT, "motivoIa": SCRIPT,
                        "origen": {**java.detalles[3]["origen"], "texto": SCRIPT}}

    at = _abrir(_con_sesion(), LOGRO_B)

    # Se ve tal cual, como texto: en textos simples, el área de edición y el cuadro de copiar
    assert f"“{SCRIPT}”" in _textos(at) and SCRIPT in _textos(at)
    assert at.text_area(key="texto_3").value == SCRIPT
    assert any(c.value == SCRIPT for c in at.code)
    # Y nunca dentro de un markdown ni de un bloque de HTML
    assert not any("<script>" in m.value for m in at.markdown)
    assert "<script>" not in _html(at)


# ── Borradores: aprobar (pruebas 2 y 3) ──

def test_un_post_no_se_aprueba_sin_la_casilla(java):
    at = _abrir(_con_sesion(), LOGRO_B)

    # Apagados: ni un navegador ni AppTest pueden pulsarlos
    assert at.button(key="aprobar_3").disabled and at.button(key="aprobar_4").disabled
    assert "Para aprobar, marca la casilla de consentimiento." in _html(at)
    assert java.aprobados == []


def test_aprobar_el_post_y_despues_el_caso_cada_uno_con_su_tiempo(java):
    at = _con_sesion()
    # El logro se abrió hace 1000 s
    at.session_state["abiertas"] = {LOGRO_B: time.monotonic() - 1000}
    at = _abrir(at, LOGRO_B)
    at.checkbox(key=f"consentimiento_{LOGRO_B}").check()
    at = at.run()

    at.button(key="aprobar_3").click()
    at = at.run()

    assert not at.exception
    assert len(java.aprobados) == 1
    borrador_id, usuario, consentimiento, tiempo_post, editado = java.aprobados[0]
    assert (borrador_id, usuario, consentimiento, editado) == (3, "harrison", True, None)
    assert tiempo_post >= 1000
    # La tarjeta sigue en la cola, avisa lo que falta y abre el caso
    assert at.success[0].value == "Post aprobado. Falta revisar el caso de éxito."
    assert at.session_state["tarjeta_elegida"] == LOGRO_B
    assert at.text_area(key="leer_3").disabled and not at.text_area(key="texto_4").disabled
    assert at.checkbox(key=f"consentimiento_{LOGRO_B}").value

    at.button(key="aprobar_4").click()
    at = at.run()

    assert [a[:3] for a in java.aprobados] == [(3, "harrison", True), (4, "harrison", True)]
    assert java.aprobados[1][3] < 1000  # el tiempo del caso cuenta desde que se aprobó el post (decisión 2)
    assert at.success[0].value == "Aprobados los dos textos de Camila."
    assert at.button(key="ir_contenido").label == "Verlos en Listos para publicar"
    assert f"abrir_{LOGRO_B}" not in [b.key for b in at.button]  # salió de "Por revisar"
    assert at.button_group(key="filtro_estado").options[0] == "Por revisar (2)"

    # El enlace abre el dashboard en la pestaña Contenido
    at.button(key="ir_contenido").click()
    at = at.run()
    assert at.session_state["dash_vista"] == "Contenido"


def test_editar_y_aprobar_envia_el_texto_editado(java):
    at = _abrir(_con_sesion(), LOGRO_B)
    at.text_area(key="texto_3").input("Texto corregido por Marketing")
    at.checkbox(key=f"consentimiento_{LOGRO_B}").check()
    at = at.run()
    at.button(key="aprobar_3").click()
    at = at.run()

    assert java.aprobados[0][0] == 3 and java.aprobados[0][4] == "Texto corregido por Marketing"


@pytest.mark.parametrize("modo, etiqueta, nota, confirma", [
    ("APAGADO", "Aprobar post", "La publicación en LinkedIn está apagada: aprobar no publica nada.", False),
    ("SIMULADO", "Aprobar post", "LinkedIn está en modo simulado: aprobar no publica nada.", False),
    ("REAL", "Aprobar y publicar en LinkedIn",
     "Al aprobar, el post se publica en público en el LinkedIn de CommunityLab.", True),
    (None, "Aprobar post", "No se pudo saber si LinkedIn está encendido: al aprobar, podría publicarse.", True),
])
def test_el_boton_del_post_dice_antes_de_aprobar_que_pasara_en_linkedin(monkeypatch, modo, etiqueta, nota, confirma):
    java = _ejemplo(modo=modo)
    monkeypatch.setattr(ui, "obtener_cliente", lambda: java)
    at = _abrir(_con_sesion(), LOGRO_B)
    at.checkbox(key=f"consentimiento_{LOGRO_B}").check()
    at = at.run()

    assert at.button(key="aprobar_3").label == etiqueta
    assert at.button(key="aprobar_4").label == "Aprobar caso de éxito"
    assert nota in _html(at)

    at.button(key="aprobar_3").click()
    at = at.run()

    if not confirma:
        assert [a[0] for a in java.aprobados] == [3]
        return
    # Sin confirmar no se envía el pedido
    assert java.aprobados == []
    assert "publicar_3" in [b.key for b in at.button]
    at.button(key="cancelar_3").click()
    at = at.run()
    assert java.aprobados == [] and "publicar_3" not in [b.key for b in at.button]
    # Al confirmar, sí
    at.button(key="aprobar_3").click()
    at = at.run()
    at.button(key="publicar_3").click()
    at = at.run()
    assert [a[:3] for a in java.aprobados] == [(3, "harrison", True)]
    assert at.success[0].value == "Post aprobado. Falta revisar el caso de éxito."


def test_la_faq_se_aprueba_sin_casilla(java):
    at = _abrir(_con_sesion(), FAQ)

    assert len(at.checkbox) == 0
    assert [t.label for t in at.tabs] == ["FAQ semanal"]
    assert at.button(key="aprobar_5").label == "Aprobar FAQ"
    at.button(key="aprobar_5").click()
    at = at.run()

    assert java.aprobados[0][:3] == (5, "harrison", False)
    assert at.success[0].value == "FAQ aprobada."


def test_si_otra_persona_gano_se_avisa(java):
    java.error_al_aprobar = ErrorJava(409, "CONFLICTO", "El borrador ya no está PENDIENTE: otra persona lo revisó.")
    at = _con_sesion()
    at.button(key="aprobar_2").click()
    at = at.run()

    assert "otra persona" in at.warning[0].value and "Actualiza la lista" in at.warning[0].value
    assert not at.exception


# ── Borradores: guardar, rechazar y la edición (pruebas 4, 5 y 6) ──

def test_guardar_edicion_y_rechazar_tocan_solo_su_texto(java):
    at = _abrir(_con_sesion(), LOGRO_B)
    at.text_area(key="texto_3").input("Post nuevo")
    at.button(key="guardar_3").click()
    at = at.run()
    assert java.ediciones == [(3, "harrison", "Post nuevo")]
    assert "Edición guardada" in at.success[0].value

    at.text_input(key="motivo_4").input("Repite el de ayer")
    at.button(key="rechazar_4").click()
    at = at.run()

    assert java.rechazados[0][:3] == (4, "harrison", "Repite el de ayer")
    assert java.aprobados == [] and len(java.ediciones) == 1  # el post no cambió
    assert java.detalles[3]["estado"] == "PENDIENTE"
    assert at.success[0].value == "Caso de éxito rechazado. Falta revisar el post."


def test_una_edicion_no_se_pierde_al_cambiar_de_pestana_ni_de_tarjeta(java):
    at = _abrir(_con_sesion(), LOGRO_B)
    at.text_area(key="texto_3").input("Post editado sin guardar")
    at = at.run()
    # Las dos pestañas se dibujan siempre: escribir en el caso no borra el post
    at.text_area(key="texto_4").input("Caso editado")
    at = at.run()
    assert at.text_area(key="texto_3").value == "Post editado sin guardar"

    # Otra tarjeta y vuelta: ninguna de las dos se dibujó en el medio
    at = _abrir(at, FAQ)
    assert at.text_area(key="texto_5") is not None
    at = _abrir(at, LOGRO_B)

    assert at.text_area(key="texto_3").value == "Post editado sin guardar"
    assert at.text_area(key="texto_4").value == "Caso editado"
    assert java.ediciones == []  # nada se envió


def test_el_contador_cuenta_como_java_y_un_post_muy_largo_no_se_aprueba(java):
    at = _abrir(_con_sesion(), LOGRO_B)
    at.checkbox(key=f"consentimiento_{LOGRO_B}").check()
    at.text_area(key="texto_3").input("🎉" * 1500)
    at = at.run()

    assert "1 palabra (la guía pide 90 a 160) · 3.000 de 3.000 caracteres de LinkedIn" in _html(at)
    assert not at.button(key="aprobar_3").disabled

    at.text_area(key="texto_3").input("🎉" * 1500 + "!")
    at = at.run()

    assert "3.001 de 3.000 caracteres de LinkedIn" in _html(at)
    assert at.button(key="aprobar_3").disabled
    assert "LinkedIn acepta hasta 3.000 caracteres: acorta el post para aprobarlo." in _html(at)
    assert "(la guía pide 150 a 250) · sin emojis ni hashtags" in _html(at)  # el contador del caso


# ── Borradores: lo aprobado y el estado en LinkedIn (prueba 8) ──

@pytest.mark.parametrize("linkedin, frase, enlace", [
    ({"estado": "PUBLICADO", "postId": "urn:li:share:7251234567890123456", "en": "2026-10-15T19:00:00Z"},
     "Publicado en LinkedIn el 2026-10-15 14:00",
     "https://www.linkedin.com/feed/update/urn:li:share:7251234567890123456/"),
    ({"estado": "PUBLICADO", "postId": "javascript:alert(1)", "en": "2026-10-15T19:00:00Z"},
     "Publicado en LinkedIn el 2026-10-15 14:00", None),
    ({"estado": "APAGADO"}, "No publicado: la publicación en LinkedIn está apagada", None),
    ({"estado": "SIMULADO"}, "Simulado: LinkedIn está encendido sin token", None),
    ({"estado": "ERROR", "motivo": "Pasa de 3.000 caracteres"}, "Falló: Pasa de 3.000 caracteres", None),
    ({"estado": None, "postId": None, "en": None, "motivo": None},
     "Sin dato (se aprobó antes de que se guardara este estado)", None),
])
def test_un_post_aprobado_dice_que_paso_en_linkedin(java, linkedin, frase, enlace):
    java.detalles[1] = {**java.detalles[1], "linkedin": linkedin}

    at = _con_sesion()

    assert frase in _textos(at)
    assert [b.proto.url for b in at.get("link_button")] == ([enlace] if enlace else [])


def test_lo_aprobado_sale_de_los_pendientes_y_se_ve_solo_para_leer(java):
    at = _con_sesion()
    at.button(key="aprobar_2").click()  # la casilla ya viene marcada: el post se aprobó con consentimiento
    at = at.run()

    assert not at.exception
    assert [b.key for b in at.button if b.key and b.key.startswith("abrir_")] == [f"abrir_{LOGRO_B}", f"abrir_{FAQ}"]

    at.button_group(key="filtro_estado").set_value("APROBADO")
    at = at.run()
    assert at.session_state["tarjeta_elegida"] == LOGRO_A
    assert at.text_area(key="leer_1").disabled and at.text_area(key="leer_2").disabled
    assert len([b for b in at.button if b.key and b.key.startswith("aprobar_")]) == 0
    assert len(at.checkbox) == 0


# ── OCI (T09) ──

def test_el_detalle_dice_si_cada_texto_ya_esta_en_oci(java):
    at = _abrir(_con_sesion(), LOGRO_B)

    # Un pendiente solo puede estar en generados/: a aprobados/ solo va lo aprobado
    assert [t for t in _textos(at) if "/:" in t] == ["Post de LinkedIn · generados/: ✅ subido",
                                                     "Caso de éxito · generados/: ✅ subido"]


def test_un_aprobado_muestra_las_dos_carpetas(java):
    java.detalles[1] = {**java.detalles[1], "oci": {"generados": "SUBIDO", "aprobados": "PENDIENTE"}}

    at = _con_sesion()

    assert [t for t in _textos(at) if "/:" in t] == [
        "Post de LinkedIn · generados/: ✅ subido",
        "Post de LinkedIn · aprobados/: ⏳ pendiente (se sube en segundo plano)",
        "Caso de éxito · generados/: ✅ subido"]


def test_si_java_no_manda_el_estado_de_oci_ni_de_linkedin_el_panel_no_falla(java):
    for d in java.detalles.values():
        d.pop("oci", None)
        d.pop("linkedin", None)
    java.modo = None

    at = _abrir(_con_sesion(), LOGRO_B)

    assert not at.exception
    assert "Post de LinkedIn · generados/: — todavía no" in _textos(at)


@pytest.mark.parametrize("oci, estado, esperado", [
    (None, "PENDIENTE", ["generados/: — todavía no"]),
    ({"generados": "PENDIENTE", "aprobados": None}, "RECHAZADO",
     ["generados/: ⏳ pendiente (se sube en segundo plano)"]),
    ({"generados": "ERROR", "aprobados": "ERROR"}, "APROBADO",
     ["generados/: ❌ error (revisar con quien administra el servidor)",
      "aprobados/: ❌ error (revisar con quien administra el servidor)"]),
    ({"generados": "SUBIDO", "aprobados": None}, "APROBADO", ["generados/: ✅ subido", "aprobados/: — todavía no"]),
])
def test_lineas_oci(oci, estado, esperado):
    assert ui.lineas_oci(oci, estado) == esperado


# ── Errores ──

def test_la_pagina_de_errores_reintenta(java):
    java.lista_errores = {
        "clasificacion": [{"mensajeId": 17, "discordId": "x", "canal": "dudas", "fecha": "2026-09-29T14:10:00Z",
                           "autorNombre": "Ana", "extracto": SCRIPT, "intentos": 3, "motivo": None}],
        "generacion": [],
        "faq": [],
    }
    at = _con_sesion()
    at.switch_page("paginas/errores.py")
    at = at.run()

    assert any(c.value == SCRIPT for c in at.code)
    at.button(key="reintentar_clasificacion_17").click()
    at = at.run()

    assert java.reintentos == [("clasificacion", 17, "harrison")]
    assert "devuelto a la cola" in at.success[0].value


def test_la_pagina_de_errores_reintenta_una_faq(java):
    java.lista_errores = {"clasificacion": [], "generacion": [], "faq": [
        {"semana": "2026-W41", "desde": "2026-10-05T13:00:00Z", "hasta": "2026-10-12T13:00:00Z", "intentos": 3,
         "motivo": SCRIPT}]}
    at = _con_sesion()
    at.switch_page("paginas/errores.py")
    at = at.run()

    assert f"Último error: {SCRIPT}" in _textos(at)  # con st.text
    at.button(key="reintentar_faq_2026-W41").click()
    at = at.run()

    assert java.reintentos == [("faq", "2026-W41", "harrison")]
    assert "se está armando" in at.success[0].value


def test_errores_de_un_java_de_antes_de_t13_sin_la_lista_faq(java):
    java.lista_errores = {"clasificacion": [], "generacion": []}
    at = _con_sesion()
    at.switch_page("paginas/errores.py")
    at = at.run()

    assert not at.exception
    assert [s.value for s in at.success] == ["No hay nada en ERROR."] * 3


def test_sin_clave_de_java_el_panel_lo_explica(monkeypatch):
    monkeypatch.setattr(ui, "obtener_cliente", lambda: None)

    at = _con_sesion()

    assert "API_KEY_PANEL" in at.error[0].value
