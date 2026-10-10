"""
Piezas comunes de las páginas del panel: estilos, cliente de Java, fechas y cómo mostrar textos.

Seguridad de lo que se muestra (S11 y T07 §11): los textos de alumnos y de la IA van SIEMPRE con
mostrar_texto() o st.text(), que los muestran tal cual (escapados). Nunca dentro de st.markdown()
ni con unsafe_allow_html: un mensaje con HTML o un enlace engañoso se vería como texto, no se ejecutaría.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import cliente_java

# El diseño del panel que estaba en main (DEC-109): botón índigo y tarjetas redondeadas.
# Son estilos fijos: aquí nunca entra un dato
ESTILOS = """
    <style>
    button[kind="primary"], button[kind="primaryFormSubmit"] {
        background-color: #4f46e5 !important; /* Color indigo moderno */
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
        background-color: #4338ca !important;
        transform: translateY(-2px);
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid #374151 !important;
    }
    </style>
"""

TIPOS = {
    "POST_LINKEDIN": "Post de LinkedIn",
    "CASO_EXITO": "Caso de éxito",
    "FAQ": "FAQ semanal",
}

ESTADOS = {
    "Pendientes": "PENDIENTE",
    "Aprobados": "APROBADO",
    "Rechazados": "RECHAZADO",
}

ZONA = ZoneInfo(os.environ.get("PANEL_ZONA", "America/Bogota"))


@st.cache_resource
def _cliente_cacheado(url: str, clave: str) -> cliente_java.ClienteJava:
    return cliente_java.ClienteJava(url, clave)


def obtener_cliente() -> cliente_java.ClienteJava | None:
    """El cliente de Java, o None si falta API_KEY_PANEL. Uno por proceso (comparte conexiones)."""
    clave = os.environ.get("API_KEY_PANEL", "").strip()
    if not clave:
        return None
    return _cliente_cacheado(os.environ.get("PANEL_JAVA_URL", "http://localhost:8008"), clave)


def usuario_actual() -> str:
    return st.session_state["usuario"]


def fecha(iso: str | None) -> str:
    """Una fecha ISO de Java en la hora local del equipo (Bogotá), corta y legible."""
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZONA).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return "—"


_ESTADOS_OCI = {
    "SUBIDO": "✅ subido",
    "PENDIENTE": "⏳ pendiente (se sube en segundo plano)",
    "ERROR": "❌ error (revisar con quien administra el servidor)",
    None: "— todavía no",
}


def lineas_oci(oci: dict | None, estado_borrador: str) -> list[str]:
    """
    Si el borrador ya está en OCI (T09), una línea por carpeta. Solo el estado: Java nunca manda la ruta
    ni la URL PAR. A aprobados/ solo va lo aprobado (F11): en lo demás no se menciona.
    """
    oci = oci or {}
    lineas = [f"generados/: {_ESTADOS_OCI.get(oci.get('generados'), str(oci.get('generados')))}"]
    if estado_borrador == "APROBADO":
        lineas.append(f"aprobados/: {_ESTADOS_OCI.get(oci.get('aprobados'), str(oci.get('aprobados')))}")
    return lineas


def mostrar_texto(texto: str | None) -> None:
    """Un texto de un alumno o de la IA, tal cual y sin interpretar (ni HTML ni markdown)."""
    st.code(texto if texto else "(sin texto)", language=None, wrap_lines=True)


def avisar(tipo: str, texto: str) -> None:
    """Un aviso para mostrar después del st.rerun() (por ejemplo, "Borrador aprobado")."""
    st.session_state["aviso"] = (tipo, texto)


def mostrar_aviso() -> None:
    aviso = st.session_state.pop("aviso", None)
    if aviso:
        tipo, texto = aviso
        (st.success if tipo == "ok" else st.warning)(texto)


def exigir_cliente() -> cliente_java.ClienteJava:
    cliente = obtener_cliente()
    if cliente is None:
        st.error("Falta API_KEY_PANEL: créala con `python scripts/generar_api_key.py --cliente panel` "
                 "y reinicia el panel.")
        st.stop()
    return cliente
