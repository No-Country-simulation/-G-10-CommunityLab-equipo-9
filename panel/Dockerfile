# Imagen del panel de curaduría (T07). Se construye desde panel/ (ver compose.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Usuario sin privilegios de administrador: el panel no escribe nada en disco
RUN useradd --create-home panel

COPY requirements.txt /tmp/requirements-panel.txt
RUN pip install -r /tmp/requirements-panel.txt

COPY .streamlit/ .streamlit/
COPY app.py auth.py cliente_java.py ui.py ./
COPY paginas/ paginas/

USER panel

EXPOSE 8501

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
