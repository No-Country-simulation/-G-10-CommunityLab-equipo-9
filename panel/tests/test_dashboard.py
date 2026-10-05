"""
Página "Dashboard" (T08) con streamlit.testing (AppTest) y un Java simulado:
dibuja, envía los parámetros de los controles, avisa cuando no hay datos y muestra los textos escapados.
"""
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import auth
import ui
from cliente_java import ErrorJava

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SCRIPT = "<script>alert('hola')</script> ¿cómo instalo python?"
CEROS = {"MUY_POSITIVO": 0, "POSITIVO": 0, "NEUTRO": 0, "NEGATIVO": 0, "MUY_NEGATIVO": 0}


class DashboardSimulado:
    """Hace de Java: devuelve lo que se le cargue y anota los parámetros de cada pedido."""

    def __init__(self, vacio=False):
        self.pedidos = []
        self.vacio = vacio
        self.falla = set()

    def _anotar(self, nombre, *args):
        self.pedidos.append((nombre, args))
        if nombre in self.falla:
            raise ErrorJava(500, "ERROR_INTERNO", "No se pudo procesar el pedido.")

    def dashboard_totales(self, desde, hasta):
        self._anotar("totales", desde, hasta)
        return {"periodo": {}, "mensajes": 0 if self.vacio else 52, "personasActivas": 0 if self.vacio else 10,
                "dudas": 0 if self.vacio else 21, "logros": 0 if self.vacio else 13, "sinClasificar": 0,
                "borradoresPendientes": 0 if self.vacio else 7}

    def dashboard_sentimiento(self, desde, hasta, agrupar, excluir_otro):
        self._anotar("sentimiento", desde, hasta, agrupar, excluir_otro)
        puntos = [{"inicio": "2026-09-28", "cantidades": dict(CEROS)},
                  {"inicio": "2026-09-29", "cantidades": dict(CEROS)}]
        if not self.vacio:
            puntos[0]["cantidades"].update(POSITIVO=3, NEUTRO=14, MUY_NEGATIVO=1)
        return {"agrupar": agrupar, "puntos": puntos}

    def dashboard_temas(self, desde, hasta, excluir_otro):
        self._anotar("temas", desde, hasta, excluir_otro)
        temas = [] if self.vacio else [{"tema": "empleo", "actual": 3, "anterior": 1, "variacion": 2},
                                       {"tema": "herramientas_entorno", "actual": 0, "anterior": 2, "variacion": -2}]
        return {"periodoAnterior": {"desde": "2026-08-29", "hasta": "2026-09-27"}, "temas": temas}

    def dashboard_desercion(self, dias):
        self._anotar("desercion", dias)
        personas = [] if self.vacio else [{"nombre": "<b>Camila</b>", "ultimoMensaje": "2026-09-28T19:10:00Z",
                                           "diasSinEscribir": 6, "mensajes": 4}]
        return {"dias": dias, "personas": personas}

    def dashboard_frustracion(self, desde, hasta):
        self._anotar("frustracion", desde, hasta)
        personas = [] if self.vacio else [{"nombre": "Diego", "motivos": ["MUY_NEGATIVO"], "negativosEnPeriodo": 1,
                                           "negativosEnUltimos3": 1, "ultimoNegativo": "2026-09-28T18:40:00Z"}]
        return {"personas": personas}

    def dashboard_dudas(self, desde, hasta, horas, excluir_otro):
        self._anotar("dudas", desde, hasta, horas, excluir_otro)
        dudas = [] if self.vacio else [{"mensajeId": 17, "discordId": "1", "fecha": "2026-09-28T18:56:30Z",
                                        "tema": "herramientas_entorno", "derivada": True, "canal": "dudas",
                                        "autorNombre": "Ana", "texto": SCRIPT}]
        return {"total": len(dudas), "dudas": dudas}

    def listar_borradores(self, estado="PENDIENTE", tipo=None, limite=100):
        return []  # la página Borradores corre primero (es la de inicio)

    def args(self, nombre):
        return [a for n, a in self.pedidos if n == nombre][-1]


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("PANEL_USUARIOS", auth.con_usuario("", "harrison", auth.crear_registro("clave-larga-123")))
    monkeypatch.setenv("API_KEY_PANEL", "clave-de-prueba")
    st.cache_resource.clear()
    yield


def _dashboard(monkeypatch, java):
    monkeypatch.setattr(ui, "obtener_cliente", lambda: java)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["usuario"] = "harrison"
    at.session_state["ultimo_uso"] = time.monotonic()
    at.run()
    at.switch_page("paginas/dashboard.py")
    return at.run()


def test_dibuja_los_indicadores_con_los_parametros_por_defecto(monkeypatch):
    java = DashboardSimulado()

    at = _dashboard(monkeypatch, java)

    assert not at.exception
    hoy = datetime.now(ui.ZONA).date()
    desde = hoy - timedelta(days=29)
    assert java.args("totales") == (desde, hoy)
    assert java.args("sentimiento") == (desde, hoy, "dia", False)
    assert java.args("temas") == (desde, hoy, False)
    assert java.args("desercion") == (14,)
    assert java.args("frustracion") == (desde, hoy)
    assert java.args("dudas") == (desde, hoy, 24, False)
    assert [m.label for m in at.metric][:3] == ["Mensajes", "Personas activas", "Dudas"]
    assert at.metric[0].value == "52"
    assert len(at.get("vega_lite_chart")) == 2  # sentimiento y temas
    # Deserción y frustración en tablas; los nombres como datos, no como HTML
    assert at.dataframe[1].value["Alumno"].tolist() == ["<b>Camila</b>"]
    assert at.dataframe[2].value["Motivo"].tolist() == ["Un mensaje muy negativo"]
    assert at.dataframe[0].value["Tema"].tolist() == ["Empleo", "Herramientas y entorno"]


def test_los_controles_envian_sus_valores(monkeypatch):
    java = DashboardSimulado()
    at = _dashboard(monkeypatch, java)

    at.date_input(key="dash_periodo").set_value((date(2026, 9, 1), date(2026, 9, 30)))
    at.radio(key="dash_agrupar").set_value("Semana")
    at.checkbox(key="dash_excluir_otro").check()
    at.number_input(key="dash_dias").set_value(3)
    at.number_input(key="dash_horas").set_value(48)
    at = at.run()

    assert not at.exception
    desde, hasta = date(2026, 9, 1), date(2026, 9, 30)
    assert java.args("sentimiento") == (desde, hasta, "semana", True)
    assert java.args("temas") == (desde, hasta, True)
    assert java.args("desercion") == (3,)
    assert java.args("frustracion") == (desde, hasta)
    assert java.args("dudas") == (desde, hasta, 48, True)


def test_sin_datos_lo_dice_y_no_se_rompe(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado(vacio=True))

    assert not at.exception
    avisos = [i.value for i in at.info] + [s.value for s in at.success]
    assert "No hay mensajes con sentimiento en este período." in avisos
    assert "No hay temas en este período." in avisos
    assert "Ningún alumno lleva más de 14 días sin escribir." in avisos
    assert "No hay dudas sin responder en este período." in avisos
    assert len(at.get("vega_lite_chart")) == 0


def test_si_un_indicador_falla_los_demas_se_ven(monkeypatch):
    java = DashboardSimulado()
    java.falla = {"temas", "frustracion"}

    at = _dashboard(monkeypatch, java)

    assert not at.exception
    assert len(at.warning) == 2
    assert all("No se pudo cargar este indicador" in w.value for w in at.warning)
    assert at.metric[0].value == "52"
    assert any(c.value == SCRIPT for c in at.code)  # las dudas se ven igual


def test_una_duda_con_html_se_muestra_escapada(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    assert any(c.value == SCRIPT for c in at.code)
    assert any("derivada a un mentor" in t.value for t in at.text)
    assert not any("<script>" in m.value or "<b>Camila" in m.value for m in at.markdown)
    assert not any("<script>" in c.value for c in at.caption)


def test_un_periodo_a_medio_elegir_no_pide_nada(monkeypatch):
    java = DashboardSimulado()
    at = _dashboard(monkeypatch, java)
    antes = len(java.pedidos)

    at.date_input(key="dash_periodo").set_value((date(2026, 9, 1),))
    at = at.run()

    assert "Elige la fecha final del período." in [i.value for i in at.info]
    assert len(java.pedidos) == antes
