"""
Vectorstore separado para detectar preguntas repetidas.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import threading

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from ..config import (
    RUTA_FAISS_PREGUNTAS,
    RUTA_HISTORIAL_PREGUNTAS,
    TOP_K_PREGUNTAS,
    FAQ_UMBRAL_PREGUNTA_REPETIDA,
)
from .embedding_models import select_embeddings, requiere_prefijo_e5
from ..contratos import PreguntaSimilar


class PreguntasStore:
    """
    Gestiona el histórico de preguntas para detección de repeticiones.
    """

    def __init__(self):
        self.embeddings = select_embeddings()
        self.vectorstore: FAISS | None = None
        # El orquestador atiende pedidos en paralelo y la instancia es compartida:
        # FAISS y el historial JSON no admiten lecturas y escrituras simultáneas.
        self._lock = threading.Lock()
        self._cargar()

    def _cargar(self) -> None:
        if RUTA_FAISS_PREGUNTAS.exists():
            self.vectorstore = FAISS.load_local(
                str(RUTA_FAISS_PREGUNTAS),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            print(f"[preguntas_store] Índice cargado ({self.vectorstore.index.ntotal} preguntas).")
        else:
            print("[preguntas_store] Sin histórico previo. Se creará al primer registro.")

    def buscar_similares(self, pregunta: str) -> list[PreguntaSimilar]:
        """Busca preguntas previas similares."""
        query = f"query: {pregunta}" if requiere_prefijo_e5() else pregunta
        with self._lock:
            if not self.vectorstore:
                return []
            resultados = self.vectorstore.similarity_search_with_score(query, k=TOP_K_PREGUNTAS)

        similares = []
        for doc, score in resultados:
            # FAISS retorna distancia; convertir a similitud (aproximación)
            similitud = 1.0 / (1.0 + float(score))
            if similitud >= FAQ_UMBRAL_PREGUNTA_REPETIDA:
                similares.append(
                    PreguntaSimilar(
                        pregunta=doc.page_content.replace("passage: ", "").replace("query: ", "").strip(),
                        similitud=round(similitud, 4),
                        fecha=doc.metadata.get("fecha"),
                    )
                )
        return similares

    def registrar(self, pregunta: str, metadatos: dict | None = None) -> None:
        """Registra una nueva pregunta en el histórico."""
        contenido = f"passage: {pregunta}" if requiere_prefijo_e5() else pregunta
        metadata = {"fecha": datetime.utcnow().isoformat(), **(metadatos or {})}
        doc = Document(page_content=contenido, metadata=metadata)

        with self._lock:
            if self.vectorstore is None:
                self.vectorstore = FAISS.from_documents([doc], self.embeddings)
            else:
                self.vectorstore.add_documents([doc])

            RUTA_FAISS_PREGUNTAS.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(str(RUTA_FAISS_PREGUNTAS))

            # Backup JSON legible
            historial = []
            if RUTA_HISTORIAL_PREGUNTAS.exists():
                try:
                    historial = json.loads(RUTA_HISTORIAL_PREGUNTAS.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    historial = []
            historial.append({"pregunta": pregunta, **metadata})
            RUTA_HISTORIAL_PREGUNTAS.write_text(
                json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8"
            )