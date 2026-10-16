"""El recuadro "Estado de los datos" de la barra lateral (T14, DEC-168) y los íconos del dashboard.

Las del recuadro corren la app con AppTest y un Java simulado: no hace falta Java ni la base.
"""
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import estilo
import ui
from cliente_java import ErrorJava

APP = str(Path(__file__).resolve().parent.parent / "app.py")
BOGOTA = timezone(timedelta(hours=-5))


def _bogota(hora: str) -> datetime:
    h, m = (int(x) for x in hora.split(":"))
    return datetime(2026, 10, 16, h, m, tzinfo=BOGOTA)


def _iso(fecha: datetime) -> str:
    return fecha.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ingesta(recibido: datetime) -> dict:
    return {"ultimoLote": {"recibidoEn": _iso(recibido), "modo": "historial", "total": 67, "nuevos": 0,
                           "actualizados": 2}}


# ── El estado (prueba 11) y la próxima corrida (prueba 12) ──

def test_un_lote_de_hace_10_min_es_datos_al_dia():
    ahora = _bogota("14:20")

    estado = estilo.estado_datos(_ingesta(ahora - timedelta(minutes=10)), ahora)

    assert estado["clave"] == "al-dia" and estado["icono"] == ":material/check_circle:"
    assert estado["titulo"] == "Datos al día"
    assert estado["lineas"] == ["Última actualización: hace 10 min", "Próxima: 15:00 (cada hora, sola)"]


def test_un_lote_de_hace_3_horas_es_datos_atrasados():
    ahora = _bogota("14:20")

    estado = estilo.estado_datos(_ingesta(ahora - timedelta(hours=3)), ahora)

    assert estado["clave"] == "atrasados" and estado["titulo"] == "Datos atrasados"
    assert estado["lineas"][0] == "Última actualización: hace 3 h"


def test_el_limite_es_2_horas():
    ahora = _bogota("14:20")

    assert estilo.estado_datos(_ingesta(ahora - timedelta(minutes=119)), ahora)["clave"] == "al-dia"
    assert estilo.estado_datos(_ingesta(ahora - timedelta(minutes=120)), ahora)["clave"] == "atrasados"


def test_sin_lotes_dice_todavia_no_hay_lotes():
    estado = estilo.estado_datos({"ultimoLote": None}, _bogota("14:20"))

    assert estado["clave"] == "atrasados" and estado["titulo"] == "Todavía no hay lotes"
    assert estado["lineas"] == ["Próxima: 15:00 (cada hora, sola)"]


def test_si_java_no_respondio_dice_sin_informacion():
    estado = estilo.estado_datos(None, _bogota("14:20"))

    assert estado["clave"] == "sin-info" and estado["titulo"] == "Estado de los datos: sin información"


@pytest.mark.parametrize("ahora, proxima", [("14:20", "15:00"), ("23:50", "00:00"), ("15:00", "16:00")])
def test_la_proxima_es_la_hora_en_punto_siguiente_en_bogota(ahora, proxima):
    assert estilo.proxima_hora(_bogota(ahora)) == proxima
    assert estilo.proxima_hora(_bogota(ahora).astimezone(timezone.utc)) == proxima  # Java entrega UTC


@pytest.mark.parametrize("minutos, texto", [(0, "hace 0 min"), (59, "hace 59 min"), (60, "hace 1 h"),
                                            (60 * 24, "hace 1 día"), (60 * 72, "hace 3 días")])
def test_hace_minutos(minutos, texto):
    ahora = _bogota("14:20")
    assert estilo.hace_minutos(_iso(ahora - timedelta(minutes=minutos)), ahora) == texto


# ── El recuadro en la app ──

class JavaConIngesta:
    """Lo mínimo para que la app corra (Borradores sin tarjetas) más la puerta de la ingesta."""

    def __init__(self, ingesta=None, error=None):
        self.ingesta, self.error, self.pedidos = ingesta, error, 0

    def listar_borradores(self, estado="PENDIENTE", tipo=None, limite=100):
        return []

    def listar_con_modo(self, estado="PENDIENTE", limite=100):
        return {"borradores": [], "linkedinModo": "APAGADO"}

    def dashboard_ingesta(self):
        self.pedidos += 1
        if self.error:
            raise self.error
        return self.ingesta


def _app(monkeypatch, java):
    st.cache_resource.clear()
    monkeypatch.setattr(ui, "obtener_cliente", lambda: java)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["usuario"] = "harrison"
    at.session_state["ultimo_uso"] = time.monotonic()
    return at.run()


def _recuadro(at) -> tuple[str, list[str]]:
    return at.sidebar.markdown[2].value, [c.value for c in at.sidebar.caption]


def test_la_barra_lateral_muestra_datos_al_dia_debajo_de_la_navegacion(monkeypatch):
    java = JavaConIngesta(_ingesta(datetime.now(timezone.utc) - timedelta(minutes=12)))

    at = _app(monkeypatch, java)

    assert not at.exception
    titulo, lineas = _recuadro(at)
    assert titulo == ":material/check_circle: **Datos al día**"
    assert lineas[0] == "Última actualización: hace 12 min" and lineas[1].startswith("Próxima: ")
    assert lineas[1].endswith(":00 (cada hora, sola)")
    assert at.sidebar.text[0].value == "Sesión: harrison"  # la sesión sigue debajo


def test_sin_lotes_y_con_java_caido_la_pagina_sigue_funcionando(monkeypatch):
    at = _app(monkeypatch, JavaConIngesta({"ultimoLote": None}))
    assert _recuadro(at)[0] == ":material/schedule: **Todavía no hay lotes**"

    at = _app(monkeypatch, JavaConIngesta(error=ErrorJava(0, "SIN_CONEXION", "No se pudo conectar con Java.")))

    assert not at.exception
    assert _recuadro(at)[0] == ":material/cloud_off: **Estado de los datos: sin información**"
    assert at.sidebar.text[0].value == "Sesión: harrison"


def test_el_estado_se_pide_a_java_como_mucho_una_vez_por_minuto(monkeypatch):
    java = JavaConIngesta(_ingesta(datetime.now(timezone.utc)))
    at = _app(monkeypatch, java)

    at.run()
    at.run()

    assert java.pedidos == 1


# ── Los íconos del dashboard (prueba 13) ──

def test_los_iconos_del_dashboard_ya_no_son_svg():
    for icono in (estilo.ICONO_RELOJ, estilo.ICONO_ALERTA, estilo.ICONO_DOCUMENTO):
        html = icono.format(color="#d18f0c")
        assert "<svg" not in html
        assert "Material Symbols Rounded" in html and 'aria-hidden="true"' in html
    assert ">schedule<" in estilo.ICONO_RELOJ and ">warning<" in estilo.ICONO_ALERTA
    assert ">description<" in estilo.ICONO_DOCUMENTO
