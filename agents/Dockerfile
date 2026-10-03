# Imagen del servicio de IA: orquestador (FastAPI + LangGraph) y Agente FAQ.
# Se construye desde la raíz del repositorio (ver compose.yml), porque el
# código se importa como paquete `agents.*`.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Usuario sin privilegios de administrador; es dueño de /app porque la IA escribe ahí
# (índice de preguntas repetidas e historial).
RUN useradd --create-home ia && mkdir -p /app/.cache && chown -R ia:ia /app

# PyTorch solo para CPU: la versión por defecto trae librerías de GPU que pesan varios GB.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY agents/requirements-ia.txt /tmp/requirements-ia.txt
RUN pip install -r /tmp/requirements-ia.txt

USER ia

# Descarga los modelos de embeddings y del reranker durante la construcción:
# así el servicio arranca sin depender de internet y la primera pregunta no espera la descarga.
ARG FAQ_EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
ARG FAQ_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('${FAQ_EMBEDDING_MODEL_NAME}'); CrossEncoder('${FAQ_RERANKER_MODEL}')"
# Los modelos ya están en la imagen: no consultar internet al arrancar.
ENV HF_HUB_OFFLINE=1

COPY --chown=ia:ia agents agents
# El contrato v1 de la ingesta: la única definición, que /v1/procesar importa (no se copia a mano)
COPY --chown=ia:ia ingestion/discord/contract.py ingestion/discord/contract.py

EXPOSE 8000

CMD ["uvicorn", "agents.orquestador.api:app", "--host", "0.0.0.0", "--port", "8000"]
