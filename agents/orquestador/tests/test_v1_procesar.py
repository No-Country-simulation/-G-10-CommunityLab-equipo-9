"""
Pruebas de POST /v1/procesar (contrato Java ↔ IA v1, tarea T02).

No llaman a ningún LLM real: usan un modelo falso y un Agente FAQ falso.
Los lotes se arman con la transformación real de la ingesta (transform.py y sus datos de prueba),
se convierten a JSON y se envían por HTTP, igual que lo hará Java.
Correr desde la raíz del repositorio:  python -m pytest agents/orquestador/tests -q
"""
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agents.orquestador import api, contrato_ia
from agents.orquestador import config as config_orq
from agents.orquestador.clasificadores.etiquetador import (
    EtiquetadorLLM,
    EtiquetadorPalabrasClave,
    EtiquetasLLM,
)
from agents.orquestador.contrato_ia import RespuestaFaq
from agents.orquestador.grafo_v1 import ProcesadorV1, responder_con_agente_faq
from agents.orquestador.nodos import invocador_faq

# transform.py importa "contract" como módulo suelto: se carga desde su carpeta
RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "ingestion" / "discord"))
sys.path.insert(0, str(RAIZ / "ingestion" / "discord" / "tests"))
import datos_prueba as dp  # noqa: E402
from transform import a_contrato, armar_lote  # noqa: E402

AUTOR_BOT = {"id": dp.BOT_ID, "username": "CommunityLab", "global_name": None, "bot": True, "discriminator": "0"}


# ── Dobles de prueba ──────────────────────────────────────────────────────────

class UsoFalso:
    usage_metadata = {"input_tokens": 100, "output_tokens": 20}


class LLMFalso:
    """Imita a un chat model de LangChain con with_structured_output(include_raw=True)."""

    def __init__(self, falla_veces: int = 0, demora_s: float = 0.0):
        self.llamadas = 0
        self.falla_veces = falla_veces
        self.demora_s = demora_s

    def with_structured_output(self, esquema, include_raw=False):
        assert esquema is EtiquetasLLM and include_raw
        return self

    def invoke(self, entrada):
        self.llamadas += 1
        if self.demora_s:
            time.sleep(self.demora_s)
        if self.llamadas <= self.falla_veces:
            raise RuntimeError("429 cupo agotado")
        texto = entrada[-1].content.lower()
        if "contrataron" in texto:
            etiquetas = EtiquetasLLM(intencion="TESTIMONIO", confianza=0.95, razon="logro",
                                     sentimiento="MUY_POSITIVO", tema="empleo")
        elif "?" in texto:
            etiquetas = EtiquetasLLM(intencion="PREGUNTA_FAQ", confianza=0.9, razon="pregunta",
                                     sentimiento="NEGATIVO", tema="herramientas_entorno")
        else:
            etiquetas = EtiquetasLLM(intencion="COMENTARIO", confianza=0.8, razon="opinión",
                                     sentimiento="POSITIVO", tema="comunidad")
        return {"raw": UsoFalso(), "parsed": etiquetas, "parsing_error": None}


class FaqFalso:
    def __init__(self):
        self.preguntas = []

    def __call__(self, mensaje):
        self.preguntas.append(mensaje.id)
        return RespuestaFaq(texto="Marca 'Add python.exe to PATH'.", encontrada=True,
                            fuentes=["06_Manual_del_Estudiante_V3.pdf (Pág. 4)"])


# ── Lotes de prueba (contrato v1 real) ────────────────────────────────────────

def _lote(crudos: list[dict], modo: str = "historial") -> dict:
    ctx = dp.contexto()
    mensajes = [a_contrato(c, "dudas", ctx) for c in crudos]
    return armar_lote(mensajes, modo, "1554157903701741700").model_dump(mode="json")


def _duda(id_: str = "1554205178671009863") -> dict:
    return dp.crudo(id=id_)  # "como instalo pyhton en windows?? ..." (alumna simulada)


def _logro(id_: str = "1554205393054466139") -> dict:
    return dp.crudo(id=id_, content="me contrataron!!!!! empiezo el lunes como QA trainee 🙌")


def _comentario(id_: str = "1554205400000000001") -> dict:
    return dp.crudo_real(id=id_, content="graciasss era eso 🙏")


CLAVE_IA = "clave-de-prueba-ia"


@pytest.fixture(autouse=True)
def clave_ia(monkeypatch):
    """S2 (T04): la IA tiene configurada una clave en todas estas pruebas."""
    monkeypatch.setattr(config_orq, "API_KEY_IA", CLAVE_IA)


@pytest.fixture
def cliente(monkeypatch):
    """Cliente HTTP con el procesador armado con dobles y la clave de Java. Sin 'with': no precarga el Agente FAQ real."""
    llm, faq = LLMFalso(), FaqFalso()

    def usar(etiquetador=None):
        monkeypatch.setattr(api, "_procesador_v1", ProcesadorV1(etiquetador or EtiquetadorLLM(llm), faq))
        return TestClient(api.app, headers={"X-Api-Key": CLAVE_IA})

    usar.llm, usar.faq = llm, faq
    return usar


def _por_id(respuesta) -> dict:
    return {r["discordId"]: r for r in respuesta.json()["resultados"]}


# ── Caso 1: un resultado por mensaje ──────────────────────────────────────────

def test_lote_valido_devuelve_un_resultado_por_mensaje_en_orden(cliente):
    lote = _lote([_duda(), _logro(), _comentario()])

    r = cliente().post("/v1/procesar", json=lote)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["versionContratoIa"] == "1.0"
    assert cuerpo["loteId"] == lote["loteId"]
    assert [x["discordId"] for x in cuerpo["resultados"]] == [m["id"] for m in lote["mensajes"]]
    logro = _por_id(r)["1554205393054466139"]
    assert logro == {
        "discordId": "1554205393054466139", "estado": "OK", "metodo": "llm",
        "intencion": "TESTIMONIO", "confianza": 0.95, "sentimiento": "MUY_POSITIVO",
        "tema": "empleo", "razon": "logro", "respuesta": None,
    }
    assert cuerpo["metricas"]["tokensIn"] == 300 and cuerpo["metricas"]["tokensOut"] == 60
    assert cliente.llm.llamadas == 3  # una sola llamada por mensaje


def test_la_respuesta_cumple_el_json_schema_publicado(cliente):
    r = cliente().post("/v1/procesar", json=_lote([_duda(), _logro()]))

    contrato_ia.RespuestaLote.model_validate(r.json())  # mismos modelos que generan el schema


# ── Caso 2: lote que no cumple el contrato ────────────────────────────────────

def test_lote_invalido_da_422_claro_sin_repetir_los_datos(cliente):
    lote = _lote([_duda()])
    lote["mensajes"][0]["autor"]["tipo"] = "HUMANO"
    lote["mensajes"][0]["textoOriginal"] = "dato privado del alumno"
    del lote["modo"]

    r = cliente().post("/v1/procesar", json=lote, headers={"X-Id-Correlacion": "abc-123"})

    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["codigo"] == "CONTRATO_INVALIDO"
    assert cuerpo["idCorrelacion"] == "abc-123"
    campos = {e["campo"] for e in cuerpo["errores"]}
    assert {"modo", "mensajes.0.autor.tipo"} <= campos
    assert "dato privado" not in r.text and "HUMANO" not in r.text  # S7
    assert cliente.llm.llamadas == 0


def test_cuerpo_que_no_es_json_da_422(cliente):
    r = cliente().post("/v1/procesar", content=b"{no es json", headers={"Content-Type": "application/json"})

    assert r.status_code == 422
    assert r.json()["codigo"] == "CONTRATO_INVALIDO"
    assert r.json()["idCorrelacion"]


# ── Caso 3: bots, avisos y mensajes sin texto no gastan el LLM ────────────────

def test_bot_aviso_y_sin_texto_son_otro_sin_llamar_al_llm(cliente):
    bot = dp.crudo_real(id="1554205500000000001", author=dict(AUTOR_BOT), content="Tu consulta fue registrada")
    aviso = dp.crudo(id="1554205500000000002", type=6, content="")
    sin_texto = dp.crudo(id="1554205500000000003", content="")
    otro_bot = dp.crudo(id="1554205500000000004", webhook_id=dp.WEBHOOK_AJENO, content="nuevo commit en main")

    r = cliente().post("/v1/procesar", json=_lote([bot, aviso, sin_texto, otro_bot]))

    assert r.status_code == 200
    resultados = _por_id(r)
    for discord_id, palabra in [("1554205500000000001", "botPropio"), ("1554205500000000002", "aviso"),
                                ("1554205500000000003", "sin texto"), ("1554205500000000004", "otroBot")]:
        res = resultados[discord_id]
        assert (res["estado"], res["metodo"], res["intencion"]) == ("OK", "regla", "OTRO")
        assert res["sentimiento"] is None and res["tema"] is None
        assert palabra in res["razon"].replace("no tiene texto", "sin texto")
    assert cliente.llm.llamadas == 0


# ── Caso 4: si el LLM falla, ERROR y no OTRO (F4) ─────────────────────────────

def test_si_el_llm_falla_el_estado_es_error_sin_intencion(cliente):
    llm = LLMFalso(falla_veces=99)

    r = cliente(EtiquetadorLLM(llm, reintentos=1)).post("/v1/procesar", json=_lote([_duda(), _logro()]))

    assert r.status_code == 200
    for res in r.json()["resultados"]:
        assert res["estado"] == "ERROR"
        assert res["intencion"] is None and res["confianza"] is None
        assert res["sentimiento"] is None and res["tema"] is None
        assert "RuntimeError" in res["razon"]
        assert "429" not in res["razon"]  # el detalle del proveedor queda en el registro, no en la respuesta
    assert llm.llamadas == 4  # 2 mensajes × (1 intento + 1 reintento)


def test_un_fallo_pasajero_se_reintenta_y_sale_ok(cliente):
    llm = LLMFalso(falla_veces=1)

    r = cliente(EtiquetadorLLM(llm, reintentos=1)).post("/v1/procesar", json=_lote([_logro()]))

    assert r.json()["resultados"][0]["estado"] == "OK"
    assert llm.llamadas == 2


def test_si_el_llm_no_responde_a_tiempo_es_error_y_no_se_reintenta(cliente):
    llm = LLMFalso(demora_s=0.5)
    inicio = time.perf_counter()

    r = cliente(EtiquetadorLLM(llm, timeout_s=0.1, reintentos=3)).post("/v1/procesar", json=_lote([_logro()]))

    res = r.json()["resultados"][0]
    assert res["estado"] == "ERROR" and "no respondió en 0.1 s" in res["razon"]
    assert llm.llamadas == 1
    assert time.perf_counter() - inicio < 0.45  # se cortó en el tiempo máximo, no esperó al LLM


def test_sin_llm_configurado_es_error_y_no_palabras_clave(cliente):
    r = cliente(EtiquetadorLLM(None)).post("/v1/procesar", json=_lote([_logro()]))

    res = r.json()["resultados"][0]
    assert res["estado"] == "ERROR" and res["metodo"] == "llm"
    assert "no está configurado" in res["razon"]


def test_palabras_clave_solo_si_se_eligen(cliente):
    r = cliente(EtiquetadorPalabrasClave()).post("/v1/procesar", json=_lote([_logro()]))

    res = r.json()["resultados"][0]
    assert (res["estado"], res["metodo"], res["intencion"], res["tema"]) == ("OK", "palabrasClave", "TESTIMONIO", "otro")


# ── Casos 5 y 6: respuesta del FAQ solo en tiempoReal ─────────────────────────

def test_pregunta_en_tiempo_real_trae_respuesta(cliente):
    r = cliente().post("/v1/procesar", json=_lote([_duda(), _logro()], modo="tiempoReal"))

    resultados = _por_id(r)
    duda = resultados["1554205178671009863"]
    assert duda["intencion"] == "PREGUNTA_FAQ"
    assert duda["respuesta"] == {
        "texto": "Marca 'Add python.exe to PATH'.", "encontrada": True,
        "fuentes": ["06_Manual_del_Estudiante_V3.pdf (Pág. 4)"], "motivo": None,
    }
    assert resultados["1554205393054466139"]["respuesta"] is None  # un logro solo se etiqueta
    assert cliente.faq.preguntas == ["1554205178671009863"]


def test_pregunta_en_historial_no_trae_respuesta(cliente):
    r = cliente().post("/v1/procesar", json=_lote([_duda()], modo="historial"))

    duda = r.json()["resultados"][0]
    assert duda["intencion"] == "PREGUNTA_FAQ" and duda["respuesta"] is None
    assert cliente.faq.preguntas == []  # no se gastó el Agente FAQ


def test_pregunta_con_error_no_va_al_faq(cliente):
    cliente(EtiquetadorLLM(LLMFalso(falla_veces=99), reintentos=0)).post(
        "/v1/procesar", json=_lote([_duda()], modo="tiempoReal"))

    assert cliente.faq.preguntas == []


# ── Traducción de la salida del Agente FAQ (D3) ───────────────────────────────

class AgenteFaqFalso:
    def __init__(self, buscador=None, error=None):
        self.buscador, self.error = buscador, error

    def responder(self, pregunta, metadata=None):
        if self.error:
            raise self.error
        return {"respuesta_agente": self.buscador, "reporte": {}}


def _mensaje_contrato():
    return contrato_ia.Lote.model_validate(_lote([_duda()])).mensajes[0]


def test_faq_con_fidelidad_media_no_cuenta_como_encontrada(monkeypatch):
    monkeypatch.setattr(invocador_faq, "_agente_faq", AgenteFaqFalso({
        "respuesta": "Quizás sea el PATH", "encontrado": True, "revision_recomendada": True,
        "fuente": "06_Manual_del_Estudiante_V3.pdf (Pág. 4)", "motivo_fallo": "Fidelidad media (0.75 < 0.85).",
    }))

    respuesta = responder_con_agente_faq(_mensaje_contrato())

    assert respuesta.encontrada is False
    assert respuesta.texto == "Quizás sea el PATH" and "Fidelidad media" in respuesta.motivo


@pytest.mark.parametrize("ruta", [
    r"C:\Users\alguien\Documents\G10\agents\agent_faq\data\pdfs\06_Manual_del_Estudiante_V3.pdf (Pág. 1)",
    "/app/agents/agent_faq/data/pdfs/06_Manual_del_Estudiante_V3.pdf (Pág. 1)",
    "06_Manual_del_Estudiante_V3.pdf (Pág. 1)",
], ids=["windows", "linux", "solo-nombre"])
def test_la_fuente_nunca_lleva_la_ruta_de_una_pc(monkeypatch, ruta):
    monkeypatch.setattr(invocador_faq, "_agente_faq", AgenteFaqFalso({
        "respuesta": "Del 1 de noviembre al 31 de diciembre.", "encontrado": True, "fuente": ruta,
    }))

    respuesta = responder_con_agente_faq(_mensaje_contrato())

    assert respuesta.fuentes == ["06_Manual_del_Estudiante_V3.pdf (Pág. 1)"]


def test_faq_que_falla_no_rompe_el_lote(monkeypatch):
    monkeypatch.setattr(invocador_faq, "_agente_faq", AgenteFaqFalso(error=RuntimeError("sin cupo")))

    respuesta = responder_con_agente_faq(_mensaje_contrato())

    assert (respuesta.texto, respuesta.encontrada, respuesta.fuentes) == ("", False, [])
    assert "RuntimeError" in respuesta.motivo


# ── Caso 7: el JSON Schema publicado coincide con los modelos ─────────────────

def test_el_json_schema_publicado_esta_al_dia():
    publicado = contrato_ia.ARCHIVO_ESQUEMA.read_text(encoding="utf-8")

    assert json.loads(publicado) == json.loads(contrato_ia.esquema_como_texto()), (
        "Regenerar con: python -m agents.orquestador.contrato_ia"
    )


def test_la_lista_de_temas_es_la_acordada():
    assert contrato_ia.TEMAS == (
        "inscripciones", "becas_pagos", "calendario_clases", "evaluaciones", "contenido_curso",
        "herramientas_entorno", "plataforma_acceso", "proyectos", "empleo", "comunidad", "otro",
    )


# ── T05: la puerta vieja /procesar ya no existe (el bot pasa por Java) ──────

def test_la_puerta_vieja_procesar_ya_no_existe():
    webhook = {"mensajes": [{"id": "1", "channel_id": "2", "content": "¿Cuándo empiezan las inscripciones?"}]}

    r = TestClient(api.app).post("/procesar", json=webhook)

    assert r.status_code == 404


# ── T05: tope total de un pedido en tiempoReal (DEC-54) ───────────────────────

class FaqLento:
    """Un Agente FAQ que tarda más que el tope."""

    def __init__(self, demora_s: float):
        self.demora_s = demora_s
        self.preguntas = []

    def __call__(self, mensaje):
        self.preguntas.append(mensaje.id)
        time.sleep(self.demora_s)
        return RespuestaFaq(texto="tarde", encontrada=True, fuentes=["x.pdf"])


def _cliente_con(procesador) -> TestClient:
    api._procesador_v1 = procesador
    return TestClient(api.app, headers={"X-Api-Key": CLAVE_IA})


@pytest.fixture
def restaurar_procesador(monkeypatch):
    monkeypatch.setattr(api, "_procesador_v1", None)


def test_si_el_faq_supera_el_tope_responde_a_tiempo_con_encontrada_false(restaurar_procesador):
    faq = FaqLento(demora_s=1.0)
    cliente = _cliente_con(ProcesadorV1(EtiquetadorLLM(LLMFalso()), faq, tope_tiempo_real_s=0.3))
    inicio = time.perf_counter()

    r = cliente.post("/v1/procesar", json=_lote([_duda(), _logro()], modo="tiempoReal"))

    assert time.perf_counter() - inicio < 0.9  # no esperó al Agente FAQ
    assert r.status_code == 200
    duda = _por_id(r)["1554205178671009863"]
    assert (duda["estado"], duda["intencion"], duda["tema"]) == ("OK", "PREGUNTA_FAQ", "herramientas_entorno")
    assert duda["respuesta"] == {"texto": "", "encontrada": False, "fuentes": [],
                                 "motivo": "Se agotó el tope de 0.3 s del pedido en tiempo real."}
    assert _por_id(r)["1554205393054466139"]["estado"] == "OK"  # el logro conserva sus etiquetas
    assert faq.preguntas == ["1554205178671009863"]
    contrato_ia.RespuestaLote.model_validate(r.json())  # el agregado no cambia el formato


def test_el_tope_tambien_corta_al_clasificador(restaurar_procesador):
    faq = FaqLento(demora_s=0.0)
    llm = LLMFalso(demora_s=1.0)
    cliente = _cliente_con(ProcesadorV1(EtiquetadorLLM(llm, timeout_s=5), faq, tope_tiempo_real_s=0.2))
    inicio = time.perf_counter()

    r = cliente.post("/v1/procesar", json=_lote([_duda()], modo="tiempoReal"))

    assert time.perf_counter() - inicio < 0.8
    res = r.json()["resultados"][0]
    assert res["estado"] == "ERROR" and res["intencion"] is None  # F4: sin etiquetas inventadas
    assert faq.preguntas == []


def test_con_tiempo_de_sobra_el_tope_no_cambia_nada(restaurar_procesador):
    faq = FaqLento(demora_s=0.0)
    cliente = _cliente_con(ProcesadorV1(EtiquetadorLLM(LLMFalso()), faq, tope_tiempo_real_s=5))

    r = cliente.post("/v1/procesar", json=_lote([_duda()], modo="tiempoReal"))

    assert r.json()["resultados"][0]["respuesta"]["encontrada"] is True


def test_en_historial_no_hay_tope(restaurar_procesador):
    llm = LLMFalso(demora_s=0.3)
    cliente = _cliente_con(ProcesadorV1(EtiquetadorLLM(llm, timeout_s=5), FaqLento(0.0), tope_tiempo_real_s=0.1))

    r = cliente.post("/v1/procesar", json=_lote([_logro()], modo="historial"))

    assert r.json()["resultados"][0]["estado"] == "OK"


# ── S2 (T04): /v1/procesar exige la API key de Java ───────────────────────────

def test_sin_clave_es_401_y_no_llama_al_llm(cliente):
    cliente()  # arma el procesador con el LLM falso
    r = TestClient(api.app).post("/v1/procesar", json=_lote([_logro()]), headers={"X-Id-Correlacion": "corr-1"})

    assert r.status_code == 401
    assert r.json() == {"codigo": "NO_AUTORIZADO", "mensaje": "Falta la cabecera X-Api-Key o la clave no es válida.",
                        "errores": [], "idCorrelacion": "corr-1"}
    assert cliente.llm.llamadas == 0


def test_con_clave_incorrecta_es_401(cliente):
    cliente()
    r = TestClient(api.app).post("/v1/procesar", json=_lote([_logro()]), headers={"X-Api-Key": "otra-clave"})

    assert r.status_code == 401
    assert "otra-clave" not in r.text and CLAVE_IA not in r.text
    assert cliente.llm.llamadas == 0


def test_sin_clave_configurada_en_la_ia_se_rechaza_todo(cliente, monkeypatch):
    monkeypatch.setattr(config_orq, "API_KEY_IA", "")

    r = cliente().post("/v1/procesar", json=_lote([_logro()]))  # aunque envíe una clave

    assert r.status_code == 401


def test_la_clave_se_revisa_antes_que_el_cuerpo(cliente):
    cliente()
    r = TestClient(api.app).post("/v1/procesar", content=b"{no es json", headers={"Content-Type": "application/json"})

    assert r.status_code == 401  # sin clave no se le dice nada del contrato


def test_health_no_pide_clave():
    r = TestClient(api.app).get("/health")

    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_el_json_schema_incluye_el_error_no_autorizado():
    codigos = contrato_ia.generar_esquema()["error"]["properties"]["codigo"]["enum"]
    assert codigos == ["CONTRATO_INVALIDO", "NO_AUTORIZADO", "ERROR_INTERNO"]
