"""
Página "Dashboard" (T08 y T12) con streamlit.testing (AppTest) y un Java simulado: las dos vistas por rol,
qué pide cada una, el supuesto de P1, la n junto a cada porcentaje, los avisos sin datos, los textos escapados,
el enlace a Discord y la paleta según el tema.
"""
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import streamlit as st
from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from streamlit.testing.v1 import AppTest

import auth
import ui
from cliente_java import ErrorJava

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SCRIPT = "<script>alert('hola')</script> ¿cómo instalo python?"
CEROS = {"MUY_POSITIVO": 0, "POSITIVO": 0, "NEUTRO": 0, "NEGATIVO": 0, "MUY_NEGATIVO": 0}
PEDIDOS_COMUNIDAD = {"comunidad", "sentimiento", "temas", "desercion", "frustracion", "dudas"}
PEDIDOS_CONTENIDO = {"aprobados", "detalle"}


class DashboardSimulado:
    """Hace de Java: devuelve datos como los de la base de pruebas y anota los parámetros de cada pedido."""

    def __init__(self, vacio=False):
        self.pedidos = []
        self.vacio = vacio
        self.falla = set()
        self.anterior_vacio = True  # el período anterior al de la demo no tiene mensajes

    def _anotar(self, nombre, *args):
        self.pedidos.append((nombre, args))
        if nombre in self.falla:
            raise ErrorJava(500, "ERROR_INTERNO", "No se pudo procesar el pedido.")

    def dashboard_contenido(self, desde, hasta):
        self._anotar("contenido", desde, hasta)
        v = 0 if self.vacio else 1
        return {
            "porRevisar": {"total": 3 * v, "porTipo": {"POST_LINKEDIN": 0, "CASO_EXITO": 2 * v, "FAQ": v},
                           "masAntiguo": None if self.vacio else "2026-10-05T17:31:41Z"},
            "revision": [{"tipo": "POST_LINKEDIN", "medianaSeg": None if self.vacio else 60.0, "n": 9 * v},
                         {"tipo": "CASO_EXITO", "medianaSeg": None if self.vacio else 5.0, "n": 7 * v},
                         {"tipo": "FAQ", "medianaSeg": None if self.vacio else 1000.0, "n": v}],
            "aprobacion": {"aprobados": 16 * v, "rechazados": v},
            "embudo": {"logros": 16 * v, "publicables": 9 * v, "noPublicables": 7 * v, "conPostAprobado": 9 * v},
            "aprobadosPorSemana": [{"inicio": "2026-09-28", "cantidad": 4 * v},
                                   {"inicio": "2026-10-05", "cantidad": 9 * v}],
            "logroAAprobacion": {"medianaHoras": None if self.vacio else 146.0, "n": 9 * v},
            "mensajesDePersonas": 64 * v,
            "activosOci": 36 * v,
        }

    def dashboard_comunidad(self, desde, hasta):
        self._anotar("comunidad", desde, hasta)
        v = 0 if self.vacio else 1
        return {"alumnos": {"total": 9 * v, "activos7Dias": 2 * v, "activos30Dias": 9 * v, "dudas": 18 * v},
                "bot": {"respondidas": 4 * v, "derivadas": 6 * v, "sinPasarPorElBot": 17 * v,
                        "segundosMediana": None if self.vacio else 6.0},
                "derivadasPorTema": [] if self.vacio else [{"tema": "contenido_curso", "cantidad": 2},
                                                           {"tema": "evaluaciones", "cantidad": 1}]}

    def dashboard_sentimiento(self, desde, hasta, agrupar, excluir_otro, rol="todos"):
        self._anotar("sentimiento", desde, hasta, agrupar, excluir_otro, rol)
        puntos = [{"inicio": "2026-09-28", "cantidades": dict(CEROS)},
                  {"inicio": "2026-10-05", "cantidades": dict(CEROS)}]
        anterior = hasta < datetime.now(ui.ZONA).date()  # el período actual siempre termina hoy
        if not self.vacio and not (anterior and self.anterior_vacio):
            # Alumnos: +28 (n = 32) y +33 (n = 3); con los mentores se suman 3 positivos más
            puntos[0]["cantidades"].update(MUY_POSITIVO=9, POSITIVO=4, NEUTRO=15, NEGATIVO=3, MUY_NEGATIVO=1)
            puntos[1]["cantidades"].update(MUY_POSITIVO=1, NEUTRO=2)
            if rol == "todos":
                puntos[1]["cantidades"]["POSITIVO"] = 3
        return {"agrupar": agrupar, "puntos": puntos}

    def dashboard_temas(self, desde, hasta, excluir_otro, rol="todos"):
        self._anotar("temas", desde, hasta, excluir_otro, rol)
        temas = [] if self.vacio else [{"tema": "contenido_curso", "actual": 9, "anterior": 0, "variacion": 9},
                                       {"tema": "empleo", "actual": 4, "anterior": 0, "variacion": 4},
                                       {"tema": "becas_pagos", "actual": 0, "anterior": 2, "variacion": -2}]
        return {"periodoAnterior": {"desde": "2026-08-16", "hasta": "2026-09-14"}, "temas": temas}

    def dashboard_desercion(self, dias):
        self._anotar("desercion", dias)
        personas = [] if self.vacio else [{"nombre": "<b>Camila</b>", "ultimoMensaje": "2026-09-28T19:10:00Z",
                                           "diasSinEscribir": 16, "mensajes": 4}]
        return {"dias": dias, "personas": personas}

    def dashboard_frustracion(self, desde, hasta):
        self._anotar("frustracion", desde, hasta)
        personas = [] if self.vacio else [{"nombre": "Diego", "motivos": ["MUY_NEGATIVO"], "negativosEnPeriodo": 1,
                                           "negativosEnUltimos3": 1, "ultimoNegativo": "2026-09-28T18:40:00Z"}]
        return {"personas": personas}

    def dashboard_dudas(self, desde, hasta, horas, excluir_otro):
        self._anotar("dudas", desde, hasta, horas, excluir_otro)
        dudas = [] if self.vacio else [
            {"mensajeId": 17, "discordId": "1554205178671009863", "fecha": "2026-09-28T18:56:30Z",
             "tema": "herramientas_entorno", "derivada": True, "canal": "dudas", "autorNombre": "Ana",
             "texto": SCRIPT, "servidorId": "1554157903701741700", "canalId": "1554158212742127821"},
            # Sin servidor (un mensaje de antes de V2): sin botón, pero se ve
            {"mensajeId": 18, "discordId": "1554205178671009864", "fecha": "2026-09-28T19:00:00Z",
             "tema": "empleo", "derivada": False, "canal": "dudas", "autorNombre": "Beto",
             "texto": "¿hay bolsa de empleo?", "servidorId": None, "canalId": "1554158212742127821"},
        ]
        return {"total": len(dudas), "dudas": dudas}

    def listar_borradores(self, estado="PENDIENTE", tipo=None, limite=100):
        if estado != "APROBADO":
            return []  # la página Borradores corre primero (es la de inicio)
        self._anotar("aprobados", estado, tipo, limite)
        if self.vacio:
            return []
        return [{"id": 12, "tipo": "POST_LINKEDIN", "estado": "APROBADO", "creadoEn": "2026-10-05T15:00:00Z",
                 "extracto": "🎉 Camila consiguió su primer trabajo…", "autorNombre": "Camila", "canal": "logros",
                 "semana": None, "revisadoPor": "harrison", "revisadoEn": "2026-10-06T15:00:00Z"},
                {"id": 13, "tipo": "FAQ", "estado": "APROBADO", "creadoEn": "2026-10-05T15:00:00Z",
                 "extracto": "Preguntas frecuentes…", "autorNombre": None, "canal": None, "semana": "2026-W40",
                 "revisadoPor": "harrison", "revisadoEn": "2026-10-06T16:00:00Z"}]

    def detalle(self, borrador_id):
        self._anotar("detalle", borrador_id)
        return {"id": borrador_id, "textoIa": "texto de la IA", "textoFinal": f"Texto final {borrador_id} <b>listo</b>"}

    def nombres(self):
        return {n for n, _ in self.pedidos}

    def args(self, nombre):
        return [a for n, a in self.pedidos if n == nombre][-1]

    def todos(self, nombre):
        return [a for n, a in self.pedidos if n == nombre]


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("PANEL_USUARIOS", auth.con_usuario("", "harrison", auth.crear_registro("clave-larga-123")))
    monkeypatch.setenv("API_KEY_PANEL", "clave-de-prueba")
    monkeypatch.delenv("PANEL_MINUTOS_POR_HISTORIA", raising=False)
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


def _contenido(monkeypatch, java):
    at = _dashboard(monkeypatch, java)
    java.pedidos.clear()
    at.segmented_control(key="dash_vista").set_value("Contenido")
    return at.run()


def _metricas(at) -> dict:
    return {m.label: m.value for m in at.metric}


def _textos(at) -> list[str]:
    return [c.value for c in at.caption] + [m.value for m in at.markdown]


def _graficos(at):
    return at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")


def _enlaces(at) -> list[str]:
    return [b.proto.url for b in at.get("link_button")]


# ── Vista Comunidad (la de inicio) ──

def test_comunidad_pide_solo_lo_suyo_con_los_parametros_por_defecto(monkeypatch):
    java = DashboardSimulado()

    at = _dashboard(monkeypatch, java)

    assert not at.exception
    hoy = datetime.now(ui.ZONA).date()
    desde = hoy - timedelta(days=29)
    assert java.args("contenido") == (desde, hoy)  # la franja de valor
    assert java.args("comunidad") == (desde, hoy)
    # Alumnos por semana, toda la comunidad y el período anterior de igual largo
    assert java.todos("sentimiento") == [(desde, hoy, "semana", False, "alumnos"),
                                         (desde, hoy, "semana", False, "todos"),
                                         (desde - timedelta(days=30), desde - timedelta(days=1), "semana", False,
                                          "alumnos")]
    assert java.args("temas") == (desde, hoy, False, "alumnos")
    assert java.args("desercion") == (14,)
    assert java.args("frustracion") == (desde, hoy)
    assert java.args("dudas") == (desde, hoy, 24, False)
    assert not java.nombres() & PEDIDOS_CONTENIDO


def test_comunidad_muestra_las_tarjetas_con_su_n(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    metricas = _metricas(at)
    # La franja (P1 y P4) y las 4 tarjetas, en ese orden (DEC-153)
    assert [m.label for m in at.metric][:6] == [
        "Horas ahorradas a Marketing (estimado)", "Historias encontradas solas", "Clima de los alumnos",
        "Dudas que respondió el bot", "Dudas sin respuesta (más de 24 h)", "Alumnos que necesitan apoyo"]
    assert metricas["Clima de los alumnos"] == "+29"   # (14 − 4) / 35
    assert metricas["Dudas que respondió el bot"] == "40 %"
    assert metricas["Dudas sin respuesta (más de 24 h)"] == "2"
    assert metricas["Alumnos que necesitan apoyo"] == "1 de 9"
    textos = _textos(at)
    assert any("n = 35 mensajes de alumnos" in t for t in textos)
    assert any("Toda la comunidad (también mentores): +34 (n = 38)" in t for t in textos)
    assert any("Sin datos del período anterior para comparar." in t for t in textos)
    assert any("4 de 10 dudas que vio el bot (n = 10)" in t and "6 s (mediana)" in t for t in textos)
    assert any("De 18 dudas de alumnos del período" in t for t in textos)
    assert "Sin clasificar" not in metricas  # T12: se quitó de la vista


def test_comunidad_compara_con_el_periodo_anterior_cuando_tiene_datos(monkeypatch):
    java = DashboardSimulado()
    java.anterior_vacio = False

    at = _dashboard(monkeypatch, java)

    clima = next(m for m in at.metric if m.label == "Clima de los alumnos")
    assert clima.proto.delta.startswith("+0 frente al período anterior (n = 35)")
    assert not any("Sin datos del período anterior" in t for t in _textos(at))


def test_comunidad_dibuja_tres_graficos_y_las_listas(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    assert not at.exception
    assert len(_graficos(at)) == 3  # clima, alumnos activos y temas
    tablas = [d.value for d in at.dataframe]
    clima = tablas[0]
    assert clima["n"].tolist() == [32, 3]
    assert clima["Índice"].tolist() == ["+28", "+33"]
    a_quien = next(t for t in tablas if "Alumno" in t.columns)
    assert a_quien["Alumno"].tolist() == ["<b>Camila</b>", "Diego"]  # como datos, no como HTML
    assert a_quien["Motivo"].tolist() == ["Lleva 16 días sin escribir", "Un mensaje muy negativo"]
    falta = next(t for t in tablas if "Dudas derivadas" in t.columns)
    assert falta["Tema"].tolist() == ["Contenido del curso", "Evaluaciones"]


def test_abrir_en_discord_lleva_al_mensaje(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    # La duda sin servidor no tiene botón
    assert _enlaces(at) == ["https://discord.com/channels/1554157903701741700/1554158212742127821/1554205178671009863"]


def test_una_duda_con_html_se_muestra_escapada(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    assert any(c.value == SCRIPT for c in at.code)
    assert any("derivada a un mentor" in t.value for t in at.text)
    assert not any("<script>" in m.value or "<b>Camila" in m.value for m in at.markdown)
    assert not any("<script>" in c.value for c in at.caption)


def test_los_atajos_y_los_ajustes_envian_sus_valores(monkeypatch):
    java = DashboardSimulado()
    at = _dashboard(monkeypatch, java)
    hoy = datetime.now(ui.ZONA).date()

    at.segmented_control(key="dash_atajo").set_value("7 días")
    at.number_input(key="dash_dias").set_value(3)
    at.number_input(key="dash_horas").set_value(48)
    at = at.run()

    assert not at.exception
    desde = hoy - timedelta(days=6)
    assert java.args("comunidad") == (desde, hoy)
    assert java.todos("sentimiento")[-3][2] == "dia"  # con 7 días, el clima va por día
    assert java.args("desercion") == (3,)
    assert java.args("dudas") == (desde, hoy, 48, False)
    assert "Dudas sin respuesta (más de 48 h)" in _metricas(at)

    at.segmented_control(key="dash_atajo").set_value("90 días")
    at = at.run()
    assert java.args("contenido") == (hoy - timedelta(days=89), hoy)


def test_elegir_fechas_muestra_el_calendario_y_un_periodo_a_medio_elegir_no_pide_nada(monkeypatch):
    java = DashboardSimulado()
    at = _dashboard(monkeypatch, java)
    assert not at.date_input  # con un atajo, no hay calendario

    at.segmented_control(key="dash_atajo").set_value("Elegir fechas")
    at = at.run()
    at.date_input(key="dash_periodo").set_value((date(2026, 9, 1), date(2026, 9, 30)))
    at = at.run()
    assert java.args("comunidad") == (date(2026, 9, 1), date(2026, 9, 30))

    antes = len(java.pedidos)
    at.date_input(key="dash_periodo").set_value((date(2026, 9, 1),))
    at = at.run()
    assert "Elige la fecha final del período." in [i.value for i in at.info]
    assert len(java.pedidos) == antes


# ── La franja de valor (P1 y P4) ──

def test_p1_muestra_el_supuesto_con_los_minutos_por_defecto(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    # (30 − 1 min de revisión) × 9 historias = 261 min = 4,35 h
    assert _metricas(at)["Horas ahorradas a Marketing (estimado)"] == "≈ 4,3 h"
    textos = _textos(at)
    assert ("Estimado: supone 30 min por historia encontrada y redactada a mano, menos la revisión en el panel."
            in textos)
    assert any("mediana de 9 posts" in t and "× 9 logros con su post aprobado" in t for t in textos)
    assert _metricas(at)["Historias encontradas solas"] == "9"
    assert any("de 64 mensajes de personas y 16 logros" in t for t in textos)


def test_p1_usa_los_minutos_configurados(monkeypatch):
    monkeypatch.setenv("PANEL_MINUTOS_POR_HISTORIA", "45")

    at = _dashboard(monkeypatch, DashboardSimulado())

    assert _metricas(at)["Horas ahorradas a Marketing (estimado)"] == "≈ 6,6 h"  # (45 − 1) × 9 / 60
    assert any(t.startswith("Estimado: supone 45 min por historia") for t in _textos(at))


def test_p5_va_en_la_barra_lateral(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    assert [m.value for m in at.sidebar.metric] == ["36"]
    assert at.sidebar.metric[0].label == "Archivos guardados en OCI"


# ── Vista Contenido (Marketing) ──

def test_contenido_pide_solo_lo_suyo(monkeypatch):
    java = DashboardSimulado()

    at = _contenido(monkeypatch, java)

    assert not at.exception
    assert java.nombres() == {"contenido", "aprobados", "detalle"}
    assert java.args("aprobados") == ("APROBADO", None, 20)


def test_contenido_muestra_tarjetas_graficos_y_listos_para_publicar(monkeypatch):
    at = _contenido(monkeypatch, DashboardSimulado())

    metricas = _metricas(at)
    assert metricas["Por revisar"] == "3"
    assert metricas["Tiempo de revisión de un post"] == "60 s"
    assert metricas["Tasa de aprobación"] == "94 %"
    assert metricas["Del logro al post aprobado"] == "6,1 días"
    textos = _textos(at)
    assert any(t.startswith("2 casos de éxito y 1 FAQ. El más antiguo espera hace") for t in textos)
    assert "Mediana, n = 9." in textos
    assert any("Caso de éxito: 5 s (n = 7). FAQ: 1.000 s (n = 1)." in t for t in textos)
    assert "16 aprobados de 17 revisados (n = 17)." in textos
    assert any("7 no publicables" in t for t in textos)
    assert len(_graficos(at)) == 2  # embudo y aprobados por semana
    listos = at.dataframe[0].value
    assert listos["Dónde se usa"].tolist() == ["LinkedIn", "#anuncios de Discord y la web"]
    # El texto final, escapado y con el botón de copiar de st.code
    assert any(c.value == "Texto final 12 <b>listo</b>" for c in at.code)


def test_contenido_el_embudo_muestra_los_porcentajes(monkeypatch):
    at = _contenido(monkeypatch, DashboardSimulado())

    datos = "".join(g.proto.spec for g in _graficos(at))
    for g in _graficos(at):
        for d in g.proto.datasets:
            datos += convert_arrow_bytes_to_pandas_df(d.data.data).to_string()
    assert "9 · 56 % de los logros" in datos
    assert "9 · 100 % de los publicables" in datos


# ── Sin datos, fallas y tema ──

def test_sin_datos_lo_dice_y_no_se_rompe(monkeypatch):
    java = DashboardSimulado(vacio=True)

    at = _dashboard(monkeypatch, java)

    assert not at.exception
    avisos = [i.value for i in at.info] + [s.value for s in at.success]
    assert "No hay mensajes de alumnos con sentimiento en este período." in avisos
    assert "No hay temas en este período." in avisos
    assert "No hay dudas sin respuesta en este período." in avisos
    assert "Todavía no escribió ningún alumno." in avisos
    assert len(_graficos(at)) == 0
    metricas = _metricas(at)
    assert metricas["Clima de los alumnos"] == "—"
    assert metricas["Dudas que respondió el bot"] == "—"
    assert metricas["Horas ahorradas a Marketing (estimado)"] == "≈ 0,0 h"

    at.segmented_control(key="dash_vista").set_value("Contenido")
    at = at.run()
    assert not at.exception
    avisos = [i.value for i in at.info]
    assert "No hay logros en este período." in avisos
    assert "No se aprobó nada en este período." in avisos
    assert "Todavía no hay borradores aprobados." in avisos
    assert _metricas(at)["Tiempo de revisión de un post"] == "—"


def test_si_un_dato_falla_los_demas_se_ven(monkeypatch):
    java = DashboardSimulado()
    java.falla = {"temas", "frustracion", "contenido"}

    at = _dashboard(monkeypatch, java)

    assert not at.exception
    avisos = [w.value for w in at.warning]
    assert len(avisos) == 3
    assert "No se pudo cargar la franja de valor: No se pudo procesar el pedido." in avisos
    assert _metricas(at)["Clima de los alumnos"] == "+29"
    assert any(c.value == SCRIPT for c in at.code)  # las dudas se ven igual
    assert not at.sidebar.metric  # sin P5, pero sin error


@pytest.mark.parametrize("oscuro, esperado, ausente", [(False, "#184f95", "#8cc0fb"), (True, "#8cc0fb", "#184f95")])
def test_la_paleta_cambia_con_el_tema(monkeypatch, oscuro, esperado, ausente):
    monkeypatch.setattr(ui, "tema_oscuro", lambda: oscuro)

    at = _dashboard(monkeypatch, DashboardSimulado())

    spec = "".join(g.proto.spec for g in _graficos(at))
    assert esperado in spec
    assert ausente not in spec
