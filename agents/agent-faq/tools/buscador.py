"""
Tool 'Buscador': RAG + Rerank + Guardrail anti-alucinación.
"""

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..config import (
    UMBRAL_SIMILITUD_RAG, UMBRAL_FIDELIDAD,
)
from ..contratos import EvaluacionFidelidad, BuscadorOutput
from ..prompts.prompts import PROMPT_RAG_FAQ, PROMPT_GUARDRAIL
from ..vectorstore.store import StorePDFs
from ..vectorstore.reranker import Reranker


class BuscadorTool:
    """
    Logica de herramienta 'Buscador'.
    """

    def __init__(self, store: StorePDFs, reranker: Reranker, llm):
        self.store = store
        self.reranker = reranker
        self.llm = llm
        self.rag_chain = (
            ChatPromptTemplate.from_template(PROMPT_RAG_FAQ)
            | llm
            | StrOutputParser()
        )
        self.guardrail = llm.with_structured_output(EvaluacionFidelidad)

    def ejecutar(self, pregunta: str) -> dict:
        """
        Ejecuta la búsqueda RAG completa con rerank y guardrail.
        """
        # 1. Retrieval amplio
        candidatos = self.store.buscar(pregunta)
        if not candidatos:
            return BuscadorOutput(
                respuesta="",
                encontrado=False,
                score_similitud=0.0,
                score_fidelidad=0.0,
                motivo_fallo="No se encontraron documentos candidatos.",
            ).model_dump()

        # 2. Reranking
        documentos_top = self.reranker.rerank(pregunta, candidatos)
        contexto, citaciones = self.reranker.ensamblar_contexto(documentos_top)

        # 3. Generar respuesta
        respuesta = self.rag_chain.invoke({"input": pregunta, "context": contexto})

        # 4. Detectar fallo explícito del RAG
        if "no cuento con información suficiente" in respuesta.lower():
            return BuscadorOutput(
                respuesta=respuesta,
                encontrado=False,
                score_similitud=0.0,
                score_fidelidad=0.0,
                motivo_fallo="El contexto no cubre la pregunta.",
            ).model_dump()

        # 5. Guardrail anti-alucinación
        evaluacion = self.guardrail.invoke(
            PROMPT_GUARDRAIL.format(contexto=contexto, pregunta=pregunta, respuesta=respuesta)
        )
        if not evaluacion.fiel_al_contexto:
            return BuscadorOutput(
                respuesta="",
                encontrado=False,
                score_similitud=0.0,
                score_fidelidad=evaluacion.score_fidelidad,
                alucinacion_detectada=True,
                motivo_fallo=f"Alucinación: {evaluacion.justificacion}",
            ).model_dump()

        # 6. Éxito
        return BuscadorOutput(
            respuesta=respuesta,
            encontrado=True,
            score_similitud=round(evaluacion.score_fidelidad, 4),
            score_fidelidad=evaluacion.score_fidelidad,
            fuente=citaciones[0] if citaciones else None,
        ).model_dump()


def crear_tool_buscador(buscador: BuscadorTool):
    """
    Envuelve el BuscadorTool como Tool de LangChain.
    """

    @tool
    def buscador_faq(pregunta: str) -> dict:
        """
        Busca en los PDFs institucionales la respuesta a una duda académica, o institucional.
        Devuelve un JSON con: respuesta, encontrado, score_similitud,
        score_fidelidad, fuente, alucinacion_detectada, motivo_fallo.
        """
        return buscador.ejecutar(pregunta)

    return buscador_faq