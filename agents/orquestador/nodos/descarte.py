"""Nodo 3c: registra mensajes clasificados como OTRO."""
from __future__ import annotations


def descartar_lote(
    mensajes: list[dict],
    clasificaciones: list[dict],
) -> list[dict]:
    """Registra los mensajes descartados por clasificación OTRO."""
    descartados: list[dict] = []
    for msg in mensajes:
        clas = next(
            (c for c in clasificaciones if c["mensaje_id"] == msg["mensaje_id"]),
            None,
        )
        if clas and clas["intencion"] == "OTRO":
            descartados.append({
                "mensaje_id": msg["mensaje_id"],
                "motivo": "clasificado_como_otro",
                "razon_clasificador": clas.get("razon", ""),
            })
    return descartados