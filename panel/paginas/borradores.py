"""
Página "Borradores" (T07, N6): la lista de borradores y, al elegir uno, su contexto y las acciones.

- Lo pendiente se edita, se aprueba o se rechaza. Lo aprobado y lo rechazado solo se lee.
- Un post o un caso de éxito nombra al alumno: "Aprobar" queda apagado hasta marcar el consentimiento (D6).
  Java y la base lo exigen también: son tres capas.
- El tiempo de curaduría se mide desde que se abre el borrador en esta sesión.
"""
from __future__ import annotations

import time

import streamlit as st

import ui
from cliente_java import ErrorJava

cliente = ui.exigir_cliente()
ui.mostrar_aviso()

filtro_estado, filtro_tipo = st.columns(2)
estado_label = filtro_estado.radio("Estado", list(ui.ESTADOS), horizontal=True, key="filtro_estado")
tipo_label = filtro_tipo.selectbox("Tipo", ["Todos", *ui.TIPOS.values()], key="filtro_tipo")
estado = ui.ESTADOS[estado_label]
tipo = next((k for k, v in ui.TIPOS.items() if v == tipo_label), None)

try:
    todos = cliente.listar_borradores(estado=estado)
except ErrorJava as e:
    st.error(e.mensaje)
    st.stop()

# 1. CUADRO DE MÉTRICAS (el del panel viejo, ahora con los datos reales)
with st.container(border=True):
    st.subheader(f"Borradores {estado_label.lower()}")
    columnas = st.columns(4)
    columnas[0].metric("Total", len(todos))
    for columna, (clave, nombre) in zip(columnas[1:], ui.TIPOS.items()):
        columna.metric(nombre, sum(1 for b in todos if b["tipo"] == clave))

lista = [b for b in todos if tipo is None or b["tipo"] == tipo]
if not lista:
    st.info("No hay borradores con este filtro.")
    st.stop()


def _etiqueta(b: dict) -> str:
    # Sin nombres ni textos de alumnos: solo datos del sistema
    extra = f" · semana {b['semana']}" if b.get("semana") else ""
    return f"#{b['id']} · {ui.TIPOS.get(b['tipo'], b['tipo'])} · {ui.fecha(b['creadoEn'])}{extra}"


por_id = {b["id"]: b for b in lista}
borrador_id = st.selectbox("Borrador", list(por_id), format_func=lambda i: _etiqueta(por_id[i]), key="borrador_sel")

try:
    d = cliente.detalle(borrador_id)
except ErrorJava as e:
    st.error(e.mensaje)
    st.stop()

st.write("")

# 2. CUADROS DE EDICIÓN: a la izquierda, de dónde salió; a la derecha, el borrador
col_izq, col_der = st.columns(2)

with col_izq:
    with st.container(border=True):
        origen, faq = d.get("origen"), d.get("faq")
        if origen:
            st.subheader("Mensaje original")
            st.text(f"Autor: {origen.get('autorNombre') or '—'}")
            st.text(f"Canal: #{origen.get('canal') or '—'} · {ui.fecha(origen.get('fecha'))}")
            ui.mostrar_texto(origen.get("texto"))
        elif faq:
            st.subheader("Semana de la FAQ")
            st.text(f"Semana {faq.get('semana')}: del {ui.fecha(faq.get('desde'))} al {ui.fecha(faq.get('hasta'))}")
            st.text("Junta las dudas repetidas de la semana. Revisa que ninguna pregunta incluya el nombre de un alumno.")
        st.markdown("**Por qué lo propuso la IA**")
        ui.mostrar_texto(d.get("motivoIa"))
        # T09: si ya está guardado en OCI. Con st.text, no st.caption: así no cambia el orden de los avisos del botón
        st.markdown("**Guardado en OCI**")
        for linea in ui.lineas_oci(d.get("oci"), d["estado"]):
            st.text(linea)

with col_der:
    with st.container(border=True):
        st.subheader(ui.TIPOS.get(d["tipo"], d["tipo"]))
        texto_actual = d.get("textoFinal") or d["textoIa"]

        if d["estado"] != "PENDIENTE":
            st.text_area("Texto final", value=texto_actual, height=280, disabled=True, key=f"leer_{d['id']}")
            if d["estado"] == "APROBADO":
                st.text(f"Aprobado por {d.get('aprobadoPor')} el {ui.fecha(d.get('aprobadoEn'))}")
                consentimiento = "confirmado" if d.get("consentimientoConfirmado") else "no hacía falta"
                st.text(f"Revisión: {d.get('tiempoCuraduriaSeg')} s · consentimiento: {consentimiento}")
            else:
                st.text(f"Rechazado por {d.get('rechazadoPor')} el {ui.fecha(d.get('rechazadoEn'))}")
                if d.get("motivoRechazo"):
                    st.text("Motivo del rechazo:")
                    ui.mostrar_texto(d["motivoRechazo"])
            st.stop()

        # El tiempo de curaduría corre desde la primera vez que se abre este borrador en la sesión
        abiertos = st.session_state.setdefault("abiertos", {})
        abiertos.setdefault(d["id"], time.monotonic())

        texto = st.text_area("Texto del borrador (editable)", value=texto_actual, height=280, key=f"texto_{d['id']}")
        if d["requiereConsentimiento"]:
            consentimiento = st.checkbox(
                "El alumno dio su consentimiento para publicar su nombre y su historia (D6)",
                key=f"consentimiento_{d['id']}")
        else:
            consentimiento = False
            st.info("La FAQ no nombra alumnos: no necesita consentimiento.")

        boton_guardar, boton_aprobar = st.columns(2)
        guardar = boton_guardar.button("Guardar edición", key=f"guardar_{d['id']}", width="stretch")
        falta_consentimiento = d["requiereConsentimiento"] and not consentimiento
        aprobar = boton_aprobar.button("Aprobar", type="primary", key=f"aprobar_{d['id']}",
                                       disabled=falta_consentimiento, width="stretch")
        if falta_consentimiento:
            st.caption("Para aprobar, marca la casilla de consentimiento.")

        with st.expander("Rechazar este borrador"):
            motivo = st.text_input("Motivo (opcional)", max_chars=500, key=f"motivo_{d['id']}")
            rechazar = st.button("Rechazar", key=f"rechazar_{d['id']}")


def _segundos() -> int:
    return int(time.monotonic() - st.session_state["abiertos"].get(d["id"], time.monotonic()))


def _terminar(mensaje: str) -> None:
    st.session_state["abiertos"].pop(d["id"], None)
    ui.avisar("ok", mensaje)
    st.rerun()


# 3. ACCIONES (Java vuelve a revisar todo: estado PENDIENTE, consentimiento y quién gana si hay dos a la vez)
try:
    if guardar:
        cliente.editar(d["id"], ui.usuario_actual(), texto)
        ui.avisar("ok", "Edición guardada. Sigue pendiente de aprobación.")
        st.rerun()
    if aprobar:
        if falta_consentimiento:  # el botón ya está apagado; esto es por si acaso
            st.error("No se puede aprobar sin el consentimiento del alumno (D6).")
            st.stop()
        # Si el texto cambió respecto de lo guardado, la edición viaja en el mismo pedido que la aprobación
        editado = texto if texto != texto_actual else None
        cliente.aprobar(d["id"], ui.usuario_actual(), consentimiento, _segundos(), editado)
        _terminar(f"Borrador #{d['id']} aprobado.")
    if rechazar:
        cliente.rechazar(d["id"], ui.usuario_actual(), motivo.strip() or None, _segundos())
        _terminar(f"Borrador #{d['id']} rechazado.")
except ErrorJava as e:
    if e.estado == 409:
        st.warning(f"{e.mensaje} Actualiza la lista.")
    else:
        st.error(e.mensaje)
