"""
Prueba de la IA levantada con Docker: ¿atiende /health mientras procesa una pregunta?

Antes del arreglo F6, /health esperaba a que terminara /procesar. Ahora debe responder al instante.
Necesita GEMINI_API_KEY en .env: sin la clave, /procesar termina enseguida y la prueba no dice nada.

Uso, desde la raíz del repositorio y con `docker compose up -d` corriendo:
    python scripts/comprobar_ia_en_paralelo.py
Solo usa la librería estándar de Python.
"""
import json
import threading
import time
import urllib.request

IA = "http://127.0.0.1:8000"
PREGUNTA = {
    "lote_id": "prueba_paralelo",
    "mensajes": [{
        "id": "900000000000000001",
        "channel_id": "canal_prueba",
        "author": {"id": "autor_prueba", "username": "Prueba", "bot": False},
        "content": "¿Cuándo empiezan las inscripciones?",
        "timestamp": "2026-10-03T12:00:00+00:00",
    }],
}
resultado = {}


def procesar():
    """Envía la pregunta a /procesar y guarda la respuesta (o el error) y cuánto tardó."""
    t0 = time.perf_counter()
    pedido = urllib.request.Request(
        f"{IA}/procesar",
        data=json.dumps(PREGUNTA).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=180) as resp:
            resultado["cuerpo"] = json.load(resp)
    except Exception as e:  # se informa abajo, en el hilo principal
        resultado["error"] = e
    resultado["segundos"] = time.perf_counter() - t0


hilo = threading.Thread(target=procesar)
hilo.start()
time.sleep(1)  # que /procesar ya esté trabajando

inicio = time.perf_counter()
with urllib.request.urlopen(f"{IA}/health", timeout=180) as respuesta:
    respuesta.read()
segundos_health = time.perf_counter() - inicio
procesar_seguia = hilo.is_alive()
hilo.join()

print(f"/health respondió en {segundos_health:.2f} s")
print(f"/procesar tardó {resultado['segundos']:.2f} s")
if "error" in resultado:
    print(f"/procesar falló: {resultado['error']}  (ver: docker compose logs ia)")
for r in resultado.get("cuerpo", {}).get("respuesta_discord", {}).get("respuestas", []):
    print(f"Intención: {r['intencion']} · requiere humano: {r['requiere_humano']}")
    print(f"Respuesta: {r['texto_respuesta'][:200]}")

if not procesar_seguia:
    print("NO CONCLUYENTE: /procesar terminó antes de consultar /health (¿falta GEMINI_API_KEY?)")
elif segundos_health < 1:
    print("OK: la IA atendió /health mientras procesaba la pregunta")
else:
    print("FALLA: /health tuvo que esperar a /procesar")
