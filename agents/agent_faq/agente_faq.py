"""
Agente FAQ: construcción con create_react_agent + AgentExecutor.
"""
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .config import LLM_MODEL_NAME, AGENTE_VERSION
from .llm_models import select_llm
from .prompts.prompts import SYSTEM_PROMPT_AGENTE
from .tools.buscador import BuscadorTool
from .tools.reporte_faq import ReporteTool
from .tools.crear_herramientas import crear_herramientas_faq
from .vectorstore.preguntas_store import PreguntasStore
from .vectorstore.reranker import Reranker
from .vectorstore.store import StorePDFs


PROMPT_AGENT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_AGENTE),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

class AgenteFAQ:
    """Agente FAQ standalone (prueba independiente antes de integrar al Orquestador)."""

    def __init__(self, forzar_reindexado: bool = False):
        print(f"[AgenteFAQ v{AGENTE_VERSION}] Inicializando...")

        # 1. LLM
        self.llm = select_llm()
        print(f"[AgenteFAQ] LLM: {LLM_MODEL_NAME}")

        # 2. Vectorstore PDFs
        self.store = StorePDFs()
        self.store.construir(forzar_reindexado=forzar_reindexado)

        # 3. Reranker
        self.reranker = Reranker()

        # 4. Vectorstore de preguntas
        self.preguntas_store = PreguntasStore()

        # 5. Tools
        self.buscador = BuscadorTool(self.store, self.reranker, self.llm)
        self.reporte = ReporteTool(self.preguntas_store)
        self.tools = crear_herramientas_faq(self.buscador, self.reporte)

        # 6. Agente ReAct
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=PROMPT_AGENT,
        )
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True,
        )
        print("[AgenteFAQ] Listo.")

    def responder(self, pregunta: str, metadata: dict | None = None) -> dict:
        """
        El agente invoca al buscador, y luego genera el reporte, para enviar al angente
        """
        buscador_result = self.buscador.ejecutar(pregunta)
        reporte_result = self.reporte.ejecutar(pregunta, buscador_result, metadata)

        return {
            "pregunta": pregunta,
            "respuesta_agente": buscador_result,
            "reporte": reporte_result,
            "metadata": metadata or {},
        }