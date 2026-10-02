from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

# Importamos los contratos reales desde tu estructura
from agents.orquestador.contratos import (
    InputOrquestador,
    OutputOrquestador,
    RespuestaDiscord,
    RespuestaIndividual,
    PaqueteFinal,
    ResumenLote,
    LogEjecucion
)
import agents.orquestador.config as config

app = FastAPI(
    title="No Country - Orquestador FAQ & NLP API",
    version="1.0.0",
    description="Microservicio FastAPI integrado para procesar flujos del orquestador de agentes."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    """Endpoint de verificación de estado."""
    return {
        "status": "online",
        "agente": getattr(config, "AGENTE_NOMBRE", "orquestador_g10"),
        "version": getattr(config, "AGENTE_VERSION", "1.0.0")
    }

@app.post("/api/v1/orquestador/ejecutar", response_model=OutputOrquestador)
def ejecutar_flujo_orquestador(input_data: InputOrquestador):
    """
    Endpoint principal que recibe el InputOrquestador (lote de mensajes)
    y devuelve el OutputOrquestador con respuestas y auditoría completa.
    """
    try:
        # 1. Aquí más adelante conectarás la llamada real a tu orquestador.py
        # resultado = ejecutar_orquestador(input_data)
        
        # 2. Mock temporal alineado estrictamente con tus contratos Pydantic
        from datetime import datetime
        
        tiempo_actual = datetime.utcnow().isoformat()

        respuestas_mock = [
            RespuestaIndividual(
                mensaje_id=msg.mensaje_id,
                channel_id=msg.channel_id,
                texto_respuesta=f"Procesado correctamente: {msg.contenido}",
                requiere_humano=False,
                intencion="PREGUNTA_FAQ"
            ) for msg in input_data.mensajes
        ]

        respuesta_discord_mock = RespuestaDiscord(
            lote_id=input_data.lote_id,
            respuestas=respuestas_mock
        )

        resumen_lote_mock = ResumenLote(
            total_mensajes=len(input_data.mensajes),
            descartados_filtro=0,
            testimonios=0,
            preguntas_faq=len(input_data.mensajes),
            comentarios=0,
            otro=0,
            procesados_exito=len(input_data.mensajes),
            requieren_humano=0
        )

        paquete_final_mock = PaqueteFinal(
            lote_id=input_data.lote_id,
            resumen_lote=resumen_lote_mock,
            activos_generados=[],
            requiere_humano=[]
        )

        log_ejecucion_mock = LogEjecucion(
            lote_id=input_data.lote_id,
            timestamp_inicio=tiempo_actual,
            timestamp_fin=tiempo_actual,
            duracion_total_ms=120,
            tokens_totales=150,
            sublogs=[],
            errores=[]
        )

        return OutputOrquestador(
            lote_id=input_data.lote_id,
            respuesta_discord=respuesta_discord_mock,
            paquete_final=paquete_final_mock,
            log_ejecucion=log_ejecucion_mock
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el orquestador: {str(e)}")