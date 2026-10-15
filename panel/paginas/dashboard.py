"""
Página "Dashboard" (T08 y T12, N5, OE5): una vista por rol (DEC-153), con el diseño del prototipo aprobado.

- Comunidad (el Community Manager): el clima de los alumnos, si el bot ayuda, quién espera respuesta,
  a quién escribir y qué falta en los documentos.
- Contenido (Marketing): cuánto hay por revisar, cuánto tarda la revisión, si la IA propone cosas útiles
  y qué se aprobó.

Las dos empiezan con la franja "Lo que hizo InsightEdu en este período" y siguen por secciones: indicadores
clave (4 tarjetas) → gráficos → listas (DEC-153). Reglas (DEC-155): la n junto a cada porcentaje o índice,
la mediana para los tiempos y los alumnos separados de los mentores.

Java calcula y esta página solo dibuja (DEC-123). Cada dato se pide aparte: si uno falla, los demás se ven.

Seguridad de lo que se muestra (DEC-158): la franja, las tarjetas y los títulos son bloques HTML (st.html) que
llevan SOLO números y textos de esta página, siempre pasados por html.escape. Los nombres y los textos de los
alumnos NUNCA van en HTML ni en markdown: van con st.text, st.dataframe o ui.mostrar_texto, que los escapan.

Tema claro y oscuro (DEC-156): al cambiar el tema en el menú, Streamlit NO vuelve a correr esta página. Por eso
aquí no se elige ningún color según el tema: las tarjetas heredan el color del texto y usan fondos
semitransparentes, y los colores del sentimiento los pone Streamlit desde .streamlit/config.toml
(chartCategoricalColors de [theme.light] y [theme.dark]). Los gráficos son de Altair (viene con Streamlit).

Los colores, los estilos, los íconos y los bloques de HTML están en estilo.py desde T13: los comparte Borradores.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

import ui
from cliente_java import ErrorJava
from estilo import (ALERTA, BORDE, DESTINOS, ESPERA, ICONO_ALERTA, ICONO_DOCUMENTO, ICONO_RELOJ, PISTA, SERIE,
                    SUAVE, TIPOS_PLURAL)
from estilo import bloque as _bloque
from estilo import corto as _corto
from estilo import dia as _dia
from estilo import e as _e
from estilo import encabezado_lista as _encabezado_lista
from estilo import hace as _hace
from estilo import nota as _nota
from estilo import seccion as _seccion
from estilo import tarjeta as _tarjeta
from estilo import titulo as _titulo
from logros import en_linkedin_corto

# De muy negativo a muy positivo: el orden en que se dibujan las barras divergentes. Sus colores son los
# 5 primeros de chartCategoricalColors en config.toml, en este mismo orden
SENTIMIENTOS = {
    "MUY_NEGATIVO": "Muy negativo",
    "NEGATIVO": "Negativo",
    "NEUTRO": "Neutro",
    "POSITIVO": "Positivo",
    "MUY_POSITIVO": "Muy positivo",
}

# Los textos dentro de los gráficos: Streamlit cambia con el tema los ejes, pero no las marcas de texto. Este gris
# contrasta parecido en los dos fondos (🧪 4,3:1 sobre blanco y 4,4:1 sobre #0e1117)
TEXTO_GRAFICO = "#777a82"

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

MOTIVOS = {"MUY_NEGATIVO": "Un mensaje muy negativo en el período",
           "DOS_DE_TRES": "2 negativos en sus últimos 3 mensajes"}

ATAJOS = {"7 días": 7, "30 días": 30, "90 días": 90}
ELEGIR = "Elegir fechas"
MINUTOS_POR_DEFECTO = 30
CASOS_VISIBLES = 3  # en las tarjetas de "A quién ayudar hoy"; el resto, en "Ver todas"

# ── Ayudas ──

def _pedir(que: str, funcion, *args):
    """Llama a Java; si falla, avisa qué no se pudo cargar y devuelve None (la página sigue)."""
    try:
        return funcion(*args)
    except ErrorJava as e:
        st.warning(f"No se pudo cargar {que}: {e.mensaje}")
        return None


def _numero(valor: float, decimales: int = 0) -> str:
    """Como se escribe en español: punto de miles y coma decimal (1.000 · 4,4)."""
    return f"{valor:,.{decimales}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _duracion(segundos: float | None) -> str:
    """62 → "1 min 2 s"; 1000 → "16 min 40 s"; 5 → "5 s"."""
    if segundos is None:
        return "—"
    s = round(segundos)
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min {s % 60} s" if s % 60 else f"{s // 60} min"
    return f"{s // 3600} h {s % 3600 // 60} min"


def _tema(clave: str | None) -> str:
    return TEMAS.get(clave or "", clave or "Sin tema")


def _minutos_por_historia() -> int:
    """PANEL_MINUTOS_POR_HISTORIA (DEC-154): los minutos que tarda Marketing en encontrar y redactar una historia."""
    try:
        minutos = int(os.environ.get("PANEL_MINUTOS_POR_HISTORIA", MINUTOS_POR_DEFECTO))
    except ValueError:
        return MINUTOS_POR_DEFECTO
    return minutos if minutos > 0 else MINUTOS_POR_DEFECTO


def _sumar(sentimiento: dict | None) -> dict:
    """Los 5 sentimientos sumados en todo el período."""
    total = {s: 0 for s in SENTIMIENTOS}
    for p in (sentimiento or {}).get("puntos") or []:
        for s in SENTIMIENTOS:
            total[s] += p["cantidades"].get(s, 0)
    return total


def _clima(cantidades: dict) -> tuple[int | None, int]:
    """El índice de clima (C1, C2): % positivos − % negativos, de −100 a +100, y su n. Sin mensajes, None."""
    n = sum(cantidades.values())
    if n == 0:
        return None, 0
    positivos = cantidades.get("POSITIVO", 0) + cantidades.get("MUY_POSITIVO", 0)
    negativos = cantidades.get("NEGATIVO", 0) + cantidades.get("MUY_NEGATIVO", 0)
    return round((positivos - negativos) * 100 / n), n


def _indice(valor: int | None) -> str:
    return "—" if valor is None else f"{valor:+d}"


def _porcentaje(parte: int, total: int) -> str:
    return f"{round(parte * 100 / total)} %" if total else "—"


def _revision(contenido: dict, tipo: str) -> dict:
    return next((r for r in contenido.get("revision") or [] if r["tipo"] == tipo), {"medianaSeg": None, "n": 0})


def enlace_discord(duda: dict) -> str | None:
    """El enlace al mensaje en Discord, o None si falta un dato. Los tres son números (snowflakes de Discord)."""
    partes = [duda.get("servidorId"), duda.get("canalId"), duda.get("discordId")]
    if not all(isinstance(p, str) and p.isdigit() for p in partes):
        return None
    return "https://discord.com/channels/{}/{}/{}".format(*partes)


# ── Piezas de HTML propias del dashboard (las comunes están en estilo.py, DEC-158) ──

def _franja(titulo: str, piezas: list[tuple[str, str, str]]) -> None:
    columnas = "".join(
        f'<div style="flex: 1 1 260px; display: flex; flex-direction: column; gap: 4px">'
        f'<div style="font-size: 28px; font-weight: 700; line-height: 1.15">{_e(valor)}</div>'
        f'<div style="font-size: 16px">{_e(etiqueta)}</div>'
        f'<div style="font-size: 13px; {SUAVE}">{_e(nota)}</div></div>'
        for valor, etiqueta, nota in piezas)
    _bloque(f'<div style="display: flex; flex-wrap: wrap; gap: 16px 40px">'
            f'<div style="flex: 1 1 100%; font-size: 15px; font-weight: 600; {SUAVE}">{_e(titulo)}</div>'
            f'{columnas}</div>')


# ── Gráficos (Altair, sin cuadrícula ni ejes de más, como el prototipo) ──
# Sin colores de texto ni de ejes: los pone el tema de Streamlit, y cambian solos con él

def _limpio(grafico):
    # Fondo transparente: el gráfico toma el color de su tarjeta en los dos temas
    return (grafico.configure(background="transparent").configure_view(stroke=None)
            .configure_axis(grid=False, domain=False, ticks=False, labelFontSize=14, labelPadding=8, title=None))


def _grafico(grafico) -> None:
    st.altair_chart(grafico, width="stretch")


def _clima_divergente(sentimiento: dict, por_semana: bool):
    """
    C3: barras divergentes. Los negativos a la izquierda del 0, los positivos a la derecha y el neutro partido al
    medio. A la izquierda, la semana y su n; a la derecha, el índice. None si no hay ningún mensaje.
    """
    filas, resumen = [], []
    for p in sentimiento.get("puntos") or []:
        c = {s: p["cantidades"].get(s, 0) for s in SENTIMIENTOS}
        n = sum(c.values())
        if n == 0:
            continue
        fila = _dia(date.fromisoformat(p["inicio"]))
        resumen.append({"Fila": fila, "n": f"n = {n}", "Índice": _indice(_clima(c)[0])})
        x = -(c["MUY_NEGATIVO"] + c["NEGATIVO"] + c["NEUTRO"] / 2)
        for s, nombre in SENTIMIENTOS.items():
            filas.append({"Fila": fila, "Sentimiento": nombre, "x0": x, "x1": x + c[s], "Mensajes": c[s],
                          "Semana" if por_semana else "Día": fila})
            x += c[s]
    if not filas:
        return None
    orden = [r["Fila"] for r in resumen]
    extremo = max(max(abs(f["x0"]), abs(f["x1"])) for f in filas)
    # Lugar a la izquierda para la semana y su n, y a la derecha para el índice
    izquierda, derecha = -extremo * 1.35, extremo * 1.15
    escala = alt.Scale(domain=[izquierda, derecha])
    y = alt.Y("Fila:N", sort=orden, axis=None)
    barras = alt.Chart(pd.DataFrame(filas)).mark_bar(height=22).encode(
        x=alt.X("x0:Q", scale=escala, axis=None),
        x2="x1:Q",
        y=y,
        # Sin "range": los colores salen de chartCategoricalColors del tema activo (config.toml)
        color=alt.Color("Sentimiento:N", scale=alt.Scale(domain=list(SENTIMIENTOS.values())),
                        legend=alt.Legend(orient="top", title=None, symbolType="square", labelFontSize=13,
                                          columns=5)),
        tooltip=["Semana:N" if por_semana else "Día:N", "Sentimiento:N", "Mensajes:Q"],
    )
    textos = alt.Chart(pd.DataFrame(resumen).assign(izq=izquierda, der=derecha)).encode(y=y)
    capas = [
        barras,
        alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#808080", opacity=0.6).encode(
            x=alt.X("x:Q", scale=escala)),
        textos.mark_text(align="left", dy=-7, fontSize=14, fontWeight=600, color=TEXTO_GRAFICO).encode(
            x=alt.X("izq:Q", scale=escala), text="Fila:N"),
        textos.mark_text(align="left", dy=9, fontSize=13, color=TEXTO_GRAFICO).encode(
            x=alt.X("izq:Q", scale=escala), text="n:N"),
        textos.mark_text(align="right", fontSize=14, fontWeight=600, color=TEXTO_GRAFICO).encode(
            x=alt.X("der:Q", scale=escala), text="Índice:N"),
    ]
    # 46 px por fila, más el lugar de la leyenda de arriba
    return _limpio(alt.layer(*capas).properties(height=46 * len(orden) + 40))


def _barras(tabla: pd.DataFrame, x: str, y: str, texto: str, total: float | None = None,
            opacidades: list | None = None, alto_fila: int = 30, grosor: int = 18):
    """Barras horizontales con la etiqueta a la izquierda y el valor en la punta (C6, C9 y el embudo)."""
    # Lugar a la derecha para el texto de la punta: más si es largo ("9 · 82 %")
    largo_texto = max(len(str(v)) for v in tabla[texto])
    tope = (total or max(tabla[x].max(), 1)) * (1.3 if largo_texto <= 6 else 1.5)
    escala = alt.Scale(domain=[0, tope])
    eje_y = alt.Y(f"{y}:N", sort=None, axis=alt.Axis(labelLimit=240))
    capas = []
    if total:  # la pista: lo que falta para llegar al total
        capas.append(alt.Chart(tabla.assign(_total=total)).mark_bar(size=grosor, color=PISTA, cornerRadiusEnd=4)
                     .encode(y=eje_y, x=alt.X("_total:Q", scale=escala, axis=None)))
    barra = alt.Chart(tabla.assign(_opacidad=opacidades or 1)).mark_bar(size=grosor, cornerRadiusEnd=4, color=SERIE)
    capas.append(barra.encode(y=eje_y, x=alt.X(f"{x}:Q", scale=escala, axis=None),
                              opacity=alt.Opacity("_opacidad:Q", scale=None, legend=None),
                              tooltip=[f"{y}:N", f"{x}:Q"]))
    capas.append(alt.Chart(tabla.assign(_total=total or 0)).mark_text(align="left", dx=6, fontSize=14,
                                                                       fontWeight=600, color=TEXTO_GRAFICO)
                 .encode(y=eje_y, x=alt.X("_total:Q" if total else f"{x}:Q", scale=escala), text=f"{texto}:N"))
    return _limpio(alt.layer(*capas).properties(height=alto_fila * len(tabla)))


def _columnas_por_semana(semanas: list[dict]):
    """M8: lo aprobado por semana de aprobación, con el valor arriba."""
    orden = [_dia(date.fromisoformat(s["inicio"])) for s in semanas]
    tabla = pd.DataFrame({"Semana del": orden, "Aprobados": [s["cantidad"] for s in semanas]})
    base = alt.Chart(tabla).encode(
        x=alt.X("Semana del:N", sort=orden, axis=alt.Axis(labelAngle=0, domain=True, labelFontSize=13)),
        y=alt.Y("Aprobados:Q", axis=None, scale=alt.Scale(domain=[0, max(tabla["Aprobados"].max(), 1) * 1.2])),
        tooltip=["Semana del:N", "Aprobados:Q"],
    )
    grafico = (base.mark_bar(size=24, cornerRadiusEnd=4, color=SERIE)
               + base.mark_text(baseline="bottom", dy=-6, fontSize=14, fontWeight=600, color=TEXTO_GRAFICO)
               .encode(text="Aprobados:Q"))
    return (grafico.properties(height=220).configure(background="transparent").configure_view(stroke=None)
            .configure_axis(grid=False, ticks=False, title=None))


# ── Controles comunes (dentro de la pestaña abierta) ──

def _periodo(hoy: date, con_ajustes: bool) -> tuple[date, date, str, int, int]:
    """El período elegido y los ajustes de las alertas. Detiene la página si las fechas están a medio elegir."""
    col_periodo, col_ajustes = st.columns([3, 2], vertical_alignment="center")
    atajo = col_periodo.pills("Período", [*ATAJOS, ELEGIR], default="30 días", required=True, key="dash_atajo")
    dias_desercion, horas_sin_responder = 14, 24
    if con_ajustes:
        with col_ajustes.expander("Ajustes de las alertas"):
            dias_desercion = int(st.number_input("Posible deserción: días sin escribir", min_value=1,
                                                 max_value=365, value=14, step=1, key="dash_dias"))
            horas_sin_responder = int(st.number_input("Duda sin responder después de (horas)", min_value=0,
                                                      max_value=2160, value=24, step=1, key="dash_horas"))
    if atajo == ELEGIR:
        periodo = st.date_input("Fechas", value=(hoy - timedelta(days=29), hoy), max_value=hoy,
                                format="YYYY-MM-DD", key="dash_periodo")
        if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
            st.info("Elige la fecha final del período.")
            st.stop()
        desde, hasta = periodo
        if (hasta - desde).days + 1 > 366:
            st.warning("El período puede tener hasta 366 días.")
            st.stop()
        titulo = f"del {_dia(desde)} al {_dia(hasta)}"
    else:
        dias = ATAJOS.get(atajo, 30)
        hasta, desde = hoy, hoy - timedelta(days=dias - 1)
        titulo = f"en los últimos {dias} días"
    return desde, hasta, titulo, dias_desercion, horas_sin_responder


# ── La franja: lo que hizo InsightEdu en este período (P1 y P4, las dos vistas) ──

def _franja_valor(contenido: dict | None, titulo_periodo: str) -> None:
    if not contenido:
        return
    embudo = contenido["embudo"]
    minutos = _minutos_por_historia()
    historias = embudo["conPostAprobado"]
    post = _revision(contenido, "POST_LINKEDIN")
    revision_min = (post["medianaSeg"] or 0) / 60
    horas = max(minutos - revision_min, 0) * historias / 60
    with st.container(key="dash-franja"):
        # DEC-154: el supuesto va siempre junto al número
        _franja(f"Lo que hizo InsightEdu {titulo_periodo}", [
            (f"≈ {_numero(horas, 1)} h", "ahorradas a Marketing",
             f"Estimado: supone {minutos} min por historia encontrada y redactada a mano, menos la revisión en el "
             f"panel ({_numero(revision_min, 1)} min, mediana de {post['n']} posts) · {historias} historias "
             f"aprobadas"),
            (f"{embudo['publicables']} historias", "encontradas solas en la comunidad",
             f"De {contenido['mensajesDePersonas']} mensajes de personas y {embudo['logros']} logros, "
             f"{embudo['publicables']} eran publicables"),
        ])


# ── Vista Comunidad (el Community Manager) ──

def _vista_comunidad(hoy: date) -> None:
    _nota_vista("Cómo está la comunidad y a quién conviene ayudar hoy.")
    desde, hasta, titulo_periodo, dias_desercion, horas_sin_responder = _periodo(hoy, con_ajustes=True)
    por_semana = (hasta - desde).days >= 14
    largo = (hasta - desde).days + 1

    contenido = _pedir("la franja de valor", cliente.dashboard_contenido, desde, hasta)
    comunidad = _pedir("la comunidad", cliente.dashboard_comunidad, desde, hasta)
    clima = _pedir("el clima de los alumnos", cliente.dashboard_sentimiento, desde, hasta,
                   "semana" if por_semana else "dia", False, "alumnos")
    clima_todos = _pedir("el clima de la comunidad", cliente.dashboard_sentimiento, desde, hasta, "semana", False,
                         "todos")
    clima_antes = _pedir("el clima del período anterior", cliente.dashboard_sentimiento,
                         desde - timedelta(days=largo), desde - timedelta(days=1), "semana", False, "alumnos")
    dudas = _pedir("las dudas sin respuesta", cliente.dashboard_dudas, desde, hasta, horas_sin_responder, False)
    desercion = _pedir("la posible deserción", cliente.dashboard_desercion, dias_desercion)
    frustracion = _pedir("la posible frustración", cliente.dashboard_frustracion, desde, hasta)
    temas = _pedir("los temas", cliente.dashboard_temas, desde, hasta, False, "alumnos")
    alumnos = (comunidad or {}).get("alumnos") or {}
    _barra_lateral(contenido)

    _franja_valor(contenido, titulo_periodo)

    # Indicadores clave
    _seccion("Indicadores clave", "El clima, el bot y quién necesita atención, en el período elegido.")
    tarjetas = st.columns(4)
    with tarjetas[0].container(key="dash-tarjeta-clima"):
        indice, n = _clima(_sumar(clima)) if clima else (None, 0)
        notas = []
        if clima_todos:
            indice_todos, n_todos = _clima(_sumar(clima_todos))
            notas.append(f"Toda la comunidad, con mentores: {_indice(indice_todos)} (n = {n_todos}).")
        if indice is not None and clima_antes is not None:
            antes, n_antes = _clima(_sumar(clima_antes))
            notas.append(f"{indice - antes:+d} frente al período anterior (n = {n_antes})." if n_antes
                         else "Sin datos del período anterior para comparar.")
        _bloque(_tarjeta("Clima de los alumnos", _indice(indice), f"n = {n} mensajes con sentimiento",
                         " ".join(notas) or None))

    with tarjetas[1].container(key="dash-tarjeta-bot"):
        bot = (comunidad or {}).get("bot")
        if bot:
            vistas = bot["respondidas"] + bot["derivadas"]
            ancho = round(bot["respondidas"] * 100 / vistas) if vistas else 0
            barra = (f'<div style="height: 8px; background: {PISTA}; border-radius: 4px; overflow: hidden">'
                     f'<div style="width: {ancho}%; height: 8px; background: {SERIE}; border-radius: 4px"></div></div>')
            _bloque(_tarjeta(
                "Dudas que respondió el bot", _porcentaje(bot["respondidas"], vistas),
                f"{bot['respondidas']} de {vistas} dudas que vio el bot (n = {vistas}) · respondió en "
                f"{_duracion(bot['segundosMediana'])} (mediana)",
                f"{bot['derivadas']} se derivaron a un mentor. Otras {bot['sinPasarPorElBot']} llegaron por lote "
                f"y no pasan por el bot.", extra=barra))
        else:
            _bloque(_tarjeta("Dudas que respondió el bot", "—"))

    with tarjetas[2].container(key="dash-tarjeta-dudas"):
        linea = f"de {alumnos['dudas']} dudas de alumnos del período" if alumnos else None
        _bloque(_tarjeta(f"Dudas sin respuesta (más de {horas_sin_responder} h)",
                         "—" if dudas is None else dudas["total"], linea))

    with tarjetas[3].container(key="dash-tarjeta-apoyo"):
        personas_desercion = (desercion or {}).get("personas") or []
        personas_frustracion = (frustracion or {}).get("personas") or []
        total = alumnos.get("total")
        de_total = f"de {total} · " if total else ""
        _bloque(f'<div style="display: flex; flex-direction: column; gap: 8px">'
                f'<div style="font-size: 15px; {SUAVE}">Alumnos que necesitan apoyo</div>'
                f'<div><span style="font-size: 30px; font-weight: 600; line-height: 1.15">'
                f'{len(personas_desercion)}</span> <span style="font-size: 15px">{_e(de_total)}posible deserción'
                f'</span></div>'
                f'<div><span style="font-size: 22px; font-weight: 600; line-height: 1.15">'
                f'{len(personas_frustracion)}</span> <span style="font-size: 15px">posible frustración</span></div>'
                f'<div style="font-size: 13px; {SUAVE}">Deserción: más de {dias_desercion} días sin escribir, '
                f'contados desde hoy. Si el servidor está quieto, este número sube.</div></div>')

    # Cómo evoluciona la comunidad
    _seccion("Cómo evoluciona la comunidad", "El clima, la actividad y los temas de los alumnos.")
    col_clima, col_activos = st.columns(2)
    with col_clima.container(key="dash-seccion-clima"):
        _titulo(f"Clima de los alumnos por {'semana' if por_semana else 'día'}",
                "Índice de −100 (todo negativo) a +100 (todo positivo), con su n.")
        grafico = _clima_divergente(clima, por_semana) if clima else None
        if grafico is None:
            st.info("No hay mensajes de alumnos con sentimiento en este período.")
        else:
            _grafico(grafico)
            with st.expander("Ver los números en una tabla"):
                st.dataframe(pd.DataFrame([{
                    "Semana del" if por_semana else "Día": p["inicio"],
                    **{nombre: p["cantidades"].get(s, 0) for s, nombre in SENTIMIENTOS.items()},
                    "n": sum(p["cantidades"].values()),
                    "Índice": _indice(_clima(p["cantidades"])[0]),
                } for p in clima["puntos"] if sum(p["cantidades"].values())]), hide_index=True)

    with col_activos.container(key="dash-seccion-activos"):
        t_alumnos = alumnos.get("total")
        _titulo("Alumnos activos",
                f"{alumnos['activos30Dias']} de {t_alumnos} alumnos escribieron en los últimos 30 días, y "
                f"{alumnos['activos7Dias']} en la última semana." if t_alumnos else None)
        if t_alumnos:
            tabla = pd.DataFrame({
                "Ventana": ["Últimos 7 días", "Últimos 30 días"],
                "Alumnos": [alumnos["activos7Dias"], alumnos["activos30Dias"]],
                "Etiqueta": [f"{alumnos['activos7Dias']} de {t_alumnos}", f"{alumnos['activos30Dias']} de {t_alumnos}"],
            })
            _grafico(_barras(tabla, "Alumnos", "Ventana", "Etiqueta", total=t_alumnos, alto_fila=46, grosor=22))
            _nota(f"Activo: escribió al menos un mensaje, contando hasta el {_dia(hasta)}. Solo alumnos.")
        elif comunidad is not None:
            st.info("Todavía no escribió ningún alumno.")

    with st.container(key="dash-seccion-temas"):
        lista = [x for x in (temas or {}).get("temas") or [] if x["actual"]]
        total_temas = sum(x["actual"] for x in lista)
        _titulo("De qué hablan los alumnos",
                f"{_tema(lista[0]['tema'])} es el tema más frecuente: {lista[0]['actual']} de {total_temas} "
                f"mensajes." if lista else None)
        if lista:
            tabla = pd.DataFrame({"Tema": [_tema(x["tema"]) for x in lista], "Mensajes": [x["actual"] for x in lista]})
            _grafico(_barras(tabla, "Mensajes", "Tema", "Mensajes"))
            _nota(f"Mensajes de alumnos clasificados por la IA en el período (n = {total_temas}). "
                  f"\"Otro\" son preguntas que no son del curso.")
        elif temas is not None:
            st.info("No hay temas en este período.")

    # A quién ayudar hoy
    _seccion("A quién ayudar hoy", "Solo alumnos: los mentores y los bots no cuentan.")
    col_esperan, col_escribir, col_falta = st.columns(3)

    with col_esperan.container(key="dash-seccion-esperan"):
        lista = (dudas or {}).get("dudas") or []
        total = (dudas or {}).get("total", len(lista))
        _encabezado_lista(ICONO_RELOJ.format(color=ESPERA), f"Esperan respuesta ({total})")
        if dudas is not None and not lista:
            st.success("No hay dudas sin respuesta en este período.")
        for d in lista[:CASOS_VISIBLES]:
            _caso_duda(d)
        if len(lista) > CASOS_VISIBLES:
            with st.expander(f"Ver las {total}"):
                for d in lista[CASOS_VISIBLES:]:
                    _caso_duda(d)
        _nota(f"Dudas de alumnos con más de {horas_sin_responder} h que el bot no respondió y a las que nadie "
              f"contestó con «Responder» de Discord.")

    with col_escribir.container(key="dash-seccion-escribir"):
        casos = ([(p["nombre"], "posible deserción",
                   f"{p['diasSinEscribir']} días sin escribir · {p['mensajes']} mensajes en total")
                  for p in personas_desercion]
                 + [(p["nombre"], "posible frustración", ", ".join(MOTIVOS.get(m, m) for m in p["motivos"]))
                    for p in personas_frustracion])
        _encabezado_lista(ICONO_ALERTA.format(color=ALERTA), f"A quién escribir ({len(casos)})")
        if desercion is not None and frustracion is not None and not casos:
            st.success("Ningún alumno muestra señales de deserción ni de frustración.")
        for i, caso in enumerate(casos[:CASOS_VISIBLES]):
            _caso_persona(i, *caso)
        if len(casos) > CASOS_VISIBLES:
            with st.expander(f"Ver los {len(casos)}"):
                for i, caso in enumerate(casos[CASOS_VISIBLES:], start=CASOS_VISIBLES):
                    _caso_persona(i, *caso)

    with col_falta.container(key="dash-seccion-falta"):
        derivadas = (comunidad or {}).get("derivadasPorTema") or []
        _encabezado_lista(ICONO_DOCUMENTO.format(color="currentColor"),
                          f"Qué falta en los documentos ({sum(d['cantidad'] for d in derivadas)})")
        if derivadas:
            filas = "".join(
                f'<div style="display: flex; justify-content: space-between; font-size: 15px; '
                f'border-top: 1px solid {BORDE}; padding-top: 8px"><span>{_e(_tema(d["tema"]))}</span>'
                f'<span style="font-variant-numeric: tabular-nums">{_e(d["cantidad"])}</span></div>'
                for d in derivadas)
            _bloque(f'<p style="margin: 0 0 8px; font-size: 14px; {SUAVE}">Dudas que el bot derivó porque los PDF '
                    f'no tenían la respuesta, por tema:</p>'
                    f'<div style="display: flex; flex-direction: column; gap: 8px">{filas}</div>')
        elif comunidad is not None:
            st.success("El bot encontró respaldo en los documentos para todas las dudas que vio.")


def _caso_duda(d: dict) -> None:
    """Una duda: quién, dónde y cuándo; su texto, y el botón a Discord. Nombre y texto con st.text (escapados)."""
    with st.container(key=f"dash-caso-duda-{d['mensajeId']}", gap="small"):
        derivada = " · derivada a un mentor" if d.get("derivada") else ""
        with st.container(key=f"dash-meta-duda-{d['mensajeId']}"):
            st.text(f"{d.get('autorNombre') or '—'} · #{d.get('canal') or '—'} · {_hace(d.get('fecha'))} · "
                    f"{_tema(d.get('tema'))}{derivada}")
        st.text(f"“{_corto(d.get('texto'))}”")
        enlace = enlace_discord(d)
        if enlace:
            # Un botón con borde y su ícono: se distingue del texto en los dos temas
            st.link_button("Abrir en Discord", enlace, icon=":material/open_in_new:", icon_position="right")


def _caso_persona(i: int, nombre: str, motivo: str, detalle: str) -> None:
    with st.container(key=f"dash-caso-persona-{i}", gap="small"):
        with st.container(key=f"dash-nombre-{i}"):
            st.text(f"{nombre} · {motivo}")
        _bloque(f'<div style="font-size: 14px; {SUAVE}">{_e(detalle)}</div>')


# ── Vista Contenido (Marketing) ──

def _vista_contenido(hoy: date) -> None:
    _nota_vista("Cuántas historias encontró el sistema y qué hizo Marketing con ellas.")
    desde, hasta, titulo_periodo, _, _ = _periodo(hoy, con_ajustes=False)
    contenido = _pedir("la franja de valor", cliente.dashboard_contenido, desde, hasta)
    aprobados = _pedir("los aprobados", cliente.listar_borradores, "APROBADO", None, 20)
    _barra_lateral(contenido)

    _franja_valor(contenido, titulo_periodo)

    _seccion("Indicadores clave", "Lo pendiente, la revisión y cuánto tarda un logro en ser contenido.")
    tarjetas = st.columns(4)
    with tarjetas[0].container(key="dash-tarjeta-revisar"):
        por_revisar = (contenido or {}).get("porRevisar")
        if por_revisar and por_revisar["total"]:
            partes = [f"{n} {TIPOS_PLURAL[tipo][0 if n == 1 else 1]}" for tipo, n in por_revisar["porTipo"].items()
                      if n]
            espera = (f'<div style="font-size: 14px; display: flex; align-items: center; gap: 6px">'
                      f'{ICONO_RELOJ.format(color=ESPERA)}El más antiguo espera '
                      f'{_e(_hace(por_revisar["masAntiguo"]))}</div>')
            lista = ", ".join(partes[:-1]) + " y " + partes[-1] if len(partes) > 1 else partes[0]
            _bloque(_tarjeta("Por revisar", por_revisar["total"], lista) + espera)
        else:
            _bloque(_tarjeta("Por revisar", "—" if not por_revisar else 0,
                             "No hay nada pendiente." if por_revisar else None))
        st.page_link("paginas/borradores.py", label="Ir a Borradores", icon=":material/arrow_forward:")

    with tarjetas[1].container(key="dash-tarjeta-revision"):
        if contenido:
            post = _revision(contenido, "POST_LINKEDIN")
            caso, faq = _revision(contenido, "CASO_EXITO"), _revision(contenido, "FAQ")
            _bloque(_tarjeta("Tiempo de revisión (mediana)", _duracion(post["medianaSeg"]),
                             f"por post de LinkedIn · n = {post['n']}",
                             f"Caso de éxito: {_duracion(caso['medianaSeg'])} (n = {caso['n']}) · FAQ: "
                             f"{_duracion(faq['medianaSeg'])} (n = {faq['n']})"))
        else:
            _bloque(_tarjeta("Tiempo de revisión (mediana)", "—"))

    with tarjetas[2].container(key="dash-tarjeta-aprobacion"):
        if contenido:
            a = contenido["aprobacion"]
            revisados = a["aprobados"] + a["rechazados"]
            _bloque(_tarjeta("Tasa de aprobación", _porcentaje(a["aprobados"], revisados),
                             f"{a['aprobados']} de {revisados} borradores revisados (n = {revisados})",
                             "Aprobados sobre lo revisado en el período."))
        else:
            _bloque(_tarjeta("Tasa de aprobación", "—"))

    with tarjetas[3].container(key="dash-tarjeta-logro"):
        if contenido:
            logro = contenido["logroAAprobacion"]
            horas = logro["medianaHoras"]
            if horas is None:
                valor = "—"
            else:
                valor = f"{_numero(horas)} h" if horas < 48 else f"{_numero(horas / 24)} días"
            _bloque(_tarjeta("Del logro al contenido aprobado", valor, f"mediana · n = {logro['n']} posts",
                             "Desde que el alumno contó su logro hasta que Marketing aprobó el post."))
        else:
            _bloque(_tarjeta("Del logro al contenido aprobado", "—"))

    if contenido:
        _seccion("Del logro a la publicación", "Qué hizo la IA con los logros y cuánto aprobó Marketing.")
        col_embudo, col_semanas = st.columns(2)
        with col_embudo.container(key="dash-seccion-embudo"):
            e = contenido["embudo"]
            logros, publicables, aprobados_post = e["logros"], e["publicables"], e["conPostAprobado"]
            _titulo("De logro a contenido aprobado",
                    f"La IA vio publicables {publicables} de {logros} logros, y Marketing aprobó {aprobados_post}."
                    if logros else None)
            if logros:
                tabla = pd.DataFrame({
                    "Etapa": ["Logros que escribieron los alumnos", "Publicables según la IA",
                              "Aprobados por Marketing"],
                    "Cantidad": [logros, publicables, aprobados_post],
                    "Etiqueta": [str(logros), f"{publicables} · {_porcentaje(publicables, logros)}",
                                 f"{aprobados_post} · {_porcentaje(aprobados_post, publicables)}"],
                })
                # Un solo azul, cada paso más intenso: se lee igual en los dos temas
                _grafico(_barras(tabla, "Cantidad", "Etapa", "Etiqueta", opacidades=[0.45, 0.72, 1.0],
                                 alto_fila=46, grosor=24))
                sin_decidir = logros - publicables - e["noPublicables"]
                _nota(f"Publicables: % de los logros. Aprobados: % de los publicables. "
                      f"No publicables ({e['noPublicables']}): antes de redactar, la IA decide si un logro alcanza "
                      f"para una historia y deja escrito el motivo (DEC-53)."
                      + (f" {sin_decidir} todavía sin decidir o con error." if sin_decidir else ""))
            else:
                st.info("No hay logros en este período.")

        with col_semanas.container(key="dash-seccion-semanas"):
            semanas = contenido.get("aprobadosPorSemana") or []
            mejor = max(semanas, key=lambda s: s["cantidad"], default=None)
            _titulo("Contenido aprobado por semana",
                    f"{mejor['cantidad']} piezas la semana del {_dia(date.fromisoformat(mejor['inicio']))}: la "
                    f"semana con más aprobados." if mejor and mejor["cantidad"] else None)
            if mejor and mejor["cantidad"]:
                _grafico(_columnas_por_semana(semanas))
                _nota("Posts de LinkedIn, casos de éxito y FAQ, por semana de aprobación (desde el lunes).")
            else:
                st.info("No se aprobó nada en este período.")

    _seccion("Listos para publicar", "Lo aprobado y dónde se usa. Elige una fila para ver su texto y copiarlo.")
    if aprobados is not None:
        if not aprobados:
            st.info("Todavía no hay borradores aprobados.")
            return
        eleccion = st.dataframe(pd.DataFrame({
            "Qué": [ui.TIPOS.get(b["tipo"], b["tipo"]) + (f" {b['semana']}" if b.get("semana") else "")
                    for b in aprobados],
            "De quién": [b.get("autorNombre") or "Varias personas" for b in aprobados],
            "Dónde se publica": [DESTINOS.get(b["tipo"], "—") for b in aprobados],
            # T13 (M12): si el post se publicó en LinkedIn; "—" si no es un post
            "En LinkedIn": [en_linkedin_corto(b) for b in aprobados],
            "Aprobado": [f"{ui.fecha(b.get('revisadoEn'))} · {b.get('revisadoPor') or '—'}" for b in aprobados],
        }), hide_index=True, on_select="rerun", selection_mode="single-row", key="dash_listos")
        # Sin fila elegida, el más reciente
        filas = list(getattr(getattr(eleccion, "selection", None), "rows", None) or []) or [0]
        elegido = aprobados[filas[0]]
        detalle = _pedir("el texto aprobado", cliente.detalle, elegido["id"])
        if detalle:
            ui.mostrar_texto(detalle.get("textoFinal") or detalle.get("textoIa"))
            _nota("Para copiarlo, usa el ícono de copiar en la esquina del cuadro. Todo lo aprobado queda guardado "
                  "en OCI (aprobados/).")


def _nota_vista(texto: str) -> None:
    _bloque(f'<p style="margin: 0; font-size: 17px; {SUAVE}">{_e(texto)}</p>')


def _barra_lateral(contenido: dict | None) -> None:
    """P5, en la barra lateral, debajo del usuario."""
    if not contenido:
        return
    with st.sidebar.container(key="dash-oci"):
        _bloque(f'<div style="font-weight: 600; font-size: 15px">Guardados en OCI</div>'
                f'<div style="font-size: 14px; {SUAVE}">{_e(contenido["activosOci"])} activos (borradores generados '
                f'y aprobados)</div>')


# ── La página ──

cliente = ui.exigir_cliente()
hoy_bogota = datetime.now(ui.ZONA).date()  # el "hoy" de Bogotá, como Java (no el del contenedor, en UTC)

# Los estilos fijos (estilo.ESTILOS) los pone app.py para todas las páginas
_bloque('<h1 style="margin: 0; font-size: 32px; font-weight: 700">Dashboard</h1>')
# Pestañas que solo ejecutan la abierta: cada vista pide a Java solo lo suyo
pestana_comunidad, pestana_contenido = st.tabs(["Comunidad", "Contenido"], key="dash_vista", on_change="rerun")
if pestana_contenido.open:
    with pestana_contenido:
        _vista_contenido(hoy_bogota)
else:
    with pestana_comunidad:
        _vista_comunidad(hoy_bogota)
