"""
Orquestador principal en LangGraph.

Empaqueta todo el flujo: filtro → clasificación → invocadores → consolidación.
Se expone como una clase con método procesar_lote().
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import TypedDict, Optional, List

from langgraph.graph import START, END, StateGraph

from .contratos import InputOrquestador, OutputOrquestador
from .nodos.filtro_ruido import filtrar_mensajes
from .nodos.clasificador import ClasificadorNodo
from .nodos.invocador_mod import invocar_mod_lote
from .nodos.invocador_faq import invocar_faq_lote
from .nodos.descarte import descartar_lote
from .nodos.consolidacion import consolidar
from .aristas.enrutamiento import enrutar_por_intencion


class OrquestadorState(TypedDict, total=False):
    # Entrada
    lote_id: str
    origen: str
    servidor: str
    mensajes: List[dict]

    # Post-filtro
    mensajes_validos: List[dict]
    mensajes_descartados_filtro: List[dict]

    # Clasificación
    clasificaciones: List[dict]

    # Outputs de sub-agentes
    resultados_mod: List[dict]
    resultados_faq: List[dict]
    descartados_otro: List[dict]

    # Consolidación
    paquete_final: Optional[dict]
    log_ejecucion: Optional[dict]
    respuesta_discord: Optional[dict]

    # Metadata
    timestamp_inicio: str


# ============================================================
# NODOS DEL GRAFO
# ============================================================

def nodo_filtro(state: OrquestadorState) -> dict:
    print("[Nodo] filtro_ruido")
    validos, descartados = filtrar_mensajes(state["mensajes"])
    return {
        "mensajes_validos": validos,
        "mensajes_descartados_filtro": descartados,
    }


def nodo_clasificador(state: OrquestadorState) -> dict:
    print("[Nodo] clasificador")
    clasificador = ClasificadorNodo()
    resultados = clasificador.clasificar_lote(state["mensajes_validos"])
    return {"clasificaciones": [c.model_dump() for c in resultados]}


def nodo_mod(state: OrquestadorState) -> dict:
    print("[Nodo] invocador_mod")
    resultados = invocar_mod_lote(state["mensajes_validos"], state["clasificaciones"])
    return {"resultados_mod": [r.model_dump() for r in resultados]}


def nodo_faq(state: OrquestadorState) -> dict:
    print("[Nodo] invocador_faq")
    resultados = invocar_faq_lote(state["mensajes_validos"], state["clasificaciones"])
    return {"resultados_faq": [r.model_dump() for r in resultados]}


def nodo_descarte(state: OrquestadorState) -> dict:
    print("[Nodo] descarte")
    descartados = descartar_lote(state["mensajes_validos"], state["clasificaciones"])
    return {"descartados_otro": descartados}


def nodo_consolidacion(state: OrquestadorState) -> dict:
    print("[Nodo] consolidacion")
    paquete, log, respuesta = consolidar(
        lote_id=state["lote_id"],
        mensajes_originales=state["mensajes"],
        mensajes_validos=state.get("mensajes_validos", []),
        mensajes_descartados_filtro=state.get("mensajes_descartados_filtro", []),
        clasificaciones=state.get("clasificaciones", []),
        resultados_mod=state.get("resultados_mod", []),
        resultados_faq=state.get("resultados_faq", []),
        descartados_otro=state.get("descartados_otro", []),
        timestamp_inicio=state["timestamp_inicio"],
    )
    return {
        "paquete_final": paquete.model_dump(),
        "log_ejecucion": log.model_dump(),
        "respuesta_discord": respuesta.model_dump(),
    }


# ============================================================
# CONSTRUCCIÓN DEL GRAFO
# ============================================================

def construir_grafo():
    """Construye el StateGraph del Orquestador."""
    graph = StateGraph(OrquestadorState)

    # Nodos
    graph.add_node("filtro", nodo_filtro)
    graph.add_node("clasificador", nodo_clasificador)
    graph.add_node("mod", nodo_mod)
    graph.add_node("faq", nodo_faq)
    graph.add_node("descarte", nodo_descarte)
    graph.add_node("consolidacion", nodo_consolidacion)

    # Entrada
    graph.add_edge(START, "filtro")
    graph.add_edge("filtro", "clasificador")

    # Flujo secuencial (cada nodo filtra internamente)
    graph.add_edge("clasificador", "mod")
    graph.add_edge("mod", "faq")
    graph.add_edge("faq", "descarte")
    graph.add_edge("descarte", "consolidacion")

    # Todos convergen en consolidación
    graph.add_edge("consolidacion", END)

    return graph.compile()


# ============================================================
# CLASE PRINCIPAL
# ============================================================

class Orquestador:
    """Orquestador empaquetado como 1 solo agente."""

    def __init__(self):
        self.grafo = construir_grafo()

    def procesar_lote(self, input_orq: InputOrquestador) -> OutputOrquestador:
        """Punto de entrada: recibe el lote y devuelve paquete + log + respuesta."""
        timestamp_inicio = datetime.now(timezone.utc).isoformat()

        estado_inicial: OrquestadorState = {
            "lote_id": input_orq.lote_id,
            "origen": input_orq.origen,
            "servidor": input_orq.servidor,
            "mensajes": [m.model_dump() for m in input_orq.mensajes],
            "timestamp_inicio": timestamp_inicio,
        }

        estado_final = self.grafo.invoke(estado_inicial)

        return OutputOrquestador(
            lote_id=estado_final["lote_id"],
            respuesta_discord=estado_final["respuesta_discord"],
            paquete_final=estado_final["paquete_final"],
            log_ejecucion=estado_final["log_ejecucion"],
        )