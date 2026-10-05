"""
Página "Dashboard" (T08, N5, OE5): el clima de la comunidad, los temas del momento y a quién ayudar.

Java calcula y esta página solo dibuja (DEC-123), con los gráficos que trae Streamlit.
Cada indicador se pide aparte: si uno falla, los demás se siguen viendo.
Los nombres y los textos de los alumnos van con st.dataframe, st.text o ui.mostrar_texto (escapados), nunca en markdown.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

import ui
from cliente_java import ErrorJava

SENTIMIENTOS = {
    "MUY_POSITIVO": "Muy positivo",
    "POSITIVO": "Positivo",
    "NEUTRO": "Neutro",
    "NEGATIVO": "Negativo",
    "MUY_NEGATIVO": "Muy negativo",
}
# Del verde al rojo, en el orden de SENTIMIENTOS
COLORES = ["#15803d", "#86efac", "#9ca3af", "#fca5a5", "#b91c1c"]

TEMAS = {
    "inscripciones": "Inscripciones",
    "becas_pagos": "Becas y pagos",
    "calendario_clases": "Calendario de clases",
    "evaluaciones": "Evaluaciones",
    "contenido_curso": "Contenido del curso",
    "herramientas_entorno": "Herramientas y entorno",
    "plataforma_acceso": "Plataforma y acceso",
    "proyectos": "Proyectos",
    "empleo": "Empleo",
    "comunidad": "Comunidad",
    "otro": "Otro (no es del curso)",
}

MOTIVOS = {"MUY_NEGATIVO": "Un mensaje muy negativo", "DOS_DE_TRES": "2 negativos en sus últimos 3"}

cliente = ui.exigir_cliente()


def _pedir(funcion, *args):
    """Llama a Java; si falla, avisa en ese indicador y devuelve None (la página sigue)."""
    try:
        return funcion(*args)
    except ErrorJava as e:
        st.warning(f"No se pudo cargar este indicador: {e.mensaje}")
        return None


def _tema(clave: str | None) -> str:
    return TEMAS.get(clave or "", clave or "—")


# ── Controles ──

hoy = datetime.now(ui.ZONA).date()  # el "hoy" de Bogotá, como Java (no el del contenedor, en UTC)
with st.container(border=True):
    col_periodo, col_agrupar, col_otro = st.columns([2, 1, 1])
    periodo = col_periodo.date_input("Período", value=(hoy - timedelta(days=29), hoy), max_value=hoy,
                                     format="YYYY-MM-DD", key="dash_periodo")
    agrupar = col_agrupar.radio("Ver por", ["Día", "Semana"], horizontal=True, key="dash_agrupar")
    excluir_otro = col_otro.checkbox("Excluir el tema «otro»", key="dash_excluir_otro",
                                     help="Las preguntas que no son del curso")
    col_desercion, col_horas = st.columns(2)
    dias_desercion = col_desercion.number_input("Deserción: días sin escribir", min_value=1, max_value=365, value=14,
                                                step=1, key="dash_dias")
    horas_sin_responder = col_horas.number_input("Dudas sin responder después de (horas)", min_value=0,
                                                 max_value=2160, value=24, step=1, key="dash_horas")

if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info("Elige la fecha final del período.")
    st.stop()
desde, hasta = periodo
if (hasta - desde).days + 1 > 366:
    st.warning("El período puede tener hasta 366 días.")
    st.stop()
agrupar_java = "semana" if agrupar == "Semana" else "dia"

# ── 1. Totales (el cuadro de métricas del panel viejo) ──

with st.container(border=True):
    st.subheader("Resumen del período")
    totales = _pedir(cliente.dashboard_totales, desde, hasta)
    if totales:
        columnas = st.columns(6)
        columnas[0].metric("Mensajes", totales["mensajes"])
        columnas[1].metric("Personas activas", totales["personasActivas"])
        columnas[2].metric("Dudas", totales["dudas"])
        columnas[3].metric("Logros", totales["logros"])
        columnas[4].metric("Sin clasificar", totales["sinClasificar"])
        columnas[5].metric("Borradores pendientes", totales["borradoresPendientes"])
        st.caption("Mensajes de personas (no bots) en el período. Dudas y logros: solo los ya clasificados. "
                   "Borradores pendientes: los de hoy, sin importar el período.")

# ── 2. Sentimiento y temas ──

col_sentimiento, col_temas = st.columns(2)

with col_sentimiento:
    with st.container(border=True):
        st.subheader("Clima de la comunidad")
        sentimiento = _pedir(cliente.dashboard_sentimiento, desde, hasta, agrupar_java, excluir_otro)
        if sentimiento:
            puntos = sentimiento.get("puntos") or []
            if not any(sum(p["cantidades"].values()) for p in puntos):
                st.info("No hay mensajes con sentimiento en este período.")
            else:
                tabla = pd.DataFrame(
                    [{SENTIMIENTOS[s]: p["cantidades"].get(s, 0) for s in SENTIMIENTOS} for p in puntos],
                    index=[p["inicio"] for p in puntos])
                tabla.index.name = "Semana del" if agrupar_java == "semana" else "Día"
                st.bar_chart(tabla, color=COLORES, y_label="Mensajes")
        st.caption("Cuántos mensajes de cada sentimiento hubo cada día o semana. Solo mensajes de personas "
                   "clasificados OK y con sentimiento. Las semanas empiezan el lunes.")

with col_temas:
    with st.container(border=True):
        st.subheader("Temas en tendencia")
        temas = _pedir(cliente.dashboard_temas, desde, hasta, excluir_otro)
        if temas:
            lista = [t for t in temas.get("temas") or [] if t["actual"] or t["anterior"]]
            if not lista:
                st.info("No hay temas en este período.")
            else:
                tabla = pd.DataFrame({
                    "Tema": [_tema(t["tema"]) for t in lista],
                    "Este período": [t["actual"] for t in lista],
                    "Período anterior": [t["anterior"] for t in lista],
                    "Cambio": [t["variacion"] for t in lista],
                })
                st.bar_chart(tabla, x="Tema", y=["Este período", "Período anterior"], horizontal=True,
                             stack=False, sort=False)
                st.dataframe(tabla, hide_index=True)
                anterior = temas.get("periodoAnterior") or {}
                st.caption(f"Comparado con el período anterior de igual largo "
                           f"({anterior.get('desde')} a {anterior.get('hasta')}). Solo mensajes OK de personas.")

# ── 3. A quién ayudar ──

st.subheader("A quién ayudar")

with st.container(border=True):
    st.markdown("**Posible deserción**")
    desercion = _pedir(cliente.dashboard_desercion, int(dias_desercion))
    if desercion is not None:
        personas = desercion.get("personas") or []
        if not personas:
            st.success(f"Ningún alumno lleva más de {int(dias_desercion)} días sin escribir.")
        else:
            st.dataframe(pd.DataFrame({
                "Alumno": [p["nombre"] for p in personas],
                "Último mensaje": [ui.fecha(p["ultimoMensaje"]) for p in personas],
                "Días sin escribir": [p["diasSinEscribir"] for p in personas],
                "Mensajes en total": [p["mensajes"] for p in personas],
            }), hide_index=True)
    st.caption("Alumnos cuyo último mensaje tiene más días que el umbral, contados desde hoy (no depende del "
               "período). Mentores y bots no cuentan.")

with st.container(border=True):
    st.markdown("**Posible frustración**")
    frustracion = _pedir(cliente.dashboard_frustracion, desde, hasta)
    if frustracion is not None:
        personas = frustracion.get("personas") or []
        if not personas:
            st.success("Ningún alumno muestra señales de frustración en este período.")
        else:
            st.dataframe(pd.DataFrame({
                "Alumno": [p["nombre"] for p in personas],
                "Motivo": [", ".join(MOTIVOS.get(m, m) for m in p["motivos"]) for p in personas],
                "Negativos en el período": [p["negativosEnPeriodo"] for p in personas],
                "Último negativo": [ui.fecha(p["ultimoNegativo"]) for p in personas],
            }), hide_index=True)
    st.caption("Un mensaje muy negativo en el período, o 2 negativos entre sus últimos 3 mensajes (DEC-121). "
               "Solo mensajes clasificados OK.")

with st.container(border=True):
    st.markdown("**Dudas sin responder**")
    dudas = _pedir(cliente.dashboard_dudas, desde, hasta, int(horas_sin_responder), excluir_otro)
    if dudas is not None:
        lista = dudas.get("dudas") or []
        if not lista:
            st.success("No hay dudas sin responder en este período.")
        else:
            total = dudas.get("total", len(lista))
            st.text(f"{total} dudas sin responder" + (f" (se muestran {len(lista)})" if total > len(lista) else ""))
            for d in lista:
                with st.container(border=True):
                    derivada = " · derivada a un mentor" if d.get("derivada") else ""
                    st.text(f"{d.get('autorNombre') or '—'} · #{d.get('canal') or '—'} · {ui.fecha(d.get('fecha'))}"
                            f" · {_tema(d.get('tema'))}{derivada}")
                    ui.mostrar_texto(d.get("texto"))
    st.caption("Dudas de alumnos con más horas que el umbral, que el bot no respondió y a las que ninguna otra "
               "persona contestó con «Responder» de Discord. Una duda derivada sigue aquí hasta que alguien la conteste.")
