"""
El panel completo con streamlit.testing (AppTest), sin Java real: un cliente simulado ocupa su lugar.
Inicio de sesión, la casilla de consentimiento (D6), textos escapados y la página de errores.
"""
import time
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import auth
import ui
from cliente_java import ErrorJava

APP = str(Path(__file__).resolve().parent.parent / "app.py")
CONTRASENA = "clave-de-prueba-larga"
USUARIOS = auth.con_usuario("", "harrison", auth.crear_registro(CONTRASENA))
SCRIPT = "<script>alert('hola')</script>"


def _resumen(id_, tipo, semana=None):
    return {"id": id_, "tipo": tipo, "estado": "PENDIENTE", "creadoEn": "2026-10-04T15:02:11Z",
            "extracto": "…", "autorNombre": None, "canal": None, "semana": semana,
            "revisadoPor": None, "revisadoEn": None}


def _detalle(id_, tipo, texto_original="me contrataron!!!"):
    faq = tipo == "FAQ"
    return {
        "id": id_, "tipo": tipo, "estado": "PENDIENTE", "requiereConsentimiento": not faq,
        "textoIa": f"Borrador {id_} de la IA", "textoFinal": None, "consentimientoConfirmado": False,
        "creadoEn": "2026-10-04T15:02:11Z", "aprobadoPor": None, "aprobadoEn": None, "tiempoCuraduriaSeg": None,
        "rechazadoPor": None, "rechazadoEn": None, "motivoRechazo": None, "motivoIa": "Es una contratación.",
        "origen": None if faq else {"discordId": "1", "canal": "logros", "fecha": "2026-09-28T18:58:11Z",
                                    "texto": texto_original, "autorNombre": "Camila Rojas"},
        "faq": {"semana": "2026-W40", "desde": "2026-09-27T13:00:00Z", "hasta": "2026-10-04T13:00:00Z",
                "motivo": "3 repetidas."} if faq else None,
        "oci": {"generados": "SUBIDO", "aprobados": None},  # T09: solo el estado, nunca la ruta ni la PAR
    }


class JavaSimulado:
    """Hace de API Java: guarda lo que el panel le pide."""

    def __init__(self, borradores, detalles, errores=None):
        self.borradores = borradores
        self.detalles = detalles
        self.lista_errores = errores or {"clasificacion": [], "generacion": []}
        self.aprobados, self.rechazados, self.ediciones, self.reintentos = [], [], [], []
        self.error_al_aprobar = None

    def listar_borradores(self, estado="PENDIENTE", tipo=None, limite=100):
        return [b for b in self.borradores if b["estado"] == estado]

    def detalle(self, borrador_id):
        return self.detalles[borrador_id]

    def editar(self, borrador_id, usuario, texto_final):
        self.ediciones.append((borrador_id, usuario, texto_final))
        return self.detalles[borrador_id]

    def aprobar(self, borrador_id, usuario, consentimiento, tiempo_seg, texto_final=None):
        if self.error_al_aprobar:
            raise self.error_al_aprobar
        self.aprobados.append((borrador_id, usuario, consentimiento, tiempo_seg, texto_final))
        self._revisar(borrador_id, "APROBADO")
        return self.detalles[borrador_id]

    def rechazar(self, borrador_id, usuario, motivo, tiempo_seg):
        self.rechazados.append((borrador_id, usuario, motivo, tiempo_seg))
        self._revisar(borrador_id, "RECHAZADO")
        return self.detalles[borrador_id]

    def _revisar(self, borrador_id, estado):
        for b in self.borradores:
            if b["id"] == borrador_id:
                b["estado"] = estado
        self.detalles[borrador_id] = {**self.detalles[borrador_id], "estado": estado}

    def errores(self):
        return self.lista_errores

    def reintentar(self, etapa, mensaje_id, usuario):
        self.reintentos.append((etapa, mensaje_id, usuario))
        return {"mensajeId": mensaje_id, "etapa": etapa, "estado": "PENDIENTE"}


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("PANEL_USUARIOS", USUARIOS)
    monkeypatch.setenv("API_KEY_PANEL", "clave-de-prueba")
    monkeypatch.setattr(auth, "PAUSA_FALLO_S", 0)
    st.cache_resource.clear()  # que los fallos de una prueba no bloqueen a la siguiente
    yield


@pytest.fixture
def java(monkeypatch):
    simulado = JavaSimulado(
        borradores=[_resumen(1, "POST_LINKEDIN"), _resumen(2, "FAQ", semana="2026-W40")],
        detalles={1: _detalle(1, "POST_LINKEDIN"), 2: _detalle(2, "FAQ")})
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
    assert len(at.selectbox) == 0  # no se ve ningún borrador


def test_un_usuario_que_no_existe_recibe_el_mismo_mensaje(java):
    at = _entrar(_app().run(), "nadie", CONTRASENA)

    assert at.error[0].value == "Usuario o contraseña incorrectos."


def test_la_contrasena_correcta_entra_y_muestra_los_borradores(java):
    at = _entrar(_app().run(), "harrison", CONTRASENA)

    assert not at.exception
    assert at.session_state["usuario"] == "harrison"
    assert at.selectbox(key="borrador_sel").value == 1
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


# ── Borradores ──

def test_un_post_no_se_aprueba_sin_la_casilla(java):
    at = _con_sesion()

    # Apagado: ni un navegador ni AppTest pueden pulsarlo
    assert at.button(key="aprobar_1").disabled
    assert "consentimiento" in at.caption[0].value
    assert java.aprobados == []

    at.checkbox(key="consentimiento_1").check()
    at = at.run()
    assert not at.button(key="aprobar_1").disabled
    at.button(key="aprobar_1").click()
    at = at.run()

    assert len(java.aprobados) == 1
    borrador_id, usuario, consentimiento, tiempo, editado = java.aprobados[0]
    assert (borrador_id, usuario, consentimiento, editado) == (1, "harrison", True, None)
    assert tiempo >= 0
    assert "aprobado" in at.success[0].value


def test_la_faq_se_aprueba_sin_casilla(java):
    at = _con_sesion()
    at.selectbox(key="borrador_sel").select(2)
    at = at.run()

    assert len(at.checkbox) == 0
    assert not at.button(key="aprobar_2").disabled
    at.button(key="aprobar_2").click()
    at = at.run()

    assert java.aprobados[0][:3] == (2, "harrison", False)


def test_editar_y_aprobar_envia_el_texto_editado(java):
    at = _con_sesion()
    at.text_area(key="texto_1").input("Texto corregido por Marketing")
    at.checkbox(key="consentimiento_1").check()
    at = at.run()
    at.button(key="aprobar_1").click()
    at = at.run()

    assert java.aprobados[0][4] == "Texto corregido por Marketing"


def test_guardar_edicion_y_rechazar(java):
    at = _con_sesion()
    at.text_area(key="texto_1").input("Texto nuevo")
    at.button(key="guardar_1").click()
    at = at.run()
    assert java.ediciones == [(1, "harrison", "Texto nuevo")]

    at.text_input(key="motivo_1").input("Repite el de ayer")
    at.button(key="rechazar_1").click()
    at = at.run()
    assert java.rechazados[0][:3] == (1, "harrison", "Repite el de ayer")


def test_si_otra_persona_gano_se_avisa(java):
    java.error_al_aprobar = ErrorJava(409, "CONFLICTO", "El borrador ya no está PENDIENTE: otra persona lo revisó.")
    at = _con_sesion()
    at.checkbox(key="consentimiento_1").check()
    at = at.run()
    at.button(key="aprobar_1").click()
    at = at.run()

    assert "otra persona" in at.warning[0].value
    assert not at.exception


def test_un_texto_con_html_se_muestra_escapado(java):
    java.detalles[1] = _detalle(1, "POST_LINKEDIN", texto_original=SCRIPT)
    java.detalles[1]["origen"]["autorNombre"] = "<b>Camila</b>"
    java.detalles[1]["textoIa"] = SCRIPT

    at = _con_sesion()

    # Se ve tal cual, como texto: en bloques de código, textos simples y el área de edición
    assert any(c.value == SCRIPT for c in at.code)
    assert any(t.value == "Autor: <b>Camila</b>" for t in at.text)
    assert at.text_area(key="texto_1").value == SCRIPT
    # Y nunca dentro de un markdown (el único lugar donde Streamlit podría interpretarlo)
    assert not any("<script>" in m.value or "<b>Camila" in m.value for m in at.markdown)


def test_lo_aprobado_sale_de_los_pendientes_y_se_ve_solo_para_leer(java):
    at = _con_sesion()
    at.checkbox(key="consentimiento_1").check()
    at = at.run()
    at.button(key="aprobar_1").click()
    at = at.run()

    assert not at.exception
    assert at.selectbox(key="borrador_sel").options == ["#2 · FAQ semanal · 2026-10-04 10:02 · semana 2026-W40"]

    at.radio(key="filtro_estado").set_value("Aprobados")
    at = at.run()
    assert at.selectbox(key="borrador_sel").value == 1
    assert at.text_area(key="leer_1").disabled
    assert len([b for b in at.button if b.key and b.key.startswith("aprobar_")]) == 0


# ── OCI (T09) ──

def test_el_detalle_dice_si_el_borrador_ya_esta_en_oci(java):
    at = _con_sesion()

    # Un pendiente solo puede estar en generados/: a aprobados/ solo va lo aprobado
    assert [t.value for t in at.text if "/:" in t.value] == ["generados/: ✅ subido"]


def test_un_aprobado_muestra_las_dos_carpetas(java):
    java.detalles[1] = {**_detalle(1, "POST_LINKEDIN"), "estado": "APROBADO",
                        "oci": {"generados": "SUBIDO", "aprobados": "PENDIENTE"}}
    java.borradores[0]["estado"] = "APROBADO"
    at = _con_sesion()
    at.radio(key="filtro_estado").set_value("Aprobados")
    at = at.run()

    assert [t.value for t in at.text if "/:" in t.value] == [
        "generados/: ✅ subido", "aprobados/: ⏳ pendiente (se sube en segundo plano)"]


def test_si_java_no_manda_el_estado_de_oci_el_panel_no_falla(java):
    del java.detalles[1]["oci"]

    at = _con_sesion()

    assert not at.exception
    assert [t.value for t in at.text if "/:" in t.value] == ["generados/: — todavía no"]


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
    }
    at = _con_sesion()
    at.switch_page("paginas/errores.py")
    at = at.run()

    assert any(c.value == SCRIPT for c in at.code)
    at.button(key="reintentar_clasificacion_17").click()
    at = at.run()

    assert java.reintentos == [("clasificacion", 17, "harrison")]
    assert "devuelto a la cola" in at.success[0].value


def test_sin_clave_de_java_el_panel_lo_explica(monkeypatch):
    monkeypatch.setattr(ui, "obtener_cliente", lambda: None)

    at = _con_sesion()

    assert "API_KEY_PANEL" in at.error[0].value
