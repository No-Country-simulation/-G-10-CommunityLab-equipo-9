"""Gestión del vectorstore FAISS para PDFs institucionales."""
from pathlib import Path
from langchain_community.vectorstores import FAISS
from ..config import RUTA_FAISS_PDFS, TOP_K_RETRIEVAL
from .embedding_models import select_embeddings
from .loader import cargar_pdfs, fragmentar_documentos


class StorePDFs:
    """Wrapper para el vectorstore de PDFs."""

    def __init__(self):
        self.embeddings = build_embeddings()
        self.vectorstore: FAISS | None = None
        self.retriever = None

    def construir(self, forzar_reindexado: bool = False) -> None:
        """Construye o carga el índice FAISS."""
        if RUTA_FAISS_PDFS.exists() and not forzar_reindexado:
            print(f"[store] Cargando índice existente desde {RUTA_FAISS_PDFS}")
            self.vectorstore = FAISS.load_local(
                str(RUTA_FAISS_PDFS),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        else:
            print("[store] Construyendo índice desde cero...")
            documentos = cargar_pdfs()
            fragmentos = fragmentar_documentos(documentos)
            self.vectorstore = FAISS.from_documents(fragmentos, self.embeddings)
            RUTA_FAISS_PDFS.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(str(RUTA_FAISS_PDFS))
            print(f"[store] Índice guardado en {RUTA_FAISS_PDFS}")

        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": TOP_K_RETRIEVAL}
        )

    def buscar(self, query: str) -> list:
        """Recupera candidatos del vectorstore."""
        if not self.retriever:
            raise RuntimeError("El store no ha sido construido. Llama a .construir() primero.")
        return self.retriever.invoke(query)