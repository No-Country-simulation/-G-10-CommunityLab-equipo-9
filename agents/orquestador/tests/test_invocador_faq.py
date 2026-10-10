"""
Pruebas del invocador del Agente FAQ: el agente se crea una sola vez.

Usan un agente falso, así que no cargan modelos ni llaman a ningún LLM.
Correr desde la raíz del repositorio:  python -m pytest agents/orquestador/tests -q
"""
import threading
import time

from agents.orquestador.nodos import invocador_faq

CLASIFICACION = {"intencion": "PREGUNTA_FAQ"}


class AgenteFalso:
    creados = 0

    def __init__(self):
        AgenteFalso.creados += 1
        time.sleep(0.05)  # simula la carga de modelos

    def responder(self, pregunta, metadata=None):
        return {"respuesta_agente": {"respuesta": f"eco: {pregunta}", "encontrado": True}, "reporte": {}}


def _mensaje(n: int) -> dict:
    return {"mensaje_id": str(n), "contenido": f"pregunta {n}", "channel_id": "c1", "autor_username": "ana"}


def _usar_agente_falso(monkeypatch):
    AgenteFalso.creados = 0
    monkeypatch.setattr(invocador_faq, "_agente_faq", None)
    monkeypatch.setattr(invocador_faq, "_cargar_agente_faq", lambda: AgenteFalso)


def test_reutiliza_la_misma_instancia(monkeypatch):
    _usar_agente_falso(monkeypatch)

    primera = invocador_faq._invocar_uno(_mensaje(1), CLASIFICACION)
    segunda = invocador_faq._invocar_uno(_mensaje(2), CLASIFICACION)

    assert AgenteFalso.creados == 1
    assert primera.texto_respuesta == "eco: pregunta 1"
    assert segunda.status == "exito"


def test_preguntas_en_paralelo_crean_un_solo_agente(monkeypatch):
    _usar_agente_falso(monkeypatch)

    hilos = [
        threading.Thread(target=invocador_faq._invocar_uno, args=(_mensaje(n), CLASIFICACION))
        for n in range(8)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert AgenteFalso.creados == 1


def test_la_precarga_deja_el_agente_listo_para_la_primera_pregunta(monkeypatch):
    _usar_agente_falso(monkeypatch)
    assert not invocador_faq.agente_faq_listo()

    invocador_faq.precargar_agente_faq()
    invocador_faq._invocar_uno(_mensaje(1), CLASIFICACION)

    assert invocador_faq.agente_faq_listo()
    assert AgenteFalso.creados == 1


def test_si_la_precarga_falla_el_servicio_sigue(monkeypatch):
    _usar_agente_falso(monkeypatch)

    def cargar_que_falla():
        raise RuntimeError("sin clave de Gemini")

    monkeypatch.setattr(invocador_faq, "_cargar_agente_faq", cargar_que_falla)

    invocador_faq.precargar_agente_faq()  # no debe lanzar el error

    assert not invocador_faq.agente_faq_listo()


def test_si_falla_la_creacion_se_reintenta_en_la_siguiente_pregunta(monkeypatch):
    _usar_agente_falso(monkeypatch)
    intentos = {"n": 0}

    def cargar_que_falla_una_vez():
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise RuntimeError("modelo no disponible")
        return AgenteFalso

    monkeypatch.setattr(invocador_faq, "_cargar_agente_faq", cargar_que_falla_una_vez)

    fallida = invocador_faq._invocar_uno(_mensaje(1), CLASIFICACION)
    exitosa = invocador_faq._invocar_uno(_mensaje(2), CLASIFICACION)

    assert fallida.status == "atencion_humano"
    assert "modelo no disponible" in fallida.motivo_atencion
    assert exitosa.status == "exito"
