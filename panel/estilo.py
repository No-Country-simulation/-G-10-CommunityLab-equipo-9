"""
Las piezas de diseño comunes del panel (T12, movidas aquí en T13): colores, estilos, íconos, bloques de HTML,
fechas relativas y recortes. Las usan el Dashboard y Borradores, para que todo el panel se vea igual.

Tema claro y oscuro (DEC-156): al cambiar el tema en el menú, Streamlit NO vuelve a correr la página. Por eso aquí
no se elige ningún color según el tema: los bloques heredan el color del texto y usan fondos semitransparentes.

Seguridad de lo que se muestra (DEC-158): los bloques de HTML (st.html) llevan SOLO números y textos fijos del
panel, siempre pasados por e() (html.escape). Los nombres y los textos de los alumnos y de la IA NUNCA van en HTML
ni en markdown: van con st.text, st.text_area, st.dataframe o ui.mostrar_texto, que los escapan. Para darles tamaño
o peso, se ponen en un st.container(key=…) y una regla fija de ESTILOS los alcanza por esa clave.
"""
from __future__ import annotations

import html
from datetime import date, datetime

import streamlit as st

import ui

# Colores que se leen en los dos temas (🧪 validados contra el fondo claro #ffffff y el oscuro #0e1117)
SERIE = "#3987e5"                       # una sola serie: temas, activos, embudo y aprobados por semana
PISTA = "rgba(57, 135, 229, 0.22)"      # lo que falta para llegar al total
BORDE = "rgba(128, 128, 128, 0.28)"
FONDO_TARJETA = "rgba(128, 128, 128, 0.05)"
FONDO_FRANJA = "rgba(57, 135, 229, 0.09)"
FONDO_ETIQUETA = "rgba(128, 128, 128, 0.14)"  # las etiquetas redondas ("Post + caso de éxito")
ESPERA = "#d18f0c"
ALERTA = "#e0524a"
SUAVE = "opacity: 0.72"                 # el texto secundario: el color del tema, más tenue

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Dónde se usa cada tipo una vez aprobado (M11)
DESTINOS = {
    "POST_LINKEDIN": "LinkedIn de CommunityLab",
    "CASO_EXITO": "Web y presentaciones a empresas",
    "FAQ": "Canal #anuncios y la web",
}
TIPOS_PLURAL = {"POST_LINKEDIN": ("post", "posts"), "CASO_EXITO": ("caso de éxito", "casos de éxito"),
                "FAQ": ("FAQ", "FAQ")}

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

# Los estilos fijos del panel. Nunca llevan datos. dash-*: el Dashboard (T12); bor-*: Borradores (T13);
# nav-*: la barra lateral (T13)
ESTILOS = f"""<style>
[class*="st-key-dash-tarjeta"], [class*="st-key-dash-seccion"] {{
    border: 1px solid {BORDE}; border-radius: 10px; padding: 16px 18px; background: {FONDO_TARJETA};
}}
[class*="st-key-dash-franja"] {{ background: {FONDO_FRANJA}; border-radius: 12px; padding: 16px 20px; }}
[class*="st-key-dash-caso"] {{ border-top: 1px solid {BORDE}; padding-top: 10px; }}
[class*="st-key-dash-caso"] [data-testid="stText"] {{ font-size: 15px; }}
[class*="st-key-dash-meta"] [data-testid="stText"] {{ {SUAVE}; font-size: 14px; }}
[class*="st-key-dash-nombre"] [data-testid="stText"] {{ font-weight: 600; }}
[class*="st-key-dash-oci"] {{
    border: 1px solid {BORDE}; border-radius: 8px; padding: 12px 14px; background: {FONDO_TARJETA};
}}

[class*="st-key-nav-titulo"] p {{ margin: 0; }}
[class*="st-key-nav-titulo"] [data-testid="stMarkdownContainer"] p strong {{ font-size: 19px; font-weight: 700; }}
[class*="st-key-nav-subtitulo"] p {{ margin: 0; font-size: 14px; {SUAVE}; }}

[class*="st-key-bor-tarjeta"], [class*="st-key-bor-elegida"] {{
    position: relative; border: 1px solid {BORDE}; border-radius: 10px; padding: 14px 16px;
}}
[class*="st-key-bor-elegida"] {{ border: 2px solid currentColor; padding: 13px 15px; }}
[class*="st-key-bor-tarjeta"]:has(button:hover) {{ border-color: rgba(128, 128, 128, 0.6); }}
[class*="st-key-bor-tarjeta"]:has(button:focus-visible), [class*="st-key-bor-elegida"]:has(button:focus-visible) {{
    outline: 2px solid {SERIE}; outline-offset: 2px;
}}
/* Toda la tarjeta es el botón: el botón (transparente) la cubre entera, encima de sus textos */
[class*="st-key-bor-tarjeta"] [class*="st-key-abrir"], [class*="st-key-bor-elegida"] [class*="st-key-abrir"] {{
    position: absolute; inset: 0; z-index: 1; margin: 0;
}}
[class*="st-key-abrir"] button {{ width: 100%; height: 100%; opacity: 0; cursor: pointer; }}
[class*="st-key-bor-nombre"] [data-testid="stText"] {{ font-size: 16px; font-weight: 600; }}
[class*="st-key-bor-resumen"] [data-testid="stText"] {{ font-size: 15px; }}
[class*="st-key-bor-detalle"] {{ border: 1px solid {BORDE}; border-radius: 12px; padding: 24px; }}
[class*="st-key-bor-titulo"] [data-testid="stText"] {{ font-size: 24px; font-weight: 700; line-height: 1.25; }}
[class*="st-key-bor-meta"] [data-testid="stText"] {{ {SUAVE}; font-size: 14px; }}
[class*="st-key-bor-caja"] {{ background: {FONDO_TARJETA}; border-radius: 10px; padding: 14px 16px; }}
[class*="st-key-bor-caja"] [data-testid="stText"] {{ font-size: 15px; line-height: 1.45; }}
[class*="st-key-bor-consentimiento"] {{ border-top: 1px solid {BORDE}; padding-top: 16px; }}
[class*="st-key-bor-rechazar"] button {{
    border: none; background: transparent; color: {ALERTA}; text-decoration: underline;
}}
[class*="st-key-bor-lectura"] [data-testid="stText"] {{ font-size: 14px; }}
[class*="st-key-bor-destino"] p {{ margin: 0; font-size: 15px; }}
/* Un botón principal apagado (Aprobar sin consentimiento): gris, como en el prototipo. El índigo de ui.ESTILOS
   (DEC-109) lo pintaba igual que uno encendido, con el texto casi invisible */
button[kind="primary"]:disabled {{
    background-color: {FONDO_ETIQUETA} !important; color: inherit !important; opacity: 0.55;
    transform: none !important;
}}
</style>"""


def e(valor) -> str:
    """Todo lo que entra en un bloque HTML pasa por aquí (DEC-158)."""
    return html.escape(str(valor))


def dia(d: date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


def hace(iso: str | None) -> str:
    """Cuánto pasó desde una fecha de Java, en días."""
    if not iso:
        return "—"
    dias = (datetime.now(ui.ZONA) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    return "hoy" if dias < 1 else ("hace 1 día" if dias == 1 else f"hace {dias} días")


def corto(texto: str | None, largo: int = 240) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"


# ── Piezas de HTML (solo números y textos del panel, DEC-158). Heredan el color del tema ──

def bloque(cuerpo: str) -> None:
    st.html(f'<div style="font-family: inherit; color: inherit">{cuerpo}</div>')


def seccion(titulo_: str, subtitulo: str | None = None) -> None:
    """Separa las partes de una página (indicadores, gráficos, listas) con una línea y un título."""
    sub = f'<p style="margin: 2px 0 0; font-size: 15px; {SUAVE}">{e(subtitulo)}</p>' if subtitulo else ""
    bloque(f'<div style="border-top: 1px solid {BORDE}; margin-top: 18px; padding-top: 18px">'
           f'<h2 style="margin: 0; font-size: 22px; font-weight: 700">{e(titulo_)}</h2>{sub}</div>')


def titulo(titulo_: str, subtitulo: str | None = None) -> None:
    sub = f'<p style="margin: 2px 0 0; font-size: 15px; {SUAVE}">{e(subtitulo)}</p>' if subtitulo else ""
    bloque(f'<h3 style="margin: 0; font-size: 19px; font-weight: 600">{e(titulo_)}</h3>{sub}')


def nota(texto: str) -> None:
    bloque(f'<div style="font-size: 13px; {SUAVE}">{e(texto)}</div>')


def tarjeta(etiqueta: str, valor: str, linea: str | None = None, nota_: str | None = None, extra: str = "") -> str:
    """Una tarjeta del prototipo: etiqueta, número grande, una línea y una nota. extra: HTML ya escapado."""
    partes = [f'<div style="font-size: 15px; {SUAVE}">{e(etiqueta)}</div>',
              f'<div style="font-size: 30px; font-weight: 600; line-height: 1.15">{e(valor)}</div>', extra]
    if linea:
        partes.append(f'<div style="font-size: 14px">{e(linea)}</div>')
    if nota_:
        partes.append(f'<div style="font-size: 13px; {SUAVE}">{e(nota_)}</div>')
    return '<div style="display: flex; flex-direction: column; gap: 6px">' + "".join(partes) + "</div>"


def encabezado_lista(icono: str, titulo_: str) -> None:
    bloque(f'<div style="display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 17px">'
           f'{icono}{e(titulo_)}</div>')


def encabezado_pagina(titulo_: str, frase: str | None = None) -> None:
    """El título de una página y su frase (T13: Borradores; el Dashboard tiene el suyo)."""
    sub = f'<p style="margin: 4px 0 0; font-size: 17px; {SUAVE}">{e(frase)}</p>' if frase else ""
    bloque(f'<h1 style="margin: 0; font-size: 32px; font-weight: 700">{e(titulo_)}</h1>{sub}')
