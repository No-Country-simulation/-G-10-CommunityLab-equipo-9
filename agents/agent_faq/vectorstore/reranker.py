"""
Reranking local con Cross-Encoder para mejorar precisión del RAG.
"""
from sentence_transformers import CrossEncoder
from ..config import RERANKER_MODEL, TOP_N_RERANK


class Reranker:
    """Wrapper del Cross-Encoder para reranking de documentos."""

    def __init__(self):
        print(f"[reranker] Cargando modelo {RERANKER_MODEL}...")
        self.model = CrossEncoder(RERANKER_MODEL, max_length=512)

    def rerank(self, query: str, documentos: list, top_n: int = TOP_N_RERANK) -> list:
        """Reordena documentos por relevancia semántica real."""
        if not documentos:
            return []

        pares = [
            [query, doc.page_content.replace("passage: ", "").strip()]
            for doc in documentos
        ]
        scores = self.model.predict(pares)

        documentos_con_score = list(zip(documentos, scores))
        documentos_con_score.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, _ in documentos_con_score[:top_n]]

    def ensamblar_contexto(self, documentos: list) -> tuple[str, list[str]]:
        """Construye el bloque de contexto y extrae citaciones."""
        if not documentos:
            return "No hay contexto disponible.", []

        contexto = ""
        citaciones = []
        for idx, doc in enumerate(documentos, 1):
            fuente = (
                doc.metadata.get("source", "Desconocido").split("/")[-1]
                if "source" in doc.metadata
                else "Documento"
            )
            pagina = doc.metadata.get("page")
            citacion = f"{fuente} (Pág. {pagina + 1})" if pagina is not None else fuente
            citaciones.append(citacion)

            contenido = doc.page_content.replace("passage: ", "").strip()
            contexto += f"--- [RECURSO {idx} | Fuente: {citacion}] ---\n{contenido}\n\n"

        return contexto, citaciones