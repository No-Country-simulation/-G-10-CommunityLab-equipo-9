"""
Página "Dashboard" (T08 y T12, N5, OE5): una vista por rol (DEC-153).

- Comunidad (el Community Manager): el clima de los alumnos, si el bot ayuda, quién espera respuesta,
  a quién escribir y qué falta en los documentos.
- Contenido (Marketing): cuánto hay por revisar, cuánto tarda la revisión, si la IA propone cosas útiles
  y qué se aprobó.

Las dos empiezan con la franja "Lo que hizo InsightEdu en este período". Orden (DEC-153): franja → hasta 4
tarjetas → gráficos → listas. Reglas (DEC-155): la n junto a cada porcentaje o índice, la mediana para los
tiempos y los alumnos separados de los mentores.

Java calcula y esta página solo dibuja (DEC-123). Cada dato se pide aparte: si uno falla, los demás se ven.
Los nombres y los textos de los alumnos van con st.dataframe, st.text o ui.mostrar_texto (escapados), nunca
en markdown. Los gráficos son de Altair (viene con Streamlit) y eligen su paleta según el tema (DEC-156).
"""
from __future__ import annotations

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

# Las paletas del prototipo, validadas para el daltonismo en los dos fondos (T12 §3.10).
# fondo: el del tema de Streamlit, para separar las barras con 2 px; texto: el de las etiquetas
PALETAS = {
    "claro": {
        "sentimiento": ["#9b2626", "#e8726a", "#dcdad3", "#6da7ec", "#184f95"],
        "serie": "#2a78d6",
        "embudo": ["#86b6ef", "#3987e5", "#1c5cab"],
        "fondo": "#ffffff",
        "texto": "#31333f",
    },
    "oscuro": {
        "sentimiento": ["#f4877d", "#a5453e", "#3b3e46", "#3b6db3", "#8cc0fb"],
        "serie": "#3987e5",
        "embudo": ["#1c5cab", "#3987e5", "#86b6ef"],
        "fondo": "#0e1117",
        "texto": "#fafafa",
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

MOTIVOS = {"MUY_NEGATIVO": "Un mensaje muy negativo", "DOS_DE_TRES": "2 negativos en sus últimos 3"}

# Dónde se usa cada tipo una vez aprobado (M11)
DESTINOS = {
    "POST_LINKEDIN": "LinkedIn",
    "CASO_EXITO": "Web y presentaciones a empresas",
    "FAQ": "#anuncios de Discord y la web",
}
TIPOS_PLURAL = {"POST_LINKEDIN": ("post", "posts"), "CASO_EXITO": ("caso de éxito", "casos de éxito"),
                "FAQ": ("FAQ", "FAQ")}

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ATAJOS = {"7 días": 7, "30 días": 30, "90 días": 90}
ELEGIR = "Elegir fechas"
MINUTOS_POR_DEFECTO = 30


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


def _tema(clave: str | None) -> str:
    return TEMAS.get(clave or "", clave or "—")


def _dia(d: date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


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


def _segundos(valor: float | None) -> str:
    return "—" if valor is None else f"{_numero(valor)} s"


def _revision(contenido: dict, tipo: str) -> dict:
    return next((r for r in contenido.get("revision") or [] if r["tipo"] == tipo), {"medianaSeg": None, "n": 0})


def enlace_discord(duda: dict) -> str | None:
    """El enlace al mensaje en Discord, o None si falta un dato. Los tres son números (snowflakes de Discord)."""
    partes = [duda.get("servidorId"), duda.get("canalId"), duda.get("discordId")]
    if not all(isinstance(p, str) and p.isdigit() for p in partes):
        return None
    return "https://discord.com/channels/{}/{}/{}".format(*partes)


def _grafico(grafico: alt.Chart) -> None:
    st.altair_chart(grafico.configure_view(stroke=None), width="stretch")


# ── Gráficos (Altair) ──

def _clima_divergente(sentimiento: dict, paleta: dict, por_semana: bool) -> alt.Chart | None:
    """
    C3: barras divergentes. Los negativos a la izquierda del 0, los positivos a la derecha y el neutro partido
    al medio. Cada fila suma 100 % y lleva su índice y su n en la etiqueta. None si no hay ningún mensaje.
    """
    filas, etiquetas = [], []
    for p in sentimiento.get("puntos") or []:
        c = {s: p["cantidades"].get(s, 0) for s in SENTIMIENTOS}
        n = sum(c.values())
        if n == 0:
            continue
        inicio = date.fromisoformat(p["inicio"])
        indice, _ = _clima(c)
        etiqueta = f"{'Semana del ' if por_semana else ''}{_dia(inicio)} · {indice:+d} (n = {n})"
        etiquetas.append(etiqueta)
        pct = {s: c[s] * 100 / n for s in SENTIMIENTOS}
        x = -(pct["MUY_NEGATIVO"] + pct["NEGATIVO"] + pct["NEUTRO"] / 2)
        for s, nombre in SENTIMIENTOS.items():
            filas.append({"Período": etiqueta, "Sentimiento": nombre, "x0": x, "x1": x + pct[s],
                          "Mensajes": c[s], "Porcentaje": round(pct[s])})
            x += pct[s]
    if not filas:
        return None
    barras = alt.Chart(pd.DataFrame(filas)).mark_bar(stroke=paleta["fondo"], strokeWidth=2).encode(
        x=alt.X("x0:Q", title="% de los mensajes de alumnos (← negativos · positivos →)",
                scale=alt.Scale(domain=[-100, 100]), axis=alt.Axis(format="d")),
        x2="x1:Q",
        y=alt.Y("Período:N", sort=etiquetas, title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("Sentimiento:N", scale=alt.Scale(domain=list(SENTIMIENTOS.values()),
                                                         range=paleta["sentimiento"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Período:N", "Sentimiento:N", "Mensajes:Q", alt.Tooltip("Porcentaje:Q", title="% de la fila")],
    )
    cero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=paleta["texto"], opacity=0.4).encode(x="x:Q")
    return (barras + cero).properties(height=max(120, 34 * len(etiquetas)))


def _barras_horizontales(tabla: pd.DataFrame, x: str, y: str, paleta: dict, titulo_x: str,
                         texto: str | None = None, dominio: list | None = None) -> alt.Chart:
    """Un solo color, ordenadas como vienen, con el valor en la punta (C6 y C9)."""
    escala = alt.Scale(domain=dominio) if dominio else alt.Undefined
    base = alt.Chart(tabla).encode(
        x=alt.X(f"{x}:Q", title=titulo_x, scale=escala, axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y(f"{y}:N", sort=None, title=None, axis=alt.Axis(labelLimit=220)),
        tooltip=[f"{y}:N", f"{x}:Q"],
    )
    barras = base.mark_bar(color=paleta["serie"], cornerRadiusEnd=4, size=16)
    etiquetas = base.mark_text(align="left", dx=4, color=paleta["texto"]).encode(text=f"{texto or x}:N")
    return (barras + etiquetas).properties(height=max(90, 30 * len(tabla)))


def _embudo(embudo: dict, paleta: dict) -> alt.Chart:
    """M6 + M7: logros → publicables según la IA → aprobados por Marketing, con el % de cada paso."""
    logros, publicables, aprobados = embudo["logros"], embudo["publicables"], embudo["conPostAprobado"]
    etapas = ["Logros", "Publicables según la IA", "Con su post aprobado"]
    tabla = pd.DataFrame({
        "Etapa": etapas,
        "Cantidad": [logros, publicables, aprobados],
        "Etiqueta": [str(logros), f"{publicables} · {_porcentaje(publicables, logros)} de los logros",
                     f"{aprobados} · {_porcentaje(aprobados, publicables)} de los publicables"],
    })
    base = alt.Chart(tabla).encode(
        x=alt.X("Cantidad:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("Etapa:N", sort=etapas, title=None, axis=alt.Axis(labelLimit=220)),
        tooltip=["Etapa:N", "Cantidad:Q"],
    )
    barras = base.mark_bar(cornerRadiusEnd=4, size=22).encode(
        color=alt.Color("Etapa:N", scale=alt.Scale(domain=etapas, range=paleta["embudo"]), legend=None))
    etiquetas = base.mark_text(align="left", dx=4, color=paleta["texto"]).encode(text="Etiqueta:N")
    return (barras + etiquetas).properties(height=140)


def _columnas_por_semana(semanas: list[dict], paleta: dict) -> alt.Chart:
    """M8: lo aprobado por semana de aprobación, con el valor arriba."""
    orden = [_dia(date.fromisoformat(s["inicio"])) for s in semanas]
    tabla = pd.DataFrame({"Semana del": orden, "Aprobados": [s["cantidad"] for s in semanas]})
    base = alt.Chart(tabla).encode(
        x=alt.X("Semana del:N", sort=orden, title="Semana (desde el lunes)", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Aprobados:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
        tooltip=["Semana del:N", "Aprobados:Q"],
    )
    barras = base.mark_bar(color=paleta["serie"], cornerRadiusEnd=4, size=28)
    etiquetas = base.mark_text(baseline="bottom", dy=-4, color=paleta["texto"]).encode(text="Aprobados:Q")
    return (barras + etiquetas).properties(height=220)


# ── Controles ──

cliente = ui.exigir_cliente()
paleta = PALETAS["oscuro" if ui.tema_oscuro() else "claro"]
hoy = datetime.now(ui.ZONA).date()  # el "hoy" de Bogotá, como Java (no el del contenedor, en UTC)

col_vista, col_periodo = st.columns([1, 2])
vista = col_vista.segmented_control("Vista", ["Comunidad", "Contenido"], default="Comunidad", required=True,
                                    key="dash_vista",
                                    help="Comunidad: para el Community Manager. Contenido: para Marketing.")
atajo = col_periodo.segmented_control("Período", [*ATAJOS, ELEGIR], default="30 días", required=True,
                                      key="dash_atajo")

if atajo == ELEGIR:
    periodo = st.date_input("Fechas", value=(hoy - timedelta(days=29), hoy), max_value=hoy, format="YYYY-MM-DD",
                            key="dash_periodo")
    if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
        st.info("Elige la fecha final del período.")
        st.stop()
    desde, hasta = periodo
    if (hasta - desde).days + 1 > 366:
        st.warning("El período puede tener hasta 366 días.")
        st.stop()
else:
    hasta = hoy
    desde = hoy - timedelta(days=ATAJOS.get(atajo, 30) - 1)
st.caption(f"Del {desde.isoformat()} al {hasta.isoformat()}, en hora de Bogotá.")

dias_desercion, horas_sin_responder = 14, 24
if vista == "Comunidad":
    with st.expander("Ajustes de las alertas"):
        col_dias, col_horas = st.columns(2)
        dias_desercion = int(col_dias.number_input("Posible deserción: días sin escribir", min_value=1,
                                                   max_value=365, value=14, step=1, key="dash_dias"))
        horas_sin_responder = int(col_horas.number_input("Dudas sin respuesta después de (horas)", min_value=0,
                                                         max_value=2160, value=24, step=1, key="dash_horas"))

# ── Franja: lo que hizo InsightEdu en este período (P1 y P4, las dos vistas) ──

contenido = _pedir("la franja de valor", cliente.dashboard_contenido, desde, hasta)

with st.container(border=True):
    st.subheader("Lo que hizo InsightEdu en este período")
    if contenido:
        embudo = contenido["embudo"]
        minutos = _minutos_por_historia()
        historias = embudo["conPostAprobado"]
        post = _revision(contenido, "POST_LINKEDIN")
        revision_min = (post["medianaSeg"] or 0) / 60
        horas = max(minutos - revision_min, 0) * historias / 60
        col_horas_ahorradas, col_historias = st.columns(2)
        with col_horas_ahorradas:
            st.metric("Horas ahorradas a Marketing (estimado)", f"≈ {_numero(horas, 1)} h")
            # DEC-154: el supuesto va siempre junto al número
            st.caption(f"Estimado: supone {minutos} min por historia encontrada y redactada a mano, menos la "
                       f"revisión en el panel.")
            st.caption(f"Cálculo: ({minutos} − {_numero(revision_min, 1)} min de revisión, mediana de "
                       f"{post['n']} posts) × {historias} logros con su post aprobado.")
        with col_historias:
            st.metric("Historias encontradas solas", embudo["publicables"])
            st.caption(f"Logros publicables que la IA encontró, sin que nadie los buscara: de "
                       f"{contenido['mensajesDePersonas']} mensajes de personas y {embudo['logros']} logros del "
                       f"período.")

# P5, en la barra lateral, debajo del usuario
if contenido:
    with st.sidebar:
        st.metric("Archivos guardados en OCI", contenido["activosOci"])
        st.caption("Borradores generados y aprobados que ya están en el bucket.")


# ── Vista Comunidad (el Community Manager) ──

def _vista_comunidad() -> None:
    por_semana = (hasta - desde).days >= 14
    largo = (hasta - desde).days + 1
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

    # Tarjetas
    tarjetas = st.columns(4)
    with tarjetas[0].container(border=True):
        indice, n = _clima(_sumar(clima)) if clima else (None, 0)
        delta, nota = None, None
        if indice is not None and clima_antes is not None:
            antes, n_antes = _clima(_sumar(clima_antes))
            if n_antes:
                delta = f"{indice - antes:+d} frente al período anterior (n = {n_antes})"
            else:
                nota = "Sin datos del período anterior para comparar."
        st.metric("Clima de los alumnos", _indice(indice), delta=delta)
        st.caption(f"De −100 a +100: % positivos − % negativos. n = {n} mensajes de alumnos.")
        if clima_todos:
            indice_todos, n_todos = _clima(_sumar(clima_todos))
            st.caption(f"Toda la comunidad (también mentores): {_indice(indice_todos)} (n = {n_todos}).")
        if nota:
            st.caption(nota)

    with tarjetas[1].container(border=True):
        bot = (comunidad or {}).get("bot")
        if bot:
            vistas = bot["respondidas"] + bot["derivadas"]
            st.metric("Dudas que respondió el bot", _porcentaje(bot["respondidas"], vistas))
            st.caption(f"{bot['respondidas']} de {vistas} dudas que vio el bot (n = {vistas}). Reacciona en "
                       f"{_segundos(bot['segundosMediana'])} (mediana).")
            st.caption(f"{bot['derivadas']} derivadas a un mentor. {bot['sinPasarPorElBot']} llegaron por lote, "
                       f"sin pasar por el bot.")
        else:
            st.metric("Dudas que respondió el bot", "—")

    with tarjetas[2].container(border=True):
        st.metric(f"Dudas sin respuesta (más de {horas_sin_responder} h)", "—" if dudas is None else dudas["total"])
        if alumnos:
            st.caption(f"De {alumnos['dudas']} dudas de alumnos del período. La lista está más abajo.")

    with tarjetas[3].container(border=True):
        n_desercion = len((desercion or {}).get("personas") or [])
        n_frustracion = len((frustracion or {}).get("personas") or [])
        total = alumnos.get("total")
        st.metric("Alumnos que necesitan apoyo", f"{n_desercion} de {total}" if total else n_desercion)
        st.caption(f"Posible deserción: más de {dias_desercion} días sin escribir, contados desde hoy. Si el "
                   f"servidor está quieto, este número sube.")
        st.caption(f"Posible frustración: {n_frustracion} (un mensaje muy negativo, o 2 negativos entre sus "
                   f"últimos 3 del período).")

    # Gráficos
    with st.container(border=True):
        st.subheader(f"Clima de los alumnos por {'semana' if por_semana else 'día'}")
        grafico = _clima_divergente(clima, paleta, por_semana) if clima else None
        if grafico is None:
            st.info("No hay mensajes de alumnos con sentimiento en este período.")
        else:
            _grafico(grafico)
            with st.expander("Ver los números"):
                st.dataframe(pd.DataFrame([{
                    "Semana del" if por_semana else "Día": p["inicio"],
                    **{nombre: p["cantidades"].get(s, 0) for s, nombre in SENTIMIENTOS.items()},
                    "n": sum(p["cantidades"].values()),
                    "Índice": _indice(_clima(p["cantidades"])[0]),
                } for p in clima["puntos"] if sum(p["cantidades"].values())]), hide_index=True)
        st.caption("Solo alumnos (sin mentores) y solo mensajes clasificados con sentimiento. El índice va de −100 "
                   "(todo negativo) a +100 (todo positivo).")

    col_activos, col_temas = st.columns(2)
    with col_activos.container(border=True):
        st.subheader("Alumnos activos")
        if alumnos.get("total"):
            t = alumnos["total"]
            tabla = pd.DataFrame({
                "Ventana": ["Últimos 7 días", "Últimos 30 días"],
                "Alumnos": [alumnos["activos7Dias"], alumnos["activos30Dias"]],
                "Etiqueta": [f"{alumnos['activos7Dias']} de {t}", f"{alumnos['activos30Dias']} de {t}"],
            })
            _grafico(_barras_horizontales(tabla, "Alumnos", "Ventana", paleta, "Alumnos que escribieron",
                                          texto="Etiqueta", dominio=[0, t]))
            st.caption(f"Con al menos un mensaje, contando hasta el {hasta.isoformat()}. De {t} alumnos que "
                       f"escribieron alguna vez.")
        elif comunidad is not None:
            st.info("Todavía no escribió ningún alumno.")

    with col_temas.container(border=True):
        st.subheader("De qué hablan los alumnos")
        lista = [t for t in (temas or {}).get("temas") or [] if t["actual"]]
        if lista:
            tabla = pd.DataFrame({"Tema": [_tema(t["tema"]) for t in lista],
                                  "Mensajes": [t["actual"] for t in lista]})
            _grafico(_barras_horizontales(tabla, "Mensajes", "Tema", paleta, "Mensajes de alumnos"))
            st.caption("Mensajes de alumnos del período por tema, de mayor a menor.")
        elif temas is not None:
            st.info("No hay temas en este período.")

    # Listas de acción
    with st.container(border=True):
        st.subheader("Esperan respuesta")
        if dudas is not None:
            lista = dudas.get("dudas") or []
            if not lista:
                st.success("No hay dudas sin respuesta en este período.")
            else:
                total = dudas.get("total", len(lista))
                if total > len(lista):
                    st.text(f"Se muestran {len(lista)} de {total}.")
                for d in lista:
                    with st.container(border=True):
                        derivada = " · derivada a un mentor" if d.get("derivada") else ""
                        st.text(f"{d.get('autorNombre') or '—'} · #{d.get('canal') or '—'} · "
                                f"{ui.fecha(d.get('fecha'))} · {_tema(d.get('tema'))}{derivada}")
                        ui.mostrar_texto(d.get("texto"))
                        enlace = enlace_discord(d)
                        if enlace:
                            st.link_button("Abrir en Discord", enlace)
        st.caption(f"Dudas de alumnos con más de {horas_sin_responder} horas, que el bot no respondió y a las que "
                   f"ninguna otra persona contestó con «Responder» de Discord. Una duda derivada sigue aquí hasta "
                   f"que alguien la conteste.")

    with st.container(border=True):
        st.subheader("A quién escribir")
        filas = [{"Alumno": p["nombre"], "Motivo": f"Lleva {p['diasSinEscribir']} días sin escribir",
                  "Último mensaje o negativo": ui.fecha(p["ultimoMensaje"])}
                 for p in (desercion or {}).get("personas") or []]
        filas += [{"Alumno": p["nombre"], "Motivo": ", ".join(MOTIVOS.get(m, m) for m in p["motivos"]),
                   "Último mensaje o negativo": ui.fecha(p["ultimoNegativo"])}
                  for p in (frustracion or {}).get("personas") or []]
        if filas:
            st.dataframe(pd.DataFrame(filas), hide_index=True)
        elif desercion is not None and frustracion is not None:
            st.success("Ningún alumno muestra señales de deserción ni de frustración.")
        st.caption("Posible deserción: sin escribir hace más días que el umbral (contados desde hoy). Posible "
                   "frustración: un mensaje muy negativo en el período, o 2 negativos entre sus últimos 3 mensajes "
                   "del período. Mentores y bots no cuentan.")

    with st.container(border=True):
        st.subheader("Qué falta en los documentos")
        derivadas = (comunidad or {}).get("derivadasPorTema") or []
        if derivadas:
            st.dataframe(pd.DataFrame({"Tema": [_tema(d["tema"]) for d in derivadas],
                                       "Dudas derivadas": [d["cantidad"] for d in derivadas]}), hide_index=True)
        elif comunidad is not None:
            st.success("El bot encontró respaldo en los documentos para todas las dudas que vio.")
        st.caption("Dudas que el bot derivó a un mentor porque no encontró la respuesta en los PDF del Agente FAQ: "
                   "son los temas que conviene sumar a los documentos.")


# ── Vista Contenido (Marketing) ──

def _vista_contenido() -> None:
    aprobados = _pedir("los aprobados", cliente.listar_borradores, "APROBADO", None, 20)

    tarjetas = st.columns(4)
    with tarjetas[0].container(border=True):
        por_revisar = (contenido or {}).get("porRevisar")
        st.metric("Por revisar", "—" if not por_revisar else por_revisar["total"])
        if por_revisar and por_revisar["total"]:
            partes = [f"{n} {TIPOS_PLURAL[t][0 if n == 1 else 1]}" for t, n in por_revisar["porTipo"].items() if n]
            espera = (datetime.now(ui.ZONA) - datetime.fromisoformat(
                por_revisar["masAntiguo"].replace("Z", "+00:00"))).days
            st.caption(f"{' y '.join(partes)}. El más antiguo espera hace {espera} días.")
        elif por_revisar:
            st.caption("No hay nada pendiente.")
        st.page_link("paginas/borradores.py", label="Ir a Borradores")

    with tarjetas[1].container(border=True):
        if contenido:
            post = _revision(contenido, "POST_LINKEDIN")
            caso, faq = _revision(contenido, "CASO_EXITO"), _revision(contenido, "FAQ")
            st.metric("Tiempo de revisión de un post", _segundos(post["medianaSeg"]))
            st.caption(f"Mediana, n = {post['n']}.")
            st.caption(f"Caso de éxito: {_segundos(caso['medianaSeg'])} (n = {caso['n']}). FAQ: "
                       f"{_segundos(faq['medianaSeg'])} (n = {faq['n']}).")
        else:
            st.metric("Tiempo de revisión de un post", "—")

    with tarjetas[2].container(border=True):
        if contenido:
            a = contenido["aprobacion"]
            revisados = a["aprobados"] + a["rechazados"]
            st.metric("Tasa de aprobación", _porcentaje(a["aprobados"], revisados))
            st.caption(f"{a['aprobados']} aprobados de {revisados} revisados (n = {revisados}).")
        else:
            st.metric("Tasa de aprobación", "—")

    with tarjetas[3].container(border=True):
        if contenido:
            logro = contenido["logroAAprobacion"]
            horas = logro["medianaHoras"]
            if horas is None:
                valor = "—"
            else:
                valor = f"{_numero(horas)} h" if horas < 48 else f"{_numero(horas / 24, 1)} días"
            st.metric("Del logro al post aprobado", valor)
            st.caption(f"Mediana desde el mensaje del logro hasta la aprobación de su post, n = {logro['n']}.")
        else:
            st.metric("Del logro al post aprobado", "—")

    if contenido:
        col_embudo, col_semanas = st.columns(2)
        with col_embudo.container(border=True):
            st.subheader("De logro a contenido aprobado")
            e = contenido["embudo"]
            if e["logros"]:
                _grafico(_embudo(e, paleta))
                sin_decidir = e["logros"] - e["publicables"] - e["noPublicables"]
                st.caption(f"{e['noPublicables']} no publicables: antes de redactar, la IA decide si un logro "
                           f"alcanza para una historia y deja escrito el motivo (DEC-53). Por ejemplo, «por fin "
                           f"entendí recursividad» no es un post."
                           + (f" {sin_decidir} todavía sin decidir o con error." if sin_decidir else ""))
            else:
                st.info("No hay logros en este período.")

        with col_semanas.container(border=True):
            st.subheader("Contenido aprobado por semana")
            semanas = contenido.get("aprobadosPorSemana") or []
            if any(s["cantidad"] for s in semanas):
                _grafico(_columnas_por_semana(semanas, paleta))
                st.caption("Posts, casos de éxito y FAQ, por la semana en que se aprobaron.")
            else:
                st.info("No se aprobó nada en este período.")

    with st.container(border=True):
        st.subheader("Listos para publicar")
        if aprobados is not None:
            if not aprobados:
                st.info("Todavía no hay borradores aprobados.")
            else:
                st.dataframe(pd.DataFrame({
                    "#": [b["id"] for b in aprobados],
                    "Tipo": [ui.TIPOS.get(b["tipo"], b["tipo"]) for b in aprobados],
                    "Dónde se usa": [DESTINOS.get(b["tipo"], "—") for b in aprobados],
                    "Aprobado": [ui.fecha(b.get("revisadoEn")) for b in aprobados],
                    "Extracto": [b.get("extracto") or "" for b in aprobados],
                }), hide_index=True)
                por_id = {b["id"]: b for b in aprobados}
                elegido = st.selectbox("Ver el texto final para copiarlo", list(por_id), key="dash_aprobado",
                                       format_func=lambda i: f"#{i} · {ui.TIPOS.get(por_id[i]['tipo'], '')}")
                detalle = _pedir("el texto aprobado", cliente.detalle, elegido)
                if detalle:
                    ui.mostrar_texto(detalle.get("textoFinal") or detalle.get("textoIa"))
                    st.caption("Para copiarlo, usa el ícono de copiar en la esquina del cuadro.")
        st.caption("Los aprobados más recientes y dónde se usa cada tipo.")


if vista == "Contenido":
    _vista_contenido()
else:
    _vista_comunidad()
