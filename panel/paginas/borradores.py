"""
Página "Borradores" (T07; rehecha en T13 con el prototipo aprobado, DEC-159): una cola de logros.

- Cada tarjeta es un logro de un alumno, con sus dos textos (el post de LinkedIn y el caso de éxito), o una FAQ
  semanal. A la izquierda, la cola; a la derecha, el logro elegido.
- Cada texto tiene sus botones (Aprobar, Guardar edición y Rechazar…) y su tiempo de revisión: desde que se abrió
  la tarjeta en esta sesión, o desde la última aprobación o rechazo en esa misma tarjeta (decisión 2).
- Un solo consentimiento por logro (D6): vale para los dos textos, y cada Aprobar lo exige. Java y la base lo
  exigen también: son tres capas.
- El botón del post dice antes de aprobar qué pasará en LinkedIn (linkedinModo) y, si va a publicar, pide confirmar.
- Las dos pestañas se dibujan siempre, y los textos editados se guardan en st.session_state["ediciones"]: así una
  edición no se pierde al cambiar de pestaña ni de tarjeta (Streamlit borra el estado de un widget que no se dibujó).

Seguridad (DEC-158): los nombres, el mensaje original, los borradores y el motivo van con st.text o st.text_area.
En las etiquetas de los widgets y en st.success (que interpretan markdown) el nombre va escapado
(logros.escapar_markdown). Los bloques de HTML solo llevan textos fijos y números.
"""
from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

import estilo
import logros
import ui
from cliente_java import ErrorJava
from logros import CASO, FAQ, POST

ESTADOS = {"PENDIENTE": "Por revisar", "APROBADO": "Aprobados", "RECHAZADO": "Rechazados"}
LIMITE = 500
VACIAS = {"PENDIENTE": "No hay nada por revisar. Cuando la IA proponga un logro o una FAQ, aparecerá aquí.",
          "APROBADO": "Todavía no hay nada aprobado.", "RECHAZADO": "No hay nada rechazado."}
ETIQUETAS_TEXTO = {POST: "Texto del post (puedes editarlo)", CASO: "Texto del caso de éxito (puedes editarlo)",
                   FAQ: "Texto de la FAQ (puedes editarlo)"}
SUAVE_14 = f"font-size: 14px; {estilo.SUAVE}"


# ── Estado de la sesión ──

def _ir_a_contenido() -> None:
    st.session_state["ir_a_contenido"] = True


def _elegir(clave: str) -> None:
    st.session_state["tarjeta_elegida"] = clave
    st.session_state.pop("confirmar_publicar", None)


def _abiertas() -> dict:
    """Cuándo empezó a correr el tiempo de cada tarjeta (time.monotonic)."""
    return st.session_state.setdefault("abiertas", {})


def _ediciones() -> dict:
    """Lo que se escribió en cada texto, por id: sobrevive aunque su pestaña o su tarjeta no se dibuje."""
    return st.session_state.setdefault("ediciones", {})


def _segundos(clave: str) -> int:
    return int(time.monotonic() - _abiertas().get(clave, time.monotonic()))


def _olvidar_edicion(borrador_id: int) -> None:
    _ediciones().pop(borrador_id, None)
    st.session_state.pop(f"texto_{borrador_id}", None)


# ── Piezas de la página ──

def _cuando(iso: str | None) -> str:
    """Una fecha de Java como en el prototipo: "10 oct, 18:42", en la hora de Bogotá."""
    try:
        f = datetime.fromisoformat((iso or "").replace("Z", "+00:00")).astimezone(ui.ZONA)
    except ValueError:
        return "—"
    return f"{estilo.dia(f.date())}, {f:%H:%M}"


def _texto_suave(texto: str) -> None:
    """Una nota fija del panel (no un dato), a 14 px y más tenue."""
    estilo.bloque(f'<div style="{SUAVE_14}">{estilo.e(texto)}</div>')


def _etiqueta_caja(texto: str) -> None:
    estilo.bloque(f'<div style="font-size: 14px; font-weight: 600; {estilo.SUAVE}">{estilo.e(texto)}</div>')


def _tarjeta_cola(t: logros.Tarjeta, estado: str, elegida: bool) -> None:
    """Una tarjeta de la cola. Toda la tarjeta es un botón (transparente, encima): la regla bor-* de estilo.ESTILOS."""
    with st.container(key=f"bor-{'elegida' if elegida else 'tarjeta'}-{t.clave}", gap="small"):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", gap="small"):
            with st.container(key=f"bor-nombre-{t.clave}", width="stretch"):
                st.text(t.titulo)
            revisados = [t.textos[x].get("revisadoEn") for x in t.en_estado(estado)]
            cuando = estilo.hace(t.creado if estado == "PENDIENTE" else max(r or "" for r in revisados) or None)
            estilo.bloque(f'<div style="font-size: 13px; {estilo.SUAVE}; white-space: nowrap">{estilo.e(cuando)}</div>')
        if t.motivo:
            with st.container(key=f"bor-resumen-{t.clave}"):
                st.text(estilo.corto(t.motivo, 90))
        estilo.bloque(f'<span style="font-size: 13px; background: {estilo.FONDO_ETIQUETA}; border-radius: 999px; '
                      f'padding: 2px 10px">{estilo.e(t.etiqueta(estado))}</span>')
        st.button(f"Abrir: {logros.escapar_markdown(t.titulo)}", key=f"abrir_{t.clave}", on_click=_elegir,
                  args=(t.clave,))


def _aviso(aviso: dict) -> None:
    """El aviso verde de lo que se acaba de aprobar o rechazar. El texto ya trae el nombre escapado."""
    (st.success if aviso.get("ok", True) else st.warning)(aviso["texto"])
    if aviso.get("enlace"):
        st.button("Verlos en Listos para publicar", key="ir_contenido", type="tertiary",
                  icon=":material/arrow_forward:", icon_position="right", on_click=_ir_a_contenido)


def _encabezado(t: logros.Tarjeta, detalles: dict[str, dict]) -> None:
    primero = detalles[t.tipos[0]]
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        with st.container(key="bor-titulo", width="stretch"):
            st.text(t.titulo if t.es_faq else f"Logro de {t.nombre}")
        with st.container(key="bor-meta", width="content"):
            if t.es_faq:
                faq = primero.get("faq") or {}
                st.text(f"Del {_cuando(faq.get('desde'))} al {_cuando(faq.get('hasta'))} · {estilo.hace(t.creado)}")
            else:
                origen = primero.get("origen") or {}
                st.text(f"#{origen.get('canal') or '—'} · {_cuando(origen.get('fecha'))} · "
                        f"{estilo.hace(origen.get('fecha'))}")


def _contexto(t: logros.Tarjeta, detalles: dict[str, dict]) -> None:
    primero = detalles[t.tipos[0]]
    izquierda, derecha = st.columns(2, gap="small")
    with izquierda.container(key="bor-caja-origen", gap="small"):
        if t.es_faq:
            _etiqueta_caja("Qué junta")
            st.text("Las dudas repetidas de la semana. Revisa que ninguna pregunta incluya el nombre de un alumno.")
        else:
            _etiqueta_caja("Mensaje original")
            st.text(f"“{(primero.get('origen') or {}).get('texto') or '(sin texto)'}”")
    with derecha.container(key="bor-caja-motivo", gap="small"):
        _etiqueta_caja("Por qué la IA la propuso" if t.es_faq else "Por qué la IA lo propuso")
        st.text(primero.get("motivoIa") or "(sin motivo)")


def _consentimiento(t: logros.Tarjeta, detalles: dict[str, dict]) -> bool:
    """Una sola casilla por logro (decisión 2c). Marcada si ya se aprobó un texto con consentimiento."""
    clave = f"consentimiento_{t.clave}"
    ya_dado = any(d.get("consentimientoConfirmado") for d in detalles.values())
    st.session_state.setdefault(clave, ya_dado)
    with st.container(key="bor-consentimiento"):
        return st.checkbox(f"{logros.escapar_markdown(t.nombre)} dio su consentimiento para publicar su nombre y su "
                           f"historia. **Vale para los dos textos.**", key=clave)


def _copiar(texto: str, clave: str) -> None:
    with st.popover("Copiar texto", icon=":material/content_copy:", key=f"copiar_{clave}"):
        _texto_suave("Usa el ícono de copiar en la esquina del cuadro.")
        ui.mostrar_texto(texto)


def _destino(tipo: str) -> None:
    # Texto fijo del panel (DESTINOS), en markdown para usar un ícono de Material: los SVG no se ven dentro de st.html
    with st.container(key=f"bor-destino-{tipo}"):
        st.markdown(f":material/location_on: Dónde se publica: {estilo.DESTINOS.get(tipo, '—')}")


def _solo_lectura(d: dict) -> None:
    """Un texto que ya no está pendiente: se lee, se copia y, si es un post aprobado, dice qué pasó en LinkedIn."""
    texto = d.get("textoFinal") or d.get("textoIa") or ""
    st.text_area("Texto final", value=texto, height=300, disabled=True, key=f"leer_{d['id']}")
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        _texto_suave(logros.contador(d["tipo"], texto))
        _copiar(texto, f"leer_{d['id']}")
    with st.container(key=f"bor-lectura-{d['id']}", gap="small"):
        if d["estado"] == "APROBADO":
            consentimiento = "confirmado" if d.get("consentimientoConfirmado") else "no hacía falta"
            st.text(f"Aprobado por {d.get('aprobadoPor') or '—'} el {ui.fecha(d.get('aprobadoEn'))} · revisión: "
                    f"{d.get('tiempoCuraduriaSeg')} s · consentimiento: {consentimiento}")
            if d["tipo"] == POST:
                linkedin = d.get("linkedin") or {}
                st.text(logros.estado_linkedin(linkedin, d.get("aprobadoEn")))
                enlace = logros.enlace_linkedin(linkedin.get("postId"))
                if enlace:
                    st.link_button("Ver en LinkedIn", enlace, icon=":material/open_in_new:", icon_position="right")
        else:
            st.text(f"Rechazado por {d.get('rechazadoPor') or '—'} el {ui.fecha(d.get('rechazadoEn'))}")
            if d.get("motivoRechazo"):
                st.text(f"Motivo: {d['motivoRechazo']}")


def _editable(d: dict, t: logros.Tarjeta, consentimiento: bool, modo: str | None) -> None:
    """Un texto pendiente: se edita, se cuenta y se aprueba, se guarda o se rechaza, solo él (decisión 1)."""
    tipo, bid = d["tipo"], d["id"]
    texto_actual = d.get("textoFinal") or d.get("textoIa") or ""
    clave_texto = f"texto_{bid}"
    if clave_texto not in st.session_state:  # la primera vez, o después de no dibujarse: lo último que se escribió
        st.session_state[clave_texto] = _ediciones().get(bid, texto_actual)
    texto = st.text_area(ETIQUETAS_TEXTO[tipo], height=320, key=clave_texto)
    _ediciones()[bid] = texto

    largo = logros.muy_largo(tipo, texto)
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        color = f"color: {estilo.ALERTA}; font-weight: 600" if largo else estilo.SUAVE
        estilo.bloque(f'<div style="font-size: 14px; {color}">{estilo.e(logros.contador(tipo, texto))}</div>')
        _copiar(texto, str(bid))

    requiere = d.get("requiereConsentimiento", tipo != FAQ)
    falta = requiere and not consentimiento
    if tipo == POST:
        etiqueta, nota_linkedin, confirmar = logros.boton_post(modo)
    else:
        etiqueta, nota_linkedin, confirmar = ("Aprobar caso de éxito" if tipo == CASO else "Aprobar FAQ"), None, False
    sujeto = "el post" if tipo == POST else ("el caso de éxito" if tipo == CASO else "la FAQ")
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        aprobar = st.button(etiqueta, type="primary", key=f"aprobar_{bid}", disabled=falta or largo)
        guardar = st.button("Guardar edición", key=f"guardar_{bid}")
        with st.container(key=f"bor-rechazar-{bid}", width="content"):
            with st.popover("Rechazar…", key=f"popover_rechazar_{bid}"):
                motivo = st.text_input("Motivo (opcional)", max_chars=500, key=f"motivo_{bid}")
                rechazar = st.button(f"Rechazar {sujeto}", key=f"rechazar_{bid}")
    if falta:
        _texto_suave("Para aprobar, marca la casilla de consentimiento.")
    if largo:
        estilo.bloque(f'<div style="font-size: 14px; color: {estilo.ALERTA}">LinkedIn acepta hasta 3.000 caracteres: '
                      f'acorta el post para aprobarlo.</div>')
    if nota_linkedin:
        _texto_suave(nota_linkedin)
    if tipo == FAQ:
        _texto_suave("La FAQ no nombra alumnos: no necesita consentimiento.")

    try:
        if guardar:
            cliente.editar(bid, ui.usuario_actual(), texto)
            _olvidar_edicion(bid)
            ui.avisar("ok", "Edición guardada. Sigue pendiente de aprobación.")
            st.rerun()
        if aprobar and not (falta or largo):  # apagado ya lo impide; esto es por si acaso
            if confirmar:
                st.session_state["confirmar_publicar"] = bid
            else:
                _aprobar(d, t, texto, texto_actual, consentimiento)
        if st.session_state.get("confirmar_publicar") == bid:
            _confirmar(d, t, texto, texto_actual, consentimiento, modo)
        if rechazar:
            cliente.rechazar(bid, ui.usuario_actual(), motivo.strip() or None, _segundos(t.clave))
            _despues(d, t, "rechazad")
    except ErrorJava as e:
        if e.estado == 409:
            st.warning(f"{e.mensaje} Actualiza la lista.")
        else:
            st.error(e.mensaje)


def _no_confirmar() -> None:
    st.session_state.pop("confirmar_publicar", None)


@st.dialog("¿Publicar en LinkedIn?", on_dismiss=_no_confirmar)
def _confirmar(d: dict, t: logros.Tarjeta, texto: str, texto_actual: str, consentimiento: bool,
               modo: str | None) -> None:
    """REAL o sin el dato: aprobar puede publicar en público. Solo al confirmar se envía el pedido (decisión 2b)."""
    if modo == "REAL":
        st.text("Se publicará en público en el LinkedIn de CommunityLab, en cuanto apruebes.")
    else:
        st.text("No se pudo saber si LinkedIn está encendido: si lo está, se publicará en público en el LinkedIn "
                "de CommunityLab.")
    publicar, cancelar = st.columns(2)
    if publicar.button("Publicar ahora", type="primary", key=f"publicar_{d['id']}", width="stretch"):
        _no_confirmar()
        try:
            _aprobar(d, t, texto, texto_actual, consentimiento)
        except ErrorJava as e:
            st.warning(f"{e.mensaje} Actualiza la lista." if e.estado == 409 else e.mensaje)
    if cancelar.button("Cancelar", key=f"cancelar_{d['id']}", width="stretch"):
        _no_confirmar()
        st.rerun()


def _aprobar(d: dict, t: logros.Tarjeta, texto: str, texto_actual: str, consentimiento: bool) -> None:
    # Si el texto cambió respecto de lo guardado, la edición viaja en el mismo pedido que la aprobación
    editado = texto if texto != texto_actual else None
    cliente.aprobar(d["id"], ui.usuario_actual(), consentimiento, _segundos(t.clave), editado)
    _despues(d, t, "aprobad")


def _despues(d: dict, t: logros.Tarjeta, accion: str) -> None:
    """El aviso de cada texto y el reloj de la tarjeta: el texto que sigue cuenta desde ahora (decisión 2)."""
    _olvidar_edicion(d["id"])
    quedan = [x for x in t.pendientes if x != d["tipo"]]
    sujeto, terminacion = logros.SUJETOS[d["tipo"]]
    texto = f"{sujeto} {accion}{terminacion}."
    enlace = False
    if quedan:
        _abiertas()[t.clave] = time.monotonic()
        texto += f" Falta revisar {logros.CON_ARTICULO[quedan[0]]}."
    else:
        _abiertas().pop(t.clave, None)
        st.session_state.pop(f"consentimiento_{t.clave}", None)
        aprobados = t.en_estado("APROBADO") + ([d["tipo"]] if accion == "aprobad" else [])
        if not t.es_faq and sorted(aprobados) == sorted([POST, CASO]):
            texto = f"Aprobados los dos textos de {logros.escapar_markdown(t.nombre)}."
        enlace = bool(aprobados)
    st.session_state["aviso_borradores"] = {"texto": texto, "clave": t.clave, "enlace": enlace}
    st.rerun()


def _oci(detalles: dict[str, dict]) -> None:
    """T09: si los textos ya están guardados en OCI. Solo el estado: Java nunca manda la ruta ni la URL PAR."""
    with st.expander("Guardado en OCI"):
        for tipo, d in detalles.items():
            for linea in ui.lineas_oci(d.get("oci"), d["estado"]):
                st.text(f"{logros.NOMBRES[tipo]} · {linea}")


def _detalle(t: logros.Tarjeta, estado: str, modo: str | None, aviso: dict | None) -> None:
    try:
        detalles = {tipo: cliente.detalle(b["id"]) for tipo, b in t.textos.items()}
    except ErrorJava as e:
        st.error(e.mensaje)
        return
    pendientes = [x for x in t.tipos if detalles[x]["estado"] == "PENDIENTE"]
    if pendientes:
        # El tiempo corre desde que se abre esta tarjeta en la sesión (o desde el último texto revisado en ella)
        _abiertas().setdefault(t.clave, time.monotonic())

    _encabezado(t, detalles)
    _contexto(t, detalles)
    if aviso:
        _aviso(aviso)
    consentimiento = False
    if pendientes and not t.es_faq:
        consentimiento = _consentimiento(t, detalles)

    # Las pestañas se dibujan las dos (no solo la abierta): así ninguna pierde su edición. Su clave cambia cuando
    # cambia lo pendiente, para abrir el texto que falta revisar (o, en Aprobados y Rechazados, el de ese estado)
    nombres = [logros.NOMBRES[x] for x in t.tipos]
    en_estado = t.en_estado(estado) or t.tipos
    abierta = logros.NOMBRES[pendientes[0] if estado == "PENDIENTE" and pendientes else en_estado[0]]
    pestanas = st.tabs(nombres, default=abierta, key=f"pestanas_{t.clave}_{estado}_{'-'.join(pendientes) or 'leer'}")
    for tipo, pestana in zip(t.tipos, pestanas):
        with pestana:
            d = detalles[tipo]
            _destino(tipo)
            if d["estado"] == "PENDIENTE":
                _editable(d, t, consentimiento, modo)
            else:
                _solo_lectura(d)
    _oci(detalles)


# ── La página ──

cliente = ui.exigir_cliente()
if st.session_state.pop("ir_a_contenido", False):
    st.session_state["dash_vista"] = "Contenido"  # la pestaña del dashboard que se abre
    st.switch_page("paginas/dashboard.py")

estilo.encabezado_pagina("Borradores", "Cada logro trae dos textos: un post para LinkedIn y un caso de éxito para la "
                                       "web. Se revisan juntos.")
ui.mostrar_aviso()

try:
    respuesta = cliente.listar_con_modo("PENDIENTE", LIMITE)
    todos = (respuesta["borradores"] + cliente.listar_borradores(estado="APROBADO", limite=LIMITE)
             + cliente.listar_borradores(estado="RECHAZADO", limite=LIMITE))
except ErrorJava as e:
    st.error(e.mensaje)
    st.stop()
modo_linkedin = respuesta.get("linkedinModo")
por_revisar = len(logros.agrupar(todos, "PENDIENTE"))

estado = st.segmented_control(
    "Estado", list(ESTADOS), default="PENDIENTE", required=True, key="filtro_estado", label_visibility="collapsed",
    format_func=lambda k: f"Por revisar ({por_revisar})" if k == "PENDIENTE" else ESTADOS[k]) or "PENDIENTE"
cola = logros.agrupar(todos, estado)

aviso_reciente = st.session_state.pop("aviso_borradores", None)
claves = [t.clave for t in cola]
if aviso_reciente and aviso_reciente["clave"] not in claves:
    _aviso(aviso_reciente)  # la tarjeta ya salió de la cola: el aviso va arriba
    aviso_reciente = None
if not cola:
    st.info(VACIAS[estado])
    st.stop()

elegida = st.session_state.get("tarjeta_elegida")
if elegida not in claves:
    elegida = claves[0]
    st.session_state["tarjeta_elegida"] = elegida

col_cola, col_detalle = st.columns([1, 2.4], gap="medium")
with col_cola:
    _texto_suave("Del más antiguo al más nuevo" if estado == "PENDIENTE" else "Lo último revisado primero")
    for tarjeta in cola:
        _tarjeta_cola(tarjeta, estado, tarjeta.clave == elegida)
with col_detalle.container(key="bor-detalle", gap="medium"):
    actual = next(t for t in cola if t.clave == elegida)
    _detalle(actual, estado, modo_linkedin, aviso_reciente if aviso_reciente and aviso_reciente["clave"] == elegida else None)
