# Imagen del servicio `ingesta` (T14, DEC-167): la ingesta por lotes, al arrancar y cada hora en punto.
# Se construye desde la raíz del repositorio (ver compose.yml), como la IA y el bot. El .dockerignore de la raíz
# deja fuera todos los .env y ingestion/**/data/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# La misma ruta relativa que en el repositorio: los módulos guardan sus datos en data/, junto a ellos
WORKDIR /app/ingestion/discord

# Usuario sin privilegios de administrador
RUN useradd --create-home ingesta

COPY ingestion/discord/requirements.txt /tmp/requirements-ingesta.txt
RUN pip install -r /tmp/requirements-ingesta.txt

# Solo lo que hace falta para extraer, armar y enviar. simulate_students.py y simulation/ NO entran:
# publican mensajes falsos y nunca se ejecutan (AGENTS.md)
COPY ingestion/discord/config.py ingestion/discord/contract.py ingestion/discord/transform.py \
     ingestion/discord/discord_api.py ingestion/discord/extract.py ingestion/discord/build_batch.py \
     ingestion/discord/send_batch.py ingestion/discord/programador.py ./

# data/ (marcadores, crudos y lotes) es un volumen. Se crea con dueño ingesta para que el volumen nuevo lo herede
RUN mkdir data && chown ingesta:ingesta data

USER ingesta

# Sin puertos: solo sale hacia Discord (lectura) y hacia la API Java
CMD ["python", "programador.py"]
