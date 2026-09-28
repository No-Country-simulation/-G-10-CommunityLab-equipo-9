"""
Agente FAQ: construcción con create_react_agent + AgentExecutor.
"""
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from .config import LLM_MODEL_NAME, AGENTE_VERSION
from .llm_models import select_llm
from .prompts.prompts import SYSTEM_PROMPT_AGENTE
from .tools.buscador import BuscadorTool
from .tools.reporte_faq import ReporteTool
from .tools.crear_herramientas import crear_herramientas_faq
from .vectorstore.preguntas_store import PreguntasStore
from .vectorstore.reranker import Reranker
from .vectorstore.store import StorePDFs


PROMPT_REACT = PromptTemplate.from_template(
    SYSTEM_PROMPT_AGENTE
    + """

Tienes acceso a las siguientes herramientas:
{tools}

Usa EXACTAMENTE este formato:

Question: la pregunta del estudiante
Thought: razona sobre qué hacer
Action: una de [{tool_names}]
Action Input: la entrada para la acción
Observation: el resultado de la acción
... (repite Thought/Action/Action Input/Observation si es necesario)
Thought: ya tengo la respuesta final
Final Answer: la respuesta consolidada para el estudiante

Comienza.

Question: {input}
Thought: {agent_scratchpad}
"""
)


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
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=PROMPT_REACT,
        )
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
        )
        print("[AgenteFAQ] Listo.")

    def responder(self, pregunta: str, metadata: dict | None = None) -> dict:
        """Punto de entrada: recibe pregunta, devuelve respuesta + reporte."""
        resultado = self.executor.invoke({"input": pregunta})
        return {
            "pregunta": pregunta,
            "respuesta_agente": resultado.get("output", ""),
            "metadata": metadata or {},
        }