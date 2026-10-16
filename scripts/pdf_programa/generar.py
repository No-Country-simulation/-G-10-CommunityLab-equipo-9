"""
Genera el PDF 13 del Agente FAQ, "Programa del bootcamp de CommunityLab", a partir de su texto en Markdown (T15).

El texto vive en `13_Programa_del_Bootcamp_CommunityLab.md`, junto a este script: para cambiar el PDF se cambia
ese archivo y se vuelve a generar. El formato imita al PDF 12: título, una línea de introducción, títulos de sección
y cada pregunta en negrita con su respuesta debajo. Sin tablas.

Se corre en un contenedor desechable de Python, sin instalar nada en la máquina (PowerShell, desde la raíz):
    docker run --rm -v "${PWD}:/repo" -w /repo python:3.12-slim sh -c "pip install -q fpdf2==2.8.3 && python scripts/pdf_programa/generar.py"

Escribe agents/agent_faq/data/pdfs/13_Programa_del_Bootcamp_CommunityLab.pdf (o la ruta que se pase como argumento).
Después hay que rehacer el índice del Agente FAQ y pasar scripts/revisar_buscador_faq.py (OPERACION.md §14).
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parents[1]
FUENTE = CARPETA / "13_Programa_del_Bootcamp_CommunityLab.md"
SALIDA = RAIZ / "agents" / "agent_faq" / "data" / "pdfs" / "13_Programa_del_Bootcamp_CommunityLab.pdf"

ENCABEZADO = "COMMUNITYLAB · PROGRAMA DEL BOOTCAMP"
PIE = "Programa del bootcamp · Página {n}"
# Fecha fija: el mismo texto da siempre el mismo PDF
FECHA = datetime(2026, 10, 16, tzinfo=timezone.utc)

# Helvetica es una fuente de fábrica del PDF: solo admite latin-1 (tildes, ñ, ¿ y · sí; raya larga y emojis no)
FUENTE_PDF = "Helvetica"
# Espacio mínimo (mm) para empezar una pregunta: si no cabe con su respuesta, pasa a la página siguiente
ESPACIO_PREGUNTA = 22


class PdfPrograma(FPDF):
    def header(self):
        self.set_font(FUENTE_PDF, "B", 8)
        self.set_text_color(90, 90, 90)
        self.cell(0, 5, ENCABEZADO, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font(FUENTE_PDF, "", 8)
        self.set_text_color(90, 90, 90)
        self.cell(0, 10, PIE.format(n=self.page_no()), align="C")


def leer_bloques(texto: str) -> list[tuple[str, str]]:
    """Convierte el Markdown en bloques (tipo, texto): titulo, intro, seccion, pregunta y respuesta."""
    bloques = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith("## "):
            bloques.append(("seccion", linea[3:]))
        elif linea.startswith("# "):
            bloques.append(("titulo", linea[2:]))
        elif linea.startswith("**") and linea.endswith("**"):
            bloques.append(("pregunta", linea[2:-2]))
        elif bloques and bloques[-1][0] == "pregunta":
            bloques.append(("respuesta", linea))
        else:
            bloques.append(("intro", linea))
    return bloques


def revisar_caracteres(texto: str) -> None:
    """Falla antes de generar si hay caracteres que Helvetica no puede mostrar."""
    fuera = sorted({c for c in texto if ord(c) > 255})
    if fuera:
        raise SystemExit(f"Caracteres fuera de latin-1 en {FUENTE.name}: {' '.join(fuera)}")


def generar(salida: Path) -> None:
    texto = FUENTE.read_text(encoding="utf-8")
    revisar_caracteres(texto + ENCABEZADO + PIE)
    bloques = leer_bloques(texto)
    titulo = next(t for tipo, t in bloques if tipo == "titulo")

    pdf = PdfPrograma(format="A4")
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(True, margin=22)
    pdf.set_title(titulo)
    pdf.set_author("CommunityLab")
    pdf.set_subject("Qué se estudia en el bootcamp, módulo por módulo")
    pdf.set_creation_date(FECHA)
    pdf.add_page()

    for tipo, contenido in bloques:
        if tipo == "titulo":
            pdf.set_font(FUENTE_PDF, "B", 17)
            pdf.multi_cell(0, 8, contenido, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
        elif tipo == "intro":
            pdf.set_font(FUENTE_PDF, "", 10.5)
            pdf.multi_cell(0, 5.5, contenido, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        elif tipo == "seccion":
            if pdf.get_y() + ESPACIO_PREGUNTA + 12 > pdf.page_break_trigger:
                pdf.add_page()
            pdf.ln(5)
            pdf.set_font(FUENTE_PDF, "B", 13)
            pdf.multi_cell(0, 7, contenido, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
        elif tipo == "pregunta":
            if pdf.get_y() + ESPACIO_PREGUNTA > pdf.page_break_trigger:
                pdf.add_page()
            pdf.ln(2)
            pdf.set_font(FUENTE_PDF, "B", 10.5)
            pdf.multi_cell(0, 5.5, contenido, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.set_font(FUENTE_PDF, "", 10.5)
            pdf.multi_cell(0, 5.5, contenido, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    salida.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(salida))
    print(f"PDF generado: {salida} ({pdf.page_no()} páginas)")


if __name__ == "__main__":
    generar(Path(sys.argv[1]) if len(sys.argv) > 1 else SALIDA)
