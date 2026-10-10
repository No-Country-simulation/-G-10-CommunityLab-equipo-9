"""
Página "Errores" (T07, DEC-111): lo que quedó en ERROR y su botón de reintentar.

- Clasificación (T04): el mensaje vuelve a PENDIENTE con sus intentos en 0; lo toma la vuelta siguiente (30 s).
- Generación (T06): el logro vuelve a "sin generar"; lo toma la vuelta siguiente (60 s). Gasta una llamada a Gemini.
"""
from __future__ import annotations

import streamlit as st

import ui
from cliente_java import ErrorJava

cliente = ui.exigir_cliente()
ui.mostrar_aviso()

try:
    errores = cliente.errores()
except ErrorJava as e:
    st.error(e.mensaje)
    st.stop()

ETAPAS = (
    ("clasificacion", "Clasificación en ERROR",
     "La IA no pudo etiquetar estos mensajes después de varios intentos."),
    ("generacion", "Generación de borradores en ERROR",
     "El Agente-Mod no pudo redactar el post y el caso de éxito de estos logros. Reintentar gasta una llamada a Gemini."),
)

for etapa, titulo, explicacion in ETAPAS:
    lista = errores.get(etapa) or []
    with st.container(border=True):
        st.subheader(titulo)
        st.text(explicacion)
        if not lista:
            st.success("No hay nada en ERROR.")
            continue
        for m in lista:
            with st.container(border=True):
                st.text(f"Mensaje {m['mensajeId']} · #{m.get('canal') or '—'} · {ui.fecha(m.get('fecha'))} · "
                        f"{m.get('autorNombre') or '—'} · {m.get('intentos')} intentos")
                ui.mostrar_texto(m.get("extracto"))
                if m.get("motivo"):
                    st.text(f"Último error: {m['motivo']}")
                if st.button("Reintentar", key=f"reintentar_{etapa}_{m['mensajeId']}"):
                    try:
                        cliente.reintentar(etapa, m["mensajeId"], ui.usuario_actual())
                    except ErrorJava as e:
                        st.warning(e.mensaje)
                    else:
                        ui.avisar("ok", f"Mensaje {m['mensajeId']} devuelto a la cola: se procesa en la próxima vuelta.")
                        st.rerun()
