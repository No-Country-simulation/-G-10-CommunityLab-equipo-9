# Imagen del bot de Discord (T05). Se construye desde la raíz del repositorio (ver compose.yml),
# porque reutiliza los módulos de la ingesta sin tener una copia en git (C2: un solo contrato v1).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Usuario sin privilegios de administrador: el bot no escribe nada en disco
RUN useradd --create-home bot

COPY agents/bot_discord/requirements.txt /tmp/requirements-bot.txt
RUN pip install -r /tmp/requirements-bot.txt

# Los módulos de la ingesta que el bot reutiliza, en la misma ruta relativa que en el repositorio
COPY ingestion/discord/contract.py ingestion/discord/transform.py ingestion/discord/config.py \
     ingestion/discord/discord_api.py ingestion/discord/
COPY agents/bot_discord/bot_communitylab.py agents/bot_discord/

USER bot

# Sin puertos: el bot solo sale hacia Discord y hacia la API Java
CMD ["python", "agents/bot_discord/bot_communitylab.py"]
