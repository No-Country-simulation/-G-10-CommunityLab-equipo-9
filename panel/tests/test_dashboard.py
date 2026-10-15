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


def _dashboard(monkeypatch, java, vista="Comunidad"):
    monkeypatch.setattr(ui, "obtener_cliente", lambda: java)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["usuario"] = "harrison"
    at.session_state["ultimo_uso"] = time.monotonic()
    at.run()
    at.switch_page("paginas/dashboard.py")
    return _correr(at, vista)


def _correr(at, vista="Comunidad"):
    # AppTest no tiene cómo hacer clic en una pestaña: se elige por su key en cada corrida
    at.session_state["dash_vista"] = vista
    return at.run()


def _html(at) -> str:
    """Todo el HTML de la página (franja, tarjetas y títulos), en un solo texto."""
    return "\n".join(e.proto.body for e in at.get("html"))


def _textos(at) -> list[str]:
    return [t.value for t in at.text]


def _graficos(at):
    return at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")


def _enlaces(at) -> list[str]:
    return [b.proto.url for b in at.get("link_button")]


def _en_orden(texto: str, partes: list[str]) -> bool:
    posiciones = [texto.find(p) for p in partes]
    return -1 not in posiciones and posiciones == sorted(posiciones)


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
    assert [t.label for t in at.tabs] == ["Comunidad", "Contenido"]


def test_comunidad_muestra_franja_tarjetas_y_secciones_en_orden_con_su_n(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    html = _html(at)
    # DEC-153: franja → 4 tarjetas → gráficos → listas
    assert _en_orden(html, ["Lo que hizo InsightEdu en los últimos 30 días", "Clima de los alumnos<",
                            "Dudas que respondió el bot", "Dudas sin respuesta (más de 24 h)",
                            "Alumnos que necesitan apoyo", "Clima de los alumnos por semana", "Alumnos activos",
                            "De qué hablan los alumnos", "A quién ayudar hoy", "Esperan respuesta (2)",
                            "A quién escribir (2)", "Qué falta en los documentos (3)"])
    assert ">+29<" in html  # (14 − 4) / 35
    assert "n = 35 mensajes con sentimiento" in html
    assert "Toda la comunidad, con mentores: +34 (n = 38)." in html
    assert "Sin datos del período anterior para comparar." in html
    assert ">40 %<" in html
    assert "4 de 10 dudas que vio el bot (n = 10) · respondió en 6 s (mediana)" in html
    assert "6 se derivaron a un mentor. Otras 17 llegaron por lote" in html
    assert "de 18 dudas de alumnos del período" in html
    assert "de 9 · posible deserción" in html
    assert "Sin clasificar" not in html  # T12: se quitó de la vista


def test_comunidad_compara_con_el_periodo_anterior_cuando_tiene_datos(monkeypatch):
    java = DashboardSimulado()
    java.anterior_vacio = False

    at = _dashboard(monkeypatch, java)

    assert "+0 frente al período anterior (n = 35)." in _html(at)
    assert "Sin datos del período anterior" not in _html(at)


def test_comunidad_dibuja_tres_graficos_y_la_tabla_del_clima(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    assert not at.exception
    assert len(_graficos(at)) == 3  # clima, alumnos activos y temas
    clima = at.dataframe[0].value
    assert clima["n"].tolist() == [32, 3]
    assert clima["Índice"].tolist() == ["+28", "+33"]
    html = _html(at)
    spec = "".join(g.proto.spec for g in _graficos(at))
    assert '"orient": "top"' in spec and "Muy negativo" in spec  # la leyenda, arriba del clima
    assert "Contenido del curso es el tema más frecuente: 9 de 13 mensajes." in html


def test_a_quien_ayudar_muestra_los_casos_con_textos_escapados(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    textos = _textos(at)
    # Los textos y los nombres de los alumnos van con st.text, nunca dentro del HTML (DEC-158)
    assert any(SCRIPT in t for t in textos)
    assert "<b>Camila</b> · posible deserción" in textos
    assert "Diego · posible frustración" in textos
    html = _html(at)
    assert "<script>alert" not in html and "&lt;script&gt;" not in html
    assert "Camila" not in html and "Diego" not in html and "Ana ·" not in html
    assert "16 días sin escribir · 4 mensajes en total" in html
    assert "Un mensaje muy negativo en el período" in html
    assert not any("<script>" in m.value or "<b>Camila" in m.value for m in at.markdown)


def test_abrir_en_discord_lleva_al_mensaje(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    # La duda sin servidor no tiene botón
    assert _enlaces(at) == ["https://discord.com/channels/1554157903701741700/1554158212742127821/1554205178671009863"]


def test_los_atajos_y_los_ajustes_envian_sus_valores(monkeypatch):
    java = DashboardSimulado()
    at = _dashboard(monkeypatch, java)
    hoy = datetime.now(ui.ZONA).date()

    at.pills(key="dash_atajo").set_value("7 días")
    at.number_input(key="dash_dias").set_value(3)
    at.number_input(key="dash_horas").set_value(48)
    at = _correr(at)

    assert not at.exception
    desde = hoy - timedelta(days=6)
    assert java.args("comunidad") == (desde, hoy)
    assert java.todos("sentimiento")[-3][2] == "dia"  # con 7 días, el clima va por día
    assert java.args("desercion") == (3,)
    assert java.args("dudas") == (desde, hoy, 48, False)
    html = _html(at)
    assert "Dudas sin respuesta (más de 48 h)" in html
    assert "Lo que hizo InsightEdu en los últimos 7 días" in html
    assert "Clima de los alumnos por día" in html

    at.pills(key="dash_atajo").set_value("90 días")
    at = _correr(at)
    assert java.args("contenido") == (hoy - timedelta(days=89), hoy)


def test_elegir_fechas_muestra_el_calendario_y_un_periodo_a_medio_elegir_no_pide_nada(monkeypatch):
    java = DashboardSimulado()
    at = _dashboard(monkeypatch, java)
    assert not at.date_input  # con un atajo, no hay calendario

    at.pills(key="dash_atajo").set_value("Elegir fechas")
    at = _correr(at)
    at.date_input(key="dash_periodo").set_value((date(2026, 9, 1), date(2026, 9, 30)))
    at = _correr(at)
    assert java.args("comunidad") == (date(2026, 9, 1), date(2026, 9, 30))
    assert "Lo que hizo InsightEdu del 1 sep al 30 sep" in _html(at)

    antes = len(java.pedidos)
    at.date_input(key="dash_periodo").set_value((date(2026, 9, 1),))
    at = _correr(at)
    assert "Elige la fecha final del período." in [i.value for i in at.info]
    assert len(java.pedidos) == antes


# ── La franja de valor (P1 y P4) y la barra lateral (P5) ──

def test_p1_muestra_el_supuesto_con_los_minutos_por_defecto(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    html = _html(at)
    # (30 − 1 min de revisión) × 9 historias = 261 min = 4,35 h
    assert ">≈ 4,3 h<" in html
    assert "Estimado: supone 30 min por historia encontrada y redactada a mano, menos la revisión en el panel" in html
    assert "mediana de 9 posts) · 9 historias aprobadas" in html
    assert ">9 historias<" in html
    assert "De 64 mensajes de personas y 16 logros, 9 eran publicables" in html


def test_p1_usa_los_minutos_configurados(monkeypatch):
    monkeypatch.setenv("PANEL_MINUTOS_POR_HISTORIA", "45")

    at = _dashboard(monkeypatch, DashboardSimulado())

    assert ">≈ 6,6 h<" in _html(at)  # (45 − 1) × 9 / 60
    assert "Estimado: supone 45 min por historia" in _html(at)


def test_p5_va_en_la_barra_lateral(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado())

    lateral = "\n".join(e.proto.body for e in at.sidebar.get("html"))
    assert "Guardados en OCI" in lateral and "36 activos" in lateral
    assert at.sidebar.text[0].value == "Sesión: harrison"  # debajo del usuario


# ── Vista Contenido (Marketing) ──

def test_contenido_pide_solo_lo_suyo(monkeypatch):
    java = DashboardSimulado()

    _dashboard(monkeypatch, java)
    java.pedidos.clear()
    at = _dashboard(monkeypatch, java, vista="Contenido")

    assert not at.exception
    assert java.nombres() == {"contenido", "aprobados", "detalle"}
    assert java.args("aprobados") == ("APROBADO", None, 20)


def test_contenido_muestra_tarjetas_graficos_y_listos_para_publicar(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado(), vista="Contenido")

    assert not at.exception
    html = _html(at)
    assert _en_orden(html, ["Lo que hizo InsightEdu", "Por revisar", "Tiempo de revisión (mediana)",
                            "Tasa de aprobación", "Del logro al contenido aprobado", "De logro a contenido aprobado",
                            "Contenido aprobado por semana", "Listos para publicar"])
    assert "2 casos de éxito y 1 FAQ" in html
    assert "El más antiguo espera hace" in html
    assert ">1 min<" in html and "por post de LinkedIn · n = 9" in html
    assert "Caso de éxito: 5 s (n = 7) · FAQ: 16 min 40 s (n = 1)" in html
    assert ">94 %<" in html and "16 de 17 borradores revisados (n = 17)" in html
    assert ">6 días<" in html and "mediana · n = 9 posts" in html
    assert "La IA vio publicables 9 de 16 logros, y Marketing aprobó 9." in html
    assert "No publicables (7)" in html
    assert "9 piezas la semana del 5 oct" in html
    assert len(_graficos(at)) == 2  # embudo y aprobados por semana
    # T13: solo el de la página (la barra lateral tiene su propia navegación)
    assert [p.proto.label for p in at.main.get("page_link")] == ["Ir a Borradores"]
    listos = at.dataframe[0].value
    assert listos["Dónde se publica"].tolist() == ["LinkedIn de CommunityLab", "Canal #anuncios y la web"]
    assert listos["De quién"].tolist() == ["Camila", "Varias personas"]
    # Sin fila elegida, el texto final del más reciente, escapado y con el botón de copiar de st.code
    assert any(c.value == "Texto final 12 <b>listo</b>" for c in at.code)


def test_contenido_el_embudo_muestra_los_porcentajes(monkeypatch):
    at = _dashboard(monkeypatch, DashboardSimulado(), vista="Contenido")

    datos = "".join(g.proto.spec for g in _graficos(at))
    for g in _graficos(at):
        for d in g.proto.datasets:
            datos += convert_arrow_bytes_to_pandas_df(d.data.data).to_string()
    assert "9 · 56 %" in datos
    assert "9 · 100 %" in datos


def test_contenido_dice_si_cada_post_se_publico_en_linkedin(monkeypatch):
    """T13 (M12): la columna "En LinkedIn" de Listos para publicar, con cada estado."""
    java = DashboardSimulado()
    aprobados = java.listar_borradores

    def con_linkedin(estado="PENDIENTE", tipo=None, limite=100):
        lista = aprobados(estado, tipo, limite)
        if estado != "APROBADO":
            return lista
        posts = [{**lista[0], "id": 20 + i, "linkedin": {"estado": e, "postId": None, "en": None, "motivo": None}}
                 for i, e in enumerate(["PUBLICADO", "APAGADO", "SIMULADO", "ERROR", None])]
        return posts + lista[1:]

    java.listar_borradores = con_linkedin
    at = _dashboard(monkeypatch, java, vista="Contenido")

    assert not at.exception
    listos = at.dataframe[0].value
    assert listos["En LinkedIn"].tolist() == ["Publicado", "No: apagado", "Simulado", "Falló", "Sin dato", "—"]
    assert list(listos.columns) == ["Qué", "De quién", "Dónde se publica", "En LinkedIn", "Aprobado"]


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
    html = _html(at)
    assert "Clima de los alumnos</div><div style=\"font-size: 30px; font-weight: 600; line-height: 1.15\">—" in html
    assert ">≈ 0,0 h<" in html

    at = _correr(at, "Contenido")
    assert not at.exception
    avisos = [i.value for i in at.info]
    assert "No hay logros en este período." in avisos
    assert "No se aprobó nada en este período." in avisos
    assert "Todavía no hay borradores aprobados." in avisos
    assert "No hay nada pendiente." in _html(at)


def test_si_un_dato_falla_los_demas_se_ven(monkeypatch):
    java = DashboardSimulado()
    java.falla = {"temas", "frustracion", "contenido"}

    at = _dashboard(monkeypatch, java)

    assert not at.exception
    avisos = [w.value for w in at.warning]
    assert len(avisos) == 3
    assert "No se pudo cargar la franja de valor: No se pudo procesar el pedido." in avisos
    assert ">+29<" in _html(at)
    assert any(SCRIPT in t for t in _textos(at))  # las dudas se ven igual
    assert not at.sidebar.get("html")  # sin P5, pero sin error


def test_los_colores_no_dependen_del_tema_y_las_paletas_estan_en_la_configuracion(monkeypatch):
    """
    DEC-156: al cambiar el tema, Streamlit no vuelve a correr la página. Por eso la página no elige colores según
    el tema: los del sentimiento los pone Streamlit desde config.toml, uno por tema.
    """
    import tomllib

    at = _dashboard(monkeypatch, DashboardSimulado())
    spec = "".join(g.proto.spec for g in _graficos(at))
    for color in ("#9b2626", "#184f95", "#f4877d", "#8cc0fb"):
        assert color not in spec

    config = tomllib.loads((Path(APP).parent / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["theme"]["light"]["chartCategoricalColors"][:5] == ["#9b2626", "#e8726a", "#dcdad3", "#6da7ec",
                                                                       "#184f95"]
    assert config["theme"]["dark"]["chartCategoricalColors"][:5] == ["#f4877d", "#a5453e", "#3b3e46", "#3b6db3",
                                                                      "#8cc0fb"]
    assert config["client"]["toolbarMode"] == "viewer"  # deja el selector de tema en el menú
