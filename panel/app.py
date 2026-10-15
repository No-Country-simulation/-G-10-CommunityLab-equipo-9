"""
Panel de curaduría de CommunityLab (T07, N6, OE6).

Una persona de Marketing entra con su usuario y su contraseña, y revisa los borradores de la IA:
los edita, los aprueba o los rechaza. El panel habla solo con la API Java (DEC-112).

    streamlit run app.py        (desde panel/; en Docker lo levanta compose.yml en 127.0.0.1:8501)

Páginas (DEC-114), en paginas/: Borradores (T07, rehecha en T13), Dashboard (T08 y T12) y Errores (T07).

Barra lateral (T13, como el prototipo): "CommunityLab · Panel de curaduría" (el título del panel va aquí, no arriba
de cada página), la navegación con el número de tarjetas por revisar y la sesión. Streamlit dibuja su navegación
arriba de todo lo demás de la barra lateral: por eso va oculta (position="hidden") y la reemplazan st.page_link
propios, que se dibujan en el orden en que se llaman.
"""
from __future__ import annotations

import logging
import os
import time

import streamlit as st

import auth
import estilo
import logros
import ui
from cliente_java import ErrorJava

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("panel")

# Una sesión sin uso durante 8 horas se cierra sola
SESION_MAX_INACTIVA_S = 8 * 3600

st.set_page_config(page_title="CommunityLab | Curaduría", layout="wide")
st.markdown(ui.ESTILOS, unsafe_allow_html=True)  # solo los estilos fijos de ui.py, nunca datos
st.html(estilo.ESTILOS)  # los estilos fijos de las páginas y de la barra lateral (T12 y T13), nunca datos


@st.cache_resource
def _control_intentos() -> auth.ControlIntentos:
    """Uno por proceso: los fallos se cuentan aunque se abra otra pestaña."""
    return auth.ControlIntentos()


def _iniciar_sesion() -> None:
    st.title("CommunityLab · Panel de curaduría")
    usuarios = auth.leer_usuarios(os.environ.get("PANEL_USUARIOS"))
    if not usuarios:
        st.error("El panel no tiene usuarios configurados, así que nadie puede entrar. "
                 "Crea uno con `python scripts/crear_usuario_panel.py` y reinicia el panel.")
        st.stop()

    with st.form("inicio_sesion"):
        st.subheader("Iniciar sesión")
        usuario = st.text_input("Usuario", key="login_usuario")
        contrasena = st.text_input("Contraseña", type="password", key="login_contrasena")
        entrar = st.form_submit_button("Entrar", type="primary")
    if not entrar:
        st.stop()

    usuario = usuario.strip()
    control = _control_intentos()
    if control.bloqueado(usuario):
        st.error("Demasiados intentos fallidos con este usuario. Espera unos minutos.")
        st.stop()
    if auth.verificar(usuarios, usuario, contrasena):
        control.exito(usuario)
        st.session_state["usuario"] = usuario
        st.session_state["ultimo_uso"] = time.monotonic()
        log.info("Inicio de sesión: %s", usuario)
        st.rerun()
    control.fallo(usuario)
    # Sin el usuario en el registro: alguien podría escribir su contraseña en ese campo por error
    log.warning("Intento de inicio de sesión fallido")
    time.sleep(auth.PAUSA_FALLO_S)
    st.error("Usuario o contraseña incorrectos.")
    st.stop()


def _cerrar_sesion() -> None:
    st.session_state.clear()


def _etiqueta_borradores() -> str:
    """"Borradores" con el número de tarjetas por revisar (un número: no es un dato de un alumno)."""
    cliente = ui.obtener_cliente()
    if cliente is None:
        return "Borradores"
    try:
        n = logros.contar_por_revisar(cliente.listar_borradores(estado="PENDIENTE", limite=500))
    except ErrorJava:
        return "Borradores"  # la página Borradores dirá qué pasó
    return f"Borradores :gray-badge[{n}]" if n else "Borradores"


# Sesión vencida por inactividad
if "usuario" in st.session_state:
    if time.monotonic() - st.session_state.get("ultimo_uso", 0) > SESION_MAX_INACTIVA_S:
        _cerrar_sesion()
        st.info("La sesión se cerró por inactividad. Vuelve a entrar.")
    else:
        st.session_state["ultimo_uso"] = time.monotonic()

if "usuario" not in st.session_state:
    _iniciar_sesion()

pagina = st.navigation([
    st.Page("paginas/borradores.py", title="Borradores", default=True),
    st.Page("paginas/dashboard.py", title="Dashboard"),
    st.Page("paginas/errores.py", title="Errores"),
], position="hidden")

with st.sidebar:
    # Textos fijos, en markdown: el tamaño lo ponen las reglas nav-* de estilo.ESTILOS
    with st.container(key="nav-titulo", gap=None):
        st.markdown("**CommunityLab**")
    with st.container(key="nav-subtitulo", gap=None):
        st.markdown("Panel de curaduría")
    st.page_link("paginas/borradores.py", label=_etiqueta_borradores(), icon=":material/edit_note:")
    st.page_link("paginas/dashboard.py", label="Dashboard", icon=":material/bar_chart:")
    st.page_link("paginas/errores.py", label="Errores", icon=":material/error_outline:")
    st.text(f"Sesión: {ui.usuario_actual()}")
    st.button("Cerrar sesión", on_click=_cerrar_sesion)

pagina.run()
