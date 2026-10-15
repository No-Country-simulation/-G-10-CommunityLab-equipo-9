"""
Página "Dashboard" (T08 y T12, N5, OE5): una vista por rol (DEC-153), con el diseño del prototipo aprobado.

- Comunidad (el Community Manager): el clima de los alumnos, si el bot ayuda, quién espera respuesta,
  a quién escribir y qué falta en los documentos.
- Contenido (Marketing): cuánto hay por revisar, cuánto tarda la revisión, si la IA propone cosas útiles
  y qué se aprobó.

Las dos empiezan con la franja "Lo que hizo InsightEdu en este período". Orden (DEC-153): franja → 4 tarjetas →
gráficos → listas. Reglas (DEC-155): la n junto a cada porcentaje o índice, la mediana para los tiempos y los
alumnos separados de los mentores.

Java calcula y esta página solo dibuja (DEC-123). Cada dato se pide aparte: si uno falla, los demás se ven.

Seguridad de lo que se muestra (DEC-158): la franja, las tarjetas y los títulos son bloques HTML (st.html) que
llevan SOLO números y textos de esta página, siempre pasados por html.escape. Los nombres y los textos de los
alumnos NUNCA van en HTML ni en markdown: van con st.text, st.dataframe o ui.mostrar_texto, que los escapan.
Los gráficos son de Altair (viene con Streamlit) y, como los colores de las tarjetas, siguen el tema (DEC-156).
"""
from __future__ import annotations

import html
import os
from datetime import date, datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

import ui
from cliente_java import ErrorJava

# De muy negativo a muy positivo: el orden en que se dibujan las barras divergentes
SENTIMIENTOS = {
    "MUY_NEGATIVO": "Muy negativo",
    "NEGATIVO": "Negativo",
    "NEUTRO": "Neutro",
    "POSITIVO": "Positivo",
    "MUY_POSITIVO": "Muy positivo",
}

# Los colores del prototipo para cada tema. Las paletas de los gráficos están validadas para el daltonismo
# en los dos fondos (T12 §3.10)
TOKENS = {
    "claro": {
        "fondo": "#ffffff", "texto": "#262730", "suave": "#55565f", "borde": "#e1e4ea", "tarjeta": "#ffffff",
        "franja": "#f4f6f9", "enlace": "#1f4fa3", "pista": "#cde2fb", "eje": "#c3c2b7", "espera": "#c98500",
        "alerta": "#d03b3b",
        "sentimiento": ["#9b2626", "#e8726a", "#dcdad3", "#6da7ec", "#184f95"],
        "serie": "#2a78d6",
        "embudo": ["#86b6ef", "#3987e5", "#1c5cab"],
    },
    "oscuro": {
        "fondo": "#0e1117", "texto": "#fafafa", "suave": "#a7abb8", "borde": "#31343d", "tarjeta": "#12151c",
        "franja": "#181c25", "enlace": "#8ab4f8", "pista": "#1c2b44", "eje": "#4a4d55", "espera": "#e0a030",
        "alerta": "#f07070",
        "sentimiento": ["#f4877d", "#a5453e", "#3b3e46", "#3b6db3", "#8cc0fb"],
        "serie": "#3987e5",
        "embudo": ["#1c5cab", "#3987e5", "#86b6ef"],
    },
}

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

# Dónde se usa cada tipo una vez aprobado (M11)
DESTINOS = {
    "POST_LINKEDIN": "LinkedIn de CommunityLab",
    "CASO_EXITO": "Web y presentaciones a empresas",
    "FAQ": "Canal #anuncios y la web",
}
TIPOS_PLURAL = {"POST_LINKEDIN": ("post", "posts"), "CASO_EXITO": ("caso de éxito", "casos de éxito"),
                "FAQ": ("FAQ", "FAQ")}

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ATAJOS = {"7 días": 7, "30 días": 30, "90 días": 90}
ELEGIR = "Elegir fechas"
MINUTOS_POR_DEFECTO = 30
CASOS_VISIBLES = 3  # en las tarjetas de "A quién ayudar hoy"; el resto, en "Ver todas"

# Íconos de trazo (fijos), como en el prototipo
ICONO_RELOJ = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.2" '
               'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9">'
               '</circle><path d="M12 7v5l3 2"></path></svg>')
ICONO_ALERTA = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.2" '
                'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9.5 17h-19z">'
                '</path><path d="M12 10v4"></path><path d="M12 17.5v.5"></path></svg>')
ICONO_DOCUMENTO = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.2" '
                   'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h9l4 4v14H6z">'
                   '</path><path d="M14 3v5h5"></path><path d="M9 13h6"></path><path d="M9 17h4"></path></svg>')


# ── Ayudas ──

def _pedir(que: str, funcion, *args):
    """Llama a Java; si falla, avisa qué no se pudo cargar y devuelve None (la página sigue)."""
    try:
        return funcion(*args)
    except ErrorJava as e:
        st.warning(f"No se pudo cargar {que}: {e.mensaje}")
        return None


def _e(valor) -> str:
    """Todo lo que entra en un bloque HTML pasa por aquí (DEC-158)."""
    return html.escape(str(valor))


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


def _dia(d: date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


def _hace(iso: str | None) -> str:
    """Cuánto pasó desde una fecha de Java, en días."""
    if not iso:
        return "—"
    dias = (datetime.now(ui.ZONA) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    return "hoy" if dias < 1 else ("hace 1 día" if dias == 1 else f"hace {dias} días")


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


def _corto(texto: str | None, largo: int = 240) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"


def enlace_discord(duda: dict) -> str | None:
    """El enlace al mensaje en Discord, o None si falta un dato. Los tres son números (snowflakes de Discord)."""
    partes = [duda.get("servidorId"), duda.get("canalId"), duda.get("discordId")]
    if not all(isinstance(p, str) and p.isdigit() for p in partes):
        return None
    return "https://discord.com/channels/{}/{}/{}".format(*partes)


# ── Piezas de HTML (solo números y textos de esta página, DEC-158) ──

def _estilos(t: dict) -> None:
    """Los estilos fijos de las tarjetas y las secciones, con los colores del tema. Nunca llevan datos."""
    st.html(f"""<style>
    [class*="st-key-dash-tarjeta"], [class*="st-key-dash-seccion"] {{
        border: 1px solid {t['borde']}; border-radius: 10px; padding: 18px 20px; background: {t['tarjeta']};
    }}
    [class*="st-key-dash-franja"] {{ background: {t['franja']}; border-radius: 12px; padding: 18px 20px; }}
    [class*="st-key-dash-caso"] {{ border-top: 1px solid {t['borde']}; padding-top: 10px; }}
    [class*="st-key-dash-caso"] [data-testid="stText"] {{ font-size: 15px; }}
    [class*="st-key-dash-meta"] [data-testid="stText"] {{ color: {t['suave']}; font-size: 14px; }}
    [class*="st-key-dash-nombre"] [data-testid="stText"] {{ font-weight: 600; }}
    [class*="st-key-dash-oci"] {{
        border: 1px solid {t['borde']}; border-radius: 8px; padding: 12px 14px; background: {t['tarjeta']};
    }}
    </style>""")


def _bloque(t: dict, cuerpo: str) -> None:
    st.html(f'<div style="font-family: inherit; color: {t["texto"]}">{cuerpo}</div>')


def _titulo(t: dict, titulo: str, subtitulo: str | None = None, tamano: int = 20) -> None:
    sub = f'<p style="margin: 2px 0 0; font-size: 15px; color: {t["suave"]}">{_e(subtitulo)}</p>' if subtitulo else ""
    _bloque(t, f'<h2 style="margin: 0; font-size: {tamano}px; font-weight: 600; color: {t["texto"]}">'
               f'{_e(titulo)}</h2>{sub}')


def _nota(t: dict, texto: str) -> None:
    _bloque(t, f'<div style="font-size: 13px; color: {t["suave"]}">{_e(texto)}</div>')


def _tarjeta(t: dict, etiqueta: str, valor: str, linea: str | None = None, nota: str | None = None,
             extra: str = "") -> str:
    """Una tarjeta del prototipo: etiqueta, número grande, una línea y una nota. extra: HTML ya escapado."""
    partes = [f'<div style="font-size: 15px; color: {t["suave"]}">{_e(etiqueta)}</div>',
              f'<div style="font-size: 38px; font-weight: 600; line-height: 1.1">{_e(valor)}</div>', extra]
    if linea:
        partes.append(f'<div style="font-size: 14px">{_e(linea)}</div>')
    if nota:
        partes.append(f'<div style="font-size: 13px; color: {t["suave"]}">{_e(nota)}</div>')
    return '<div style="display: flex; flex-direction: column; gap: 6px">' + "".join(partes) + "</div>"


def _franja(t: dict, titulo: str, piezas: list[tuple[str, str, str]]) -> None:
    columnas = "".join(
        f'<div style="flex: 1 1 260px; display: flex; flex-direction: column; gap: 4px">'
        f'<div style="font-size: 34px; font-weight: 700; line-height: 1.1">{_e(valor)}</div>'
        f'<div style="font-size: 16px">{_e(etiqueta)}</div>'
        f'<div style="font-size: 13px; color: {t["suave"]}">{_e(nota)}</div></div>'
        for valor, etiqueta, nota in piezas)
    _bloque(t, f'<div style="display: flex; flex-wrap: wrap; gap: 18px 40px">'
               f'<div style="flex: 1 1 100%; font-size: 15px; font-weight: 600; color: {t["suave"]}">{_e(titulo)}</div>'
               f'{columnas}</div>')


def _encabezado_lista(t: dict, icono: str, titulo: str) -> None:
    _bloque(t, f'<div style="display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 17px">'
               f'{icono}{_e(titulo)}</div>')


# ── Gráficos (Altair, sin cuadrícula ni ejes de más, como el prototipo) ──

def _limpio(grafico, t: dict):
    # Fondo transparente: el gráfico toma el color de su tarjeta en los dos temas
    return (grafico.configure(background="transparent").configure_view(stroke=None)
            .configure_axis(grid=False, domain=False, ticks=False, labelFontSize=14, labelColor=t["texto"],
                            labelPadding=8, title=None))


def _grafico(grafico) -> None:
    st.altair_chart(grafico, width="stretch")


def _leyenda(t: dict) -> None:
    chips = "".join(
        f'<span style="display: inline-flex; align-items: center; gap: 6px"><span style="width: 12px; height: 12px; '
        f'border-radius: 3px; background: {color}"></span>{_e(nombre)}</span>'
        for nombre, color in zip(SENTIMIENTOS.values(), t["sentimiento"]))
    _bloque(t, f'<div style="display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 14px">{chips}</div>')


def _clima_divergente(sentimiento: dict, t: dict, por_semana: bool):
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
        inicio = date.fromisoformat(p["inicio"])
        fila = _dia(inicio)
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
    barras = alt.Chart(pd.DataFrame(filas)).mark_bar(height=22, stroke=t["fondo"], strokeWidth=2).encode(
        x=alt.X("x0:Q", scale=escala, axis=None),
        x2="x1:Q",
        y=y,
        color=alt.Color("Sentimiento:N", scale=alt.Scale(domain=list(SENTIMIENTOS.values()),
                                                         range=t["sentimiento"]), legend=None),
        tooltip=["Semana:N" if por_semana else "Día:N", "Sentimiento:N", "Mensajes:Q"],
    )
    textos = alt.Chart(pd.DataFrame(resumen).assign(izq=izquierda, der=derecha)).encode(y=y)
    capas = [
        barras,
        alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=t["eje"]).encode(x=alt.X("x:Q", scale=escala)),
        textos.mark_text(align="left", dy=-7, fontSize=14, color=t["texto"]).encode(
            x=alt.X("izq:Q", scale=escala), text="Fila:N"),
        textos.mark_text(align="left", dy=9, fontSize=13, color=t["suave"]).encode(
            x=alt.X("izq:Q", scale=escala), text="n:N"),
        textos.mark_text(align="right", fontSize=14, fontWeight=600, color=t["texto"]).encode(
            x=alt.X("der:Q", scale=escala), text="Índice:N"),
    ]
    return _limpio(alt.layer(*capas).properties(height=46 * len(orden)), t)


def _barras(t: dict, tabla: pd.DataFrame, x: str, y: str, texto: str, total: float | None = None,
            colores: list | None = None, alto_fila: int = 30, grosor: int = 18):
    """Barras horizontales con la etiqueta a la izquierda y el valor en la punta (C6, C9 y el embudo)."""
    # Lugar a la derecha para el texto de la punta: más si es largo ("9 · 82 %")
    largo_texto = max(len(str(v)) for v in tabla[texto])
    tope = (total or max(tabla[x].max(), 1)) * (1.3 if largo_texto <= 6 else 1.5)
    base = alt.Chart(tabla).encode(
        y=alt.Y(f"{y}:N", sort=None, axis=alt.Axis(labelLimit=240)),
        x=alt.X(f"{x}:Q", scale=alt.Scale(domain=[0, tope]), axis=None),
        tooltip=[f"{y}:N", f"{x}:Q"],
    )
    capas = []
    if total:  # la pista: lo que falta para llegar al total
        capas.append(alt.Chart(tabla.assign(_total=total)).mark_bar(size=grosor, color=t["pista"],
                                                                   cornerRadiusEnd=4).encode(
            y=alt.Y(f"{y}:N", sort=None), x=alt.X("_total:Q", scale=alt.Scale(domain=[0, tope]))))
    if colores:
        capas.append(base.mark_bar(size=grosor, cornerRadiusEnd=4).encode(
            color=alt.Color(f"{y}:N", scale=alt.Scale(domain=tabla[y].tolist(), range=colores), legend=None)))
    else:
        capas.append(base.mark_bar(size=grosor, cornerRadiusEnd=4, color=t["serie"]))
    punta = alt.X("_total:Q") if total else alt.X(f"{x}:Q")
    capas.append(alt.Chart(tabla.assign(_total=total or 0)).mark_text(
        align="left", dx=6, fontSize=14, fontWeight=600, color=t["texto"]).encode(
        y=alt.Y(f"{y}:N", sort=None), x=punta, text=f"{texto}:N"))
    return _limpio(alt.layer(*capas).properties(height=alto_fila * len(tabla)), t)


def _columnas_por_semana(t: dict, semanas: list[dict]):
    """M8: lo aprobado por semana de aprobación, con el valor arriba."""
    orden = [_dia(date.fromisoformat(s["inicio"])) for s in semanas]
    tabla = pd.DataFrame({"Semana del": orden, "Aprobados": [s["cantidad"] for s in semanas]})
    base = alt.Chart(tabla).encode(
        x=alt.X("Semana del:N", sort=orden, axis=alt.Axis(labelAngle=0, domain=True, domainColor=t["eje"],
                                                          labelColor=t["suave"], labelFontSize=13)),
        y=alt.Y("Aprobados:Q", axis=None, scale=alt.Scale(domain=[0, max(tabla["Aprobados"].max(), 1) * 1.2])),
        tooltip=["Semana del:N", "Aprobados:Q"],
    )
    grafico = (base.mark_bar(size=24, cornerRadiusEnd=4, color=t["serie"])
               + base.mark_text(baseline="bottom", dy=-6, fontSize=14, fontWeight=600, color=t["texto"])
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

def _franja_valor(t: dict, contenido: dict | None, titulo_periodo: str) -> None:
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
        _franja(t, f"Lo que hizo InsightEdu {titulo_periodo}", [
            (f"≈ {_numero(horas, 1)} h", "ahorradas a Marketing",
             f"Estimado: supone {minutos} min por historia encontrada y redactada a mano, menos la revisión en el "
             f"panel ({_numero(revision_min, 1)} min, mediana de {post['n']} posts) · {historias} historias "
             f"aprobadas"),
            (f"{embudo['publicables']} historias", "encontradas solas en la comunidad",
             f"De {contenido['mensajesDePersonas']} mensajes de personas y {embudo['logros']} logros, "
             f"{embudo['publicables']} eran publicables"),
        ])


# ── Vista Comunidad (el Community Manager) ──

def _vista_comunidad(t: dict, hoy: date) -> None:
    _nota_vista(t, "Cómo está la comunidad y a quién conviene ayudar hoy.")
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
    _barra_lateral(t, contenido)

    _franja_valor(t, contenido, titulo_periodo)

    # Tarjetas
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
        _bloque(t, _tarjeta(t, "Clima de los alumnos", _indice(indice), f"n = {n} mensajes con sentimiento",
                            " ".join(notas) or None))

    with tarjetas[1].container(key="dash-tarjeta-bot"):
        bot = (comunidad or {}).get("bot")
        if bot:
            vistas = bot["respondidas"] + bot["derivadas"]
            ancho = round(bot["respondidas"] * 100 / vistas) if vistas else 0
            barra = (f'<div style="height: 8px; background: {t["pista"]}; border-radius: 4px; overflow: hidden">'
                     f'<div style="width: {ancho}%; height: 8px; background: {t["serie"]}; border-radius: 4px">'
                     f'</div></div>')
            _bloque(t, _tarjeta(
                t, "Dudas que respondió el bot", _porcentaje(bot["respondidas"], vistas),
                f"{bot['respondidas']} de {vistas} dudas que vio el bot (n = {vistas}) · respondió en "
                f"{_duracion(bot['segundosMediana'])} (mediana)",
                f"{bot['derivadas']} se derivaron a un mentor. Otras {bot['sinPasarPorElBot']} llegaron por lote "
                f"y no pasan por el bot.", extra=barra))
        else:
            _bloque(t, _tarjeta(t, "Dudas que respondió el bot", "—"))

    with tarjetas[2].container(key="dash-tarjeta-dudas"):
        linea = f"de {alumnos['dudas']} dudas de alumnos del período" if alumnos else None
        _bloque(t, _tarjeta(t, f"Dudas sin respuesta (más de {horas_sin_responder} h)",
                            "—" if dudas is None else dudas["total"], linea))

    with tarjetas[3].container(key="dash-tarjeta-apoyo"):
        personas_desercion = (desercion or {}).get("personas") or []
        personas_frustracion = (frustracion or {}).get("personas") or []
        total = alumnos.get("total")
        de_total = f"de {total} · " if total else ""
        _bloque(t, f'<div style="display: flex; flex-direction: column; gap: 8px">'
                   f'<div style="font-size: 15px; color: {t["suave"]}">Alumnos que necesitan apoyo</div>'
                   f'<div><span style="font-size: 38px; font-weight: 600; line-height: 1.1">'
                   f'{len(personas_desercion)}</span> <span style="font-size: 15px">{_e(de_total)}posible deserción'
                   f'</span></div>'
                   f'<div><span style="font-size: 26px; font-weight: 600; line-height: 1.1">'
                   f'{len(personas_frustracion)}</span> <span style="font-size: 15px">posible frustración</span></div>'
                   f'<div style="font-size: 13px; color: {t["suave"]}">Deserción: más de {dias_desercion} días sin '
                   f'escribir, contados desde hoy. Si el servidor está quieto, este número sube.</div></div>')

    # Gráficos
    col_clima, col_activos = st.columns(2)
    with col_clima.container(key="dash-seccion-clima"):
        _titulo(t, f"Clima de los alumnos por {'semana' if por_semana else 'día'}",
                "Índice de −100 (todo negativo) a +100 (todo positivo), con su n. Solo alumnos.")
        grafico = _clima_divergente(clima, t, por_semana) if clima else None
        if grafico is None:
            st.info("No hay mensajes de alumnos con sentimiento en este período.")
        else:
            _leyenda(t)
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
        _titulo(t, "Alumnos activos",
                f"{alumnos['activos30Dias']} de {t_alumnos} alumnos escribieron en los últimos 30 días, y "
                f"{alumnos['activos7Dias']} en la última semana." if t_alumnos else None)
        if t_alumnos:
            tabla = pd.DataFrame({
                "Ventana": ["Últimos 7 días", "Últimos 30 días"],
                "Alumnos": [alumnos["activos7Dias"], alumnos["activos30Dias"]],
                "Etiqueta": [f"{alumnos['activos7Dias']} de {t_alumnos}", f"{alumnos['activos30Dias']} de {t_alumnos}"],
            })
            _grafico(_barras(t, tabla, "Alumnos", "Ventana", "Etiqueta", total=t_alumnos, alto_fila=46, grosor=22))
            _nota(t, f"Activo: escribió al menos un mensaje, contando hasta el {_dia(hasta)}. Solo alumnos.")
        elif comunidad is not None:
            st.info("Todavía no escribió ningún alumno.")

    with st.container(key="dash-seccion-temas"):
        lista = [x for x in (temas or {}).get("temas") or [] if x["actual"]]
        total_temas = sum(x["actual"] for x in lista)
        _titulo(t, "De qué hablan los alumnos",
                f"{_tema(lista[0]['tema'])} es el tema más frecuente: {lista[0]['actual']} de {total_temas} "
                f"mensajes." if lista else None)
        if lista:
            tabla = pd.DataFrame({"Tema": [_tema(x["tema"]) for x in lista], "Mensajes": [x["actual"] for x in lista]})
            _grafico(_barras(t, tabla, "Mensajes", "Tema", "Mensajes"))
            _nota(t, f"Mensajes de alumnos clasificados por la IA en el período (n = {total_temas}). "
                     f"\"Otro\" son preguntas que no son del curso.")
        elif temas is not None:
            st.info("No hay temas en este período.")

    # A quién ayudar hoy
    _titulo(t, "A quién ayudar hoy", "Solo alumnos: los mentores y los bots no cuentan.", tamano=22)
    col_esperan, col_escribir, col_falta = st.columns(3)

    with col_esperan.container(key="dash-seccion-esperan"):
        lista = (dudas or {}).get("dudas") or []
        total = (dudas or {}).get("total", len(lista))
        _encabezado_lista(t, ICONO_RELOJ.format(color=t["espera"]), f"Esperan respuesta ({total})")
        if dudas is not None and not lista:
            st.success("No hay dudas sin respuesta en este período.")
        for d in lista[:CASOS_VISIBLES]:
            _caso_duda(d)
        if len(lista) > CASOS_VISIBLES:
            with st.expander(f"Ver las {total}"):
                for d in lista[CASOS_VISIBLES:]:
                    _caso_duda(d)
        _nota(t, f"Dudas de alumnos con más de {horas_sin_responder} h que el bot no respondió y a las que nadie "
                 f"contestó con «Responder» de Discord.")

    with col_escribir.container(key="dash-seccion-escribir"):
        casos = ([(p["nombre"], "posible deserción",
                   f"{p['diasSinEscribir']} días sin escribir · {p['mensajes']} mensajes en total")
                  for p in personas_desercion]
                 + [(p["nombre"], "posible frustración", ", ".join(MOTIVOS.get(m, m) for m in p["motivos"]))
                    for p in personas_frustracion])
        _encabezado_lista(t, ICONO_ALERTA.format(color=t["alerta"]), f"A quién escribir ({len(casos)})")
        if desercion is not None and frustracion is not None and not casos:
            st.success("Ningún alumno muestra señales de deserción ni de frustración.")
        for i, caso in enumerate(casos[:CASOS_VISIBLES]):
            _caso_persona(t, i, *caso)
        if len(casos) > CASOS_VISIBLES:
            with st.expander(f"Ver los {len(casos)}"):
                for i, caso in enumerate(casos[CASOS_VISIBLES:], start=CASOS_VISIBLES):
                    _caso_persona(t, i, *caso)

    with col_falta.container(key="dash-seccion-falta"):
        derivadas = (comunidad or {}).get("derivadasPorTema") or []
        _encabezado_lista(t, ICONO_DOCUMENTO.format(color=t["suave"]),
                          f"Qué falta en los documentos ({sum(d['cantidad'] for d in derivadas)})")
        if derivadas:
            filas = "".join(
                f'<div style="display: flex; justify-content: space-between; font-size: 15px; border-top: 1px solid '
                f'{t["borde"]}; padding-top: 8px"><span>{_e(_tema(d["tema"]))}</span>'
                f'<span style="font-variant-numeric: tabular-nums">{_e(d["cantidad"])}</span></div>'
                for d in derivadas)
            _bloque(t, f'<p style="margin: 0 0 8px; font-size: 14px; color: {t["suave"]}">Dudas que el bot derivó '
                       f'porque los PDF no tenían la respuesta, por tema:</p>'
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
            st.link_button("Abrir en Discord", enlace, type="tertiary")


def _caso_persona(t: dict, i: int, nombre: str, motivo: str, detalle: str) -> None:
    with st.container(key=f"dash-caso-persona-{i}", gap="small"):
        with st.container(key=f"dash-nombre-{i}"):
            st.text(f"{nombre} · {motivo}")
        _bloque(t, f'<div style="font-size: 14px; color: {t["suave"]}">{_e(detalle)}</div>')


# ── Vista Contenido (Marketing) ──

def _vista_contenido(t: dict, hoy: date) -> None:
    _nota_vista(t, "Cuántas historias encontró el sistema y qué hizo Marketing con ellas.")
    desde, hasta, titulo_periodo, _, _ = _periodo(hoy, con_ajustes=False)
    contenido = _pedir("la franja de valor", cliente.dashboard_contenido, desde, hasta)
    aprobados = _pedir("los aprobados", cliente.listar_borradores, "APROBADO", None, 20)
    _barra_lateral(t, contenido)

    _franja_valor(t, contenido, titulo_periodo)

    tarjetas = st.columns(4)
    with tarjetas[0].container(key="dash-tarjeta-revisar"):
        por_revisar = (contenido or {}).get("porRevisar")
        if por_revisar and por_revisar["total"]:
            partes = [f"{n} {TIPOS_PLURAL[tipo][0 if n == 1 else 1]}" for tipo, n in por_revisar["porTipo"].items()
                      if n]
            espera = (f'<div style="font-size: 14px; display: flex; align-items: center; gap: 6px">'
                      f'{ICONO_RELOJ.format(color=t["espera"])}El más antiguo espera '
                      f'{_e(_hace(por_revisar["masAntiguo"]))}</div>')
            lista = ", ".join(partes[:-1]) + " y " + partes[-1] if len(partes) > 1 else partes[0]
            _bloque(t, _tarjeta(t, "Por revisar", por_revisar["total"], lista) + espera)
        else:
            _bloque(t, _tarjeta(t, "Por revisar", "—" if not por_revisar else 0,
                                "No hay nada pendiente." if por_revisar else None))
        st.page_link("paginas/borradores.py", label="Ir a Borradores")

    with tarjetas[1].container(key="dash-tarjeta-revision"):
        if contenido:
            post = _revision(contenido, "POST_LINKEDIN")
            caso, faq = _revision(contenido, "CASO_EXITO"), _revision(contenido, "FAQ")
            _bloque(t, _tarjeta(t, "Tiempo de revisión (mediana)", _duracion(post["medianaSeg"]),
                                f"por post de LinkedIn · n = {post['n']}",
                                f"Caso de éxito: {_duracion(caso['medianaSeg'])} (n = {caso['n']}) · FAQ: "
                                f"{_duracion(faq['medianaSeg'])} (n = {faq['n']})"))
        else:
            _bloque(t, _tarjeta(t, "Tiempo de revisión (mediana)", "—"))

    with tarjetas[2].container(key="dash-tarjeta-aprobacion"):
        if contenido:
            a = contenido["aprobacion"]
            revisados = a["aprobados"] + a["rechazados"]
            _bloque(t, _tarjeta(t, "Tasa de aprobación", _porcentaje(a["aprobados"], revisados),
                                f"{a['aprobados']} de {revisados} borradores revisados (n = {revisados})",
                                "Aprobados sobre lo revisado en el período."))
        else:
            _bloque(t, _tarjeta(t, "Tasa de aprobación", "—"))

    with tarjetas[3].container(key="dash-tarjeta-logro"):
        if contenido:
            logro = contenido["logroAAprobacion"]
            horas = logro["medianaHoras"]
            if horas is None:
                valor = "—"
            else:
                valor = f"{_numero(horas)} h" if horas < 48 else f"{_numero(horas / 24)} días"
            _bloque(t, _tarjeta(t, "Del logro al contenido aprobado", valor, f"mediana · n = {logro['n']} posts",
                                "Desde que el alumno contó su logro hasta que Marketing aprobó el post."))
        else:
            _bloque(t, _tarjeta(t, "Del logro al contenido aprobado", "—"))

    if contenido:
        col_embudo, col_semanas = st.columns(2)
        with col_embudo.container(key="dash-seccion-embudo"):
            e = contenido["embudo"]
            logros, publicables, aprobados_post = e["logros"], e["publicables"], e["conPostAprobado"]
            _titulo(t, "De logro a contenido aprobado",
                    f"La IA vio publicables {publicables} de {logros} logros, y Marketing aprobó {aprobados_post}."
                    if logros else None)
            if logros:
                etapas = ["Logros que escribieron los alumnos", "Publicables según la IA", "Aprobados por Marketing"]
                tabla = pd.DataFrame({
                    "Etapa": etapas, "Cantidad": [logros, publicables, aprobados_post],
                    "Etiqueta": [str(logros), f"{publicables} · {_porcentaje(publicables, logros)}",
                                 f"{aprobados_post} · {_porcentaje(aprobados_post, publicables)}"],
                })
                _grafico(_barras(t, tabla, "Cantidad", "Etapa", "Etiqueta", colores=t["embudo"], alto_fila=46,
                                 grosor=24))
                sin_decidir = logros - publicables - e["noPublicables"]
                _nota(t, f"Publicables: % de los logros. Aprobados: % de los publicables. "
                         f"No publicables ({e['noPublicables']}): antes de redactar, la IA decide si un logro alcanza "
                         f"para una historia y deja escrito el motivo (DEC-53)."
                         + (f" {sin_decidir} todavía sin decidir o con error." if sin_decidir else ""))
            else:
                st.info("No hay logros en este período.")

        with col_semanas.container(key="dash-seccion-semanas"):
            semanas = contenido.get("aprobadosPorSemana") or []
            mejor = max(semanas, key=lambda s: s["cantidad"], default=None)
            _titulo(t, "Contenido aprobado por semana",
                    f"{mejor['cantidad']} piezas la semana del {_dia(date.fromisoformat(mejor['inicio']))}: la "
                    f"semana con más aprobados." if mejor and mejor["cantidad"] else None)
            if mejor and mejor["cantidad"]:
                _grafico(_columnas_por_semana(t, semanas))
                _nota(t, "Posts de LinkedIn, casos de éxito y FAQ, por semana de aprobación (desde el lunes).")
            else:
                st.info("No se aprobó nada en este período.")

    _titulo(t, "Listos para publicar", "Lo aprobado y dónde se usa. Elige una fila para ver su texto y copiarlo.",
            tamano=22)
    if aprobados is not None:
        if not aprobados:
            st.info("Todavía no hay borradores aprobados.")
            return
        eleccion = st.dataframe(pd.DataFrame({
            "Qué": [ui.TIPOS.get(b["tipo"], b["tipo"]) + (f" {b['semana']}" if b.get("semana") else "")
                    for b in aprobados],
            "De quién": [b.get("autorNombre") or "Varias personas" for b in aprobados],
            "Dónde se publica": [DESTINOS.get(b["tipo"], "—") for b in aprobados],
            "Aprobado": [f"{ui.fecha(b.get('revisadoEn'))} · {b.get('revisadoPor') or '—'}" for b in aprobados],
        }), hide_index=True, on_select="rerun", selection_mode="single-row", key="dash_listos")
        # Sin fila elegida, el más reciente
        filas = list(getattr(getattr(eleccion, "selection", None), "rows", None) or []) or [0]
        elegido = aprobados[filas[0]]
        detalle = _pedir("el texto aprobado", cliente.detalle, elegido["id"])
        if detalle:
            ui.mostrar_texto(detalle.get("textoFinal") or detalle.get("textoIa"))
            _nota(t, "Para copiarlo, usa el ícono de copiar en la esquina del cuadro. Todo lo aprobado queda guardado "
                     "en OCI (aprobados/).")


def _nota_vista(t: dict, texto: str) -> None:
    _bloque(t, f'<p style="margin: 0; font-size: 17px; color: {t["suave"]}">{_e(texto)}</p>')


def _barra_lateral(t: dict, contenido: dict | None) -> None:
    """P5, en la barra lateral, debajo del usuario."""
    if not contenido:
        return
    with st.sidebar.container(key="dash-oci"):
        _bloque(t, f'<div style="font-weight: 600; font-size: 15px">Guardados en OCI</div>'
                   f'<div style="font-size: 14px; color: {t["suave"]}">{_e(contenido["activosOci"])} activos '
                   f'(borradores generados y aprobados)</div>')


# ── La página ──

cliente = ui.exigir_cliente()
tokens = TOKENS["oscuro" if ui.tema_oscuro() else "claro"]
hoy_bogota = datetime.now(ui.ZONA).date()  # el "hoy" de Bogotá, como Java (no el del contenedor, en UTC)

_estilos(tokens)
_bloque(tokens, f'<h1 style="margin: 0; font-size: 34px; font-weight: 700; color: {tokens["texto"]}">Dashboard</h1>')
# Pestañas que solo ejecutan la abierta: cada vista pide a Java solo lo suyo
pestana_comunidad, pestana_contenido = st.tabs(["Comunidad", "Contenido"], key="dash_vista", on_change="rerun")
if pestana_contenido.open:
    with pestana_contenido:
        _vista_contenido(tokens, hoy_bogota)
else:
    with pestana_comunidad:
        _vista_comunidad(tokens, hoy_bogota)
