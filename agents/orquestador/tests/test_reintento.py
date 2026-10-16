"""
Reintento ante un 503 o un 504 en vivo (T14, DEC-170): agents/reintento_llm.py.

Usan modelos falsos y un reloj simulado: ninguna llamada a Gemini y ninguna espera real larga.
Correr desde la raíz del repositorio:  python -m pytest agents/orquestador/tests -q
"""
import time

import pytest
from langchain_core.runnables import Runnable

from agents.orquestador.clasificadores.etiquetador import EtiquetadorLLM, EtiquetasLLM
from agents.orquestador.contrato_ia import RespuestaFaq
from agents.orquestador.grafo_v1 import ProcesadorV1
from agents.reintento_llm import ReintentoEnVivo, _plazo, codigo_pasajero, plazo_en_vivo

TOPE_S = 40.0
LLAMADA_S = 20.0  # LLM_TIMEOUT_S


class ErrorGoogle(Exception):
    """Como el GoogleAPIError de LangChain: el código HTTP en .code."""

    def __init__(self, code: int):
        super().__init__(f"{code} ERROR de Google")
        self.code = code


class Reloj:
    def __init__(self):
        self.ahora = 0.0
        self.esperas = []

    def __call__(self):
        return self.ahora

    def dormir(self, segundos):
        self.esperas.append(segundos)
        self.ahora += segundos


class ModeloFalso(Runnable):
    """Un modelo que falla con los errores de la lista (uno por llamada) y después responde. Tarda `dura` s."""

    def __init__(self, nombre, errores=(), registro=None, reloj=None, dura=0.0):
        self.nombre, self.errores, self.registro = nombre, list(errores), registro if registro is not None else []
        self.reloj, self.dura = reloj, dura

    def invoke(self, entrada, config=None, **kwargs):
        self.registro.append(self.nombre)
        if self.reloj:
            self.reloj.ahora += self.dura
        if self.errores:
            raise self.errores.pop(0)
        return f"respuesta de {self.nombre}"

    def with_structured_output(self, esquema, include_raw=False) -> Runnable:
        return self


def _con_reintento(modelo, reloj):
    return ReintentoEnVivo(modelo, LLAMADA_S, espera_s=1.5, reintentos=2, reloj=reloj, dormir=reloj.dormir)


# ── Qué errores se reintentan ──

@pytest.mark.parametrize("codigo, esperado", [(503, 503), (504, 504), (400, None), (401, None), (403, None),
                                              (404, None), (429, None), (500, None)])
def test_solo_un_503_o_un_504_son_pasajeros(codigo, esperado):
    assert codigo_pasajero(ErrorGoogle(codigo)) == esperado


def test_tambien_si_el_codigo_viene_en_la_causa():
    try:
        try:
            raise ErrorGoogle(503)
        except ErrorGoogle as e:
            raise RuntimeError("envuelto") from e
    except RuntimeError as envuelto:
        assert codigo_pasajero(envuelto) == 503


def test_el_error_real_de_langchain_trae_el_codigo():
    chat_models = pytest.importorskip("langchain_google_genai.chat_models")
    error = chat_models.GoogleAPIError(code=503, response_json={"error": {"code": 503, "status": "UNAVAILABLE"}})
    assert codigo_pasajero(error) == 503


# ── Prueba 15 ──

def test_un_503_con_tiempo_de_sobra_reintenta_y_responde():
    reloj = Reloj()
    modelo = ModeloFalso("principal", [ErrorGoogle(503)])

    with plazo_en_vivo(TOPE_S):
        respuesta = _con_reintento(modelo, reloj).invoke("¿duda?")

    assert respuesta == "respuesta de principal"
    assert modelo.registro == ["principal", "principal"] and reloj.esperas == [1.5]


def test_un_503_cuando_ya_no_queda_tiempo_se_rinde_enseguida():
    reloj = Reloj()
    reloj.ahora = TOPE_S - 15  # quedan 15 s: no alcanzan para esperar 1,5 s y una llamada de 20 s
    modelo = ModeloFalso("principal", [ErrorGoogle(503)])

    with plazo_en_vivo(TOPE_S), pytest.raises(ErrorGoogle):
        _con_reintento(modelo, reloj).invoke("¿duda?")

    assert modelo.registro == ["principal"] and reloj.esperas == []


@pytest.mark.parametrize("codigo", [400, 429])
def test_un_400_o_un_429_no_se_reintentan(codigo):
    reloj = Reloj()
    modelo = ModeloFalso("principal", [ErrorGoogle(codigo)])

    with plazo_en_vivo(TOPE_S), pytest.raises(ErrorGoogle):
        _con_reintento(modelo, reloj).invoke("¿duda?")

    assert modelo.registro == ["principal"] and reloj.esperas == []


def test_fuera_de_vivo_no_reintenta():
    """Sin hora límite (lotes de historial, la FAQ semanal) se comporta como el modelo envuelto."""
    reloj = Reloj()
    modelo = ModeloFalso("principal", [ErrorGoogle(503)])

    with pytest.raises(ErrorGoogle):
        _con_reintento(modelo, reloj).invoke("¿duda?")

    assert modelo.registro == ["principal"]


def test_como_mucho_dos_reintentos():
    reloj = Reloj()
    modelo = ModeloFalso("principal", [ErrorGoogle(503)] * 5)

    with plazo_en_vivo(1000.0), pytest.raises(ErrorGoogle):
        _con_reintento(modelo, reloj).invoke("¿duda?")

    assert len(modelo.registro) == 3 and reloj.esperas == [1.5, 1.5]


def test_el_registro_dice_el_codigo_y_nunca_el_texto(caplog):
    reloj = Reloj()
    with plazo_en_vivo(TOPE_S), caplog.at_level("WARNING", logger="reintento"):
        _con_reintento(ModeloFalso("principal", [ErrorGoogle(503)]), reloj).invoke("¿cómo instalo python?")

    assert "Gemini respondió 503: reintento 1 de 2" in caplog.text
    assert "python" not in caplog.text


# ── Prueba 16: el respaldo y el reintento juntos, y el tope ──

def test_primero_el_respaldo_y_si_los_dos_estan_saturados_espera_y_reintenta():
    reloj = Reloj()
    registro = []
    principal = ModeloFalso("principal", [ErrorGoogle(503)] * 2, registro, reloj, dura=1)
    respaldo = ModeloFalso("respaldo", [ErrorGoogle(503)], registro, reloj, dura=1)

    with plazo_en_vivo(TOPE_S):
        respuesta = _con_reintento(principal.with_fallbacks([respaldo]), reloj).invoke("¿duda?")

    # Un intento = el principal y, enseguida, el respaldo. Solo si los dos fallan, se espera y se reintenta
    assert registro == ["principal", "respaldo", "principal", "respaldo"]
    assert respuesta == "respuesta de respaldo" and reloj.esperas == [1.5]


def test_con_llamadas_lentas_nunca_pasa_del_tope():
    reloj = Reloj()
    registro = []
    principal = ModeloFalso("principal", [ErrorGoogle(503)] * 9, registro, reloj, dura=8)
    respaldo = ModeloFalso("respaldo", [ErrorGoogle(504)] * 9, registro, reloj, dura=8)

    with plazo_en_vivo(TOPE_S), pytest.raises(ErrorGoogle):
        _con_reintento(principal.with_fallbacks([respaldo]), reloj).invoke("¿duda?")

    # 0 → 16 s (los dos fallan) → espera → 17,5 → 33,5 s: quedan 6,5 s, menos que una llamada: se rinde
    assert registro == ["principal", "respaldo"] * 2
    assert reloj.ahora <= TOPE_S


# ── La hora límite llega a los hilos del clasificador y del Agente FAQ ──

def test_el_clasificador_en_vivo_reintenta_un_503_en_su_hilo(monkeypatch):
    from agents.orquestador.tests.test_v1_procesar import UsoFalso, _mensaje_contrato

    class Estructurado(ModeloFalso):
        def invoke(self, entrada, config=None, **kwargs):
            super().invoke(entrada)
            return {"raw": UsoFalso(), "parsed": EtiquetasLLM(intencion="PREGUNTA_FAQ", confianza=0.9, razon="duda",
                                                               sentimiento="NEUTRO", tema="otro"),
                    "parsing_error": None}

    modelo = Estructurado("principal", [ErrorGoogle(503)])
    llm = ReintentoEnVivo(modelo, tiempo_llamada_s=0.1, espera_s=0.01)

    etiquetado = EtiquetadorLLM(llm, reintentos=1).etiquetar(_mensaje_contrato(), plazo=time.perf_counter() + 5)

    assert etiquetado.etiquetas is not None and etiquetado.etiquetas.intencion == "PREGUNTA_FAQ"
    assert modelo.registro == ["principal", "principal"]  # el reintento del modelo, no el del clasificador


def test_el_clasificador_en_vivo_no_repite_un_429():
    from agents.orquestador.tests.test_v1_procesar import _mensaje_contrato

    modelo = ModeloFalso("principal", [ErrorGoogle(429)] * 3)

    etiquetado = EtiquetadorLLM(ReintentoEnVivo(modelo, 0.1, espera_s=0.01), reintentos=1).etiquetar(
        _mensaje_contrato(), plazo=time.perf_counter() + 5)

    assert etiquetado.etiquetas is None and "El LLM falló" in etiquetado.error
    assert modelo.registro == ["principal"]  # en vivo ya no se repite ante cualquier error


def test_el_agente_faq_corre_con_la_hora_limite_del_pedido():
    from agents.orquestador.tests.test_v1_procesar import _mensaje_contrato

    vistos = []

    def faq(mensaje):
        vistos.append(_plazo.get())
        return RespuestaFaq(texto="Sí.", encontrada=True, fuentes=["12_Preguntas.pdf (Pág. 1)"])

    plazo = time.perf_counter() + 5
    respuesta = ProcesadorV1(etiquetador=None, responder_faq=faq)._responder_a_tiempo(_mensaje_contrato(), plazo)

    assert respuesta.encontrada and vistos == [plazo]
    assert _plazo.get() is None  # fuera del pedido, no queda ninguna hora límite puesta
