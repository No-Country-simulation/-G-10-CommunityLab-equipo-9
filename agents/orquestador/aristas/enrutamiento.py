"""Aristas condicionales del Orquestador."""
from __future__ import annotations


def enrutar_por_intencion(state: dict) -> str:
    """
    Decide a qué nodo ir tras el clasificador.
    Prioridad: TESTIMONIO/COMENTARIO > PREGUNTA_FAQ > descarte.
    """
    clasificaciones = state.get("clasificaciones", [])
    intenciones = {c["intencion"] for c in clasificaciones}

    if intenciones & {"TESTIMONIO", "COMENTARIO"}:
        return "ir_a_mod"
    if "PREGUNTA_FAQ" in intenciones:
        return "ir_a_faq"
    return "ir_a_descarte"