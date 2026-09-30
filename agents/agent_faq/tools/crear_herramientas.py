"""
Fábrica de herramientas del Agente FAQ.
"""
from .buscador import BuscadorTool, crear_tool_buscador
from .reporte_faq import ReporteTool, crear_tool_reporte


def crear_herramientas_faq(
    buscador: BuscadorTool,
    reporte: ReporteTool,
) -> list:
    """Construye y devuelve las tools listas para el agente."""
    tool_buscador = crear_tool_buscador(buscador)
    tool_reporte = crear_tool_reporte(reporte)
    return [tool_buscador, tool_reporte]