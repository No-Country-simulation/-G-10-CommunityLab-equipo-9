"""
Cliente de ChromaDB para registro de interacciones.

Guarda pregunta + respuesta + metadata para detección futura
de preguntas repetidas. Falla silenciosamente si ChromaDB no está
instalado o configurado.
"""
from __future__ import annotations
from datetime import datetime

from ..config import RUTA_CHROMA, CHROMA_COLLECTION_INTERACCIONES


class ChromaClient:
    """Registra interacciones en ChromaDB."""

    def __init__(self):
        self.client = None
        self.collection = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import chromadb

            RUTA_CHROMA.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(RUTA_CHROMA))
            self.collection = self.client.get_or_create_collection(
                name=CHROMA_COLLECTION_INTERACCIONES,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"[ChromaClient] Inicializado en {RUTA_CHROMA}")
        except Exception as e:
            print(f"[ChromaClient] No se pudo inicializar: {e}")
            self.client = None
            self.collection = None

    def registrar_interaccion(
        self,
        mensaje_id: str,
        intencion: str,
        output: dict,
        metadata: dict,
    ) -> None:
        """Registra una interacción procesada."""
        if not self.collection:
            return

        # Texto base para embedding
        texto = (
            output.get("texto_respuesta")
            or output.get("respuesta")
            or str(output)
        )[:2000]  # Limitar tamaño

        try:
            self.collection.add(
                ids=[mensaje_id],
                documents=[texto],
                metadatas=[{
                    "intencion": intencion,
                    "timestamp": datetime.utcnow().isoformat(),
                    "tiempo_ms": metadata.get("tiempo_ms", 0),
                }],
            )
        except Exception as e:
            print(f"[ChromaClient] Error registrando {mensaje_id}: {e}")

    def buscar_similares(self, texto: str, top_k: int = 5) -> dict:
        """Busca interacciones similares."""
        if not self.collection:
            return {"ids": [], "distances": [], "metadatas": []}
        try:
            return self.collection.query(query_texts=[texto], n_results=top_k)
        except Exception as e:
            print(f"[ChromaClient] Error en búsqueda: {e}")
            return {"ids": [], "distances": [], "metadatas": []}