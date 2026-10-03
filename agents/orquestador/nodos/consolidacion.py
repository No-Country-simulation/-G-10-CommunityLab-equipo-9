"""
Nodo 4: consolidación.

Empaqueta el paquete final, construye el log, genera la respuesta_discord,
y sube todo a OCI (si está configurado).
"""
from __future__ import annotations
from datetime import datetime, timezone

from ..contratos import (
    PaqueteFinal, ResumenLote, ActivoGenerado, ItemRequiereHumano,
    LogEjecucion, SublogMensaje,
    RespuestaDiscord, RespuestaIndividual,
)
from ..storage.oci_client import OCIClient


def _construir_respuesta_discord(
    lote_id: str,
    mensajes_originales: list[dict],
    resultados_mod: list[dict],
    resultados_faq: list[dict],
) -> RespuestaDiscord:
    """Construye la respuesta lista para n8n → Discord."""
    respuestas: list[RespuestaIndividual] = []

    # Mapear mensaje_id -> channel_id (desde los originales)
    mapa_canal = {m["mensaje_id"]: m["channel_id"] for m in mensajes_originales}

    for r in (resultados_mod + resultados_faq):
        respuestas.append(
            RespuestaIndividual(
                mensaje_id=r["mensaje_id"],
                channel_id=mapa_canal.get(r["mensaje_id"], ""),
                texto_respuesta=r.get("texto_respuesta", ""),
                requiere_humano=(r.get("status") == "atencion_humano"),
                intencion=r["intencion"],
            )
        )

    return RespuestaDiscord(lote_id=lote_id, respuestas=respuestas)


def consolidar(
    lote_id: str,
    mensajes_originales: list[dict],
    mensajes_validos: list[dict],
    mensajes_descartados_filtro: list[dict],
    clasificaciones: list[dict],
    resultados_mod: list[dict],
    resultados_faq: list[dict],
    descartados_otro: list[dict],
    timestamp_inicio: str,
) -> tuple[PaqueteFinal, LogEjecucion, RespuestaDiscord]:
    """Consolida el paquete final, el log y la respuesta_discord."""

    # --- Resumen del lote ---
    resumen = ResumenLote(
        total_mensajes=len(mensajes_originales),
        descartados_filtro=len(mensajes_descartados_filtro),
        testimonios=sum(1 for c in clasificaciones if c["intencion"] == "TESTIMONIO"),
        preguntas_faq=sum(1 for c in clasificaciones if c["intencion"] == "PREGUNTA_FAQ"),
        comentarios=sum(1 for c in clasificaciones if c["intencion"] == "COMENTARIO"),
        otro=sum(1 for c in clasificaciones if c["intencion"] == "OTRO"),
        procesados_exito=sum(1 for r in (resultados_mod + resultados_faq) if r.get("status") == "exito"),
        requieren_humano=sum(1 for r in (resultados_mod + resultados_faq) if r.get("status") == "atencion_humano"),
    )

    # --- Activos generados ---
    activos = []
    for r in (resultados_mod + resultados_faq):
        if r.get("status") == "exito":
            activos.append(
                ActivoGenerado(
                    mensaje_id=r["mensaje_id"],
                    intencion=r["intencion"],
                    output=r.get("output", {}),
                    metadata=r.get("metadata", {}),
                )
            )

    # --- Requiere humano ---
    requiere_humano = []
    for r in (resultados_mod + resultados_faq):
        if r.get("status") == "atencion_humano":
            requiere_humano.append(
                ItemRequiereHumano(
                    mensaje_id=r["mensaje_id"],
                    motivo=r.get("motivo_atencion", "sin_motivo"),
                    detalle=str(r.get("output", {}))[:500],
                )
            )

    paquete = PaqueteFinal(
        lote_id=lote_id,
        resumen_lote=resumen,
        activos_generados=activos,
        requiere_humano=requiere_humano,
    )

    # --- Respuesta para Discord ---
    respuesta_discord = _construir_respuesta_discord(
        lote_id=lote_id,
        mensajes_originales=mensajes_originales,
        resultados_mod=resultados_mod,
        resultados_faq=resultados_faq,
    )

    # --- Log de ejecución ---
    timestamp_fin = datetime.now(timezone.utc).isoformat()
    try:
        duracion_ms = int(
            (datetime.fromisoformat(timestamp_fin) -
             datetime.fromisoformat(timestamp_inicio)).total_seconds() * 1000
        )
    except Exception:
        duracion_ms = 0

    sublogs = []
    tokens_totales = 0
    for r in (resultados_mod + resultados_faq):
        meta = r.get("metadata", {})
        tokens_in = meta.get("tokens_in", 0)
        tokens_out = meta.get("tokens_out", 0)
        tokens_totales += tokens_in + tokens_out

        sublogs.append(
            SublogMensaje(
                mensaje_id=r["mensaje_id"],
                intencion=r["intencion"],
                tiempo_ms=meta.get("tiempo_ms", 0),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                status=r.get("status", "exito"),
            )
        )

    log = LogEjecucion(
        lote_id=lote_id,
        timestamp_inicio=timestamp_inicio,
        timestamp_fin=timestamp_fin,
        duracion_total_ms=duracion_ms,
        tokens_totales=tokens_totales,
        sublogs=sublogs,
        errores=[],
    )

    # --- Persistencia OCI (opcional, falla silenciosa) ---
    try:
        oci = OCIClient()
        oci.subir_paquete(lote_id, paquete.model_dump())
        oci.subir_log(lote_id, log.model_dump())
    except Exception as e:
        log.errores.append(f"Error OCI: {e}")

    return paquete, log, respuesta_discord