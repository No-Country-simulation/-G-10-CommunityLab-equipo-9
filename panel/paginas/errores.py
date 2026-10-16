"""
Página "Errores" (T07, DEC-111): lo que quedó en ERROR y su botón de reintentar.

- Clasificación (T04): el mensaje vuelve a PENDIENTE con sus intentos en 0; lo toma la vuelta siguiente (30 s).
- Generación (T06): el logro vuelve a "sin generar"; lo toma la vuelta siguiente (60 s). Gasta una llamada a Gemini.
- FAQ semanal (T13, DEC-161): la semana vuelve a la cola y Java la arma enseguida, en segundo plano. Tarda hasta
  unos minutos y gasta una llamada a Gemini.
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

with st.container(border=True):
    st.subheader("FAQ semanal en ERROR")
    st.text("La IA no pudo armar la FAQ de estas semanas después de varios intentos. Reintentar la arma enseguida, "
            "en segundo plano, y gasta una llamada a Gemini.")
    semanas = errores.get("faq") or []
    if not semanas:
        st.success("No hay nada en ERROR.")
    for s in semanas:
        with st.container(border=True):
            st.text(f"Semana {s['semana']} · del {ui.fecha(s.get('desde'))} al {ui.fecha(s.get('hasta'))} · "
                    f"{s.get('intentos')} intentos")
            if s.get("motivo"):
                st.text(f"Último error: {s['motivo']}")
            if st.button("Reintentar", key=f"reintentar_faq_{s['semana']}"):
                try:
                    cliente.reintentar_faq(s["semana"], ui.usuario_actual())
                except (ErrorJava, ValueError) as e:
                    st.warning(getattr(e, "mensaje", str(e)))
                else:
                    ui.avisar("ok", f"La FAQ de la semana {s['semana']} se está armando: tarda hasta unos minutos. "
                                    f"Cuando esté, aparece en Borradores.")
                    st.rerun()
