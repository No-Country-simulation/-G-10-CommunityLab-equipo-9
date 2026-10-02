"""
Configuración de cargadores de PDF de la documentación y segmentación en chunks.
"""
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..config import RUTA_PDFS, CHUNK_SIZE, CHUNK_OVERLAP
from .embedding_models import requiere_prefijo_e5


def cargar_pdfs(ruta: Path = RUTA_PDFS) -> list:
    """Carga todos los PDFs de una carpeta."""
    if not ruta.exists():
        raise FileNotFoundError(f"Carpeta no encontrada: {ruta}")

    documentos = []
    for pdf in ruta.glob("*.pdf"):
        try:
            loader = PyPDFLoader(str(pdf))
            documentos.extend(loader.load())
        except Exception as e:
            print(f"[loader] Error cargando {pdf.name}: {e}")

    if not documentos:
        raise ValueError(f"No se cargaron PDFs desde {ruta}")

    print(f"[loader] {len(documentos)} páginas cargadas desde {len(list(ruta.glob('*.pdf')))} PDFs.")
    return documentos


def fragmentar_documentos(documentos: list) -> list:
    """Divide los documentos en chunks y aplica prefijo E5 si es necesario."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    fragmentos = splitter.split_documents(documentos)

    if requiere_prefijo_e5():
        for doc in fragmentos:
            if not doc.page_content.startswith("passage: "):
                doc.page_content = f"passage: {doc.page_content}"

    print(f"[loader] {len(fragmentos)} fragmentos generados.")
    return fragmentos
