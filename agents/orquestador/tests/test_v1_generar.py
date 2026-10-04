"""
Pruebas de POST /v1/generar y del Agente-Mod (T06), con un LLM falso: no gastan Gemini.
Los mensajes se arman con la transformación real de la ingesta, igual que lo hace Java.
Correr desde la raíz del repositorio:  python -m pytest agents/orquestador/tests -q
"""
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agents.agent_mod import agente_mod
from agents.agent_mod.agente_mod import AgenteMod, RedaccionLLM
from agents.orquestador import api, contrato_ia
from agents.orquestador import config as config_orq

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "ingestion" / "discord"))
sys.path.insert(0, str(RAIZ / "ingestion" / "discord" / "tests"))
import datos_prueba as dp  # noqa: E402
from transform import a_contrato  # noqa: E402

CLAVE_IA = "clave-de-prueba-ia"
LOGRO_ID = "1556321890585419808"
POST = "🎉 Camila consiguió su primer trabajo en tecnología. \"me contrataron!!!!!\" #CommunityLab #Bootcamp #Empleabilidad"
CASO = "Situación: … Desafío: … Logro: … En sus palabras: \"me contrataron!!!!!\" Cierre: …"


# ── Dobles de prueba ──────────────────────────────────────────────────────────

class UsoFalso:
    usage_metadata = {"input_tokens": 900, "output_tokens": 350}


class LLMRedactorFalso:
    """Imita a un chat model con with_structured_output(include_raw=True). Guarda lo que recibe."""

    def __init__(self, falla=None, demora_s=0.0, redaccion=None):
        self.falla, self.demora_s, self.redaccion = falla, demora_s, redaccion
        self.entradas = []

    def with_structured_output(self, esquema, include_raw=False):
        assert esquema is RedaccionLLM and include_raw
        return self

    def invoke(self, entrada):
        self.entradas.append(entrada)
        if self.demora_s:
            time.sleep(self.demora_s)
        if self.falla:
            raise self.falla
        if self.redaccion is not None:
            return {"raw": UsoFalso(), "parsed": self.redaccion, "parsing_error": None}
        texto = entrada[-1].content.lower()
        if "recursividad" in texto:  # un avance pequeño: la guía dice que no se publica
            parsed = RedaccionLLM(publicable=False, motivo="Es un avance de aprendizaje del día a día.")
        else:
            parsed = RedaccionLLM(publicable=True, motivo="Es una contratación.", post_linkedin=POST, caso_exito=CASO)
        return {"raw": UsoFalso(), "parsed": parsed, "parsing_error": None}

    @property
    def sistema(self):
        return self.entradas[-1][0].content

    @property
    def usuario(self):
        return self.entradas[-1][-1].content


# ── Mensajes (contrato v1 real) ───────────────────────────────────────────────

AUTORA = {"id": dp.PERSONA_REAL_ID, "username": "camila.rojas.dev", "global_name": "Camila Rojas", "discriminator": "0"}
MENTOR = {"id": "222222222222222222", "username": "andres.mentor", "global_name": "Andrés Gómez", "discriminator": "0"}


def _logro(content="me contrataron!!!!! después de 6 meses en el bootcamp, empiezo el lunes como QA trainee"):
    crudo = dp.crudo_real(id=LOGRO_ID, author=dict(AUTORA), content=content,
                          reactions=[{"emoji": {"id": None, "name": "🎉"}, "count": 12}])
    return a_contrato(crudo, "logros", dp.contexto()).model_dump(mode="json")


def _respuesta(id_, content):
    crudo = dp.crudo_real(id=id_, author=dict(MENTOR), content=content, type=19,
                          message_reference={"message_id": LOGRO_ID})
    return a_contrato(crudo, "logros", dp.contexto(roles_por_autor={MENTOR["id"]: [dp.ROL_MENTOR_ID]})).model_dump(mode="json")


def _pedido(logro=None, respuestas=()):
    return {"versionContrato": "1.0", "pedidoId": "gen-1", "logro": logro or _logro(), "respuestas": list(respuestas)}


@pytest.fixture(autouse=True)
def clave_ia(monkeypatch):
    monkeypatch.setattr(config_orq, "API_KEY_IA", CLAVE_IA)


@pytest.fixture
def cliente(monkeypatch):
    """Cliente HTTP con el Agente-Mod armado con un LLM falso y la guía de voz real."""
    def usar(llm=None, timeout_s=5.0):
        llm = llm or LLMRedactorFalso()
        monkeypatch.setattr(api, "_agente_mod", AgenteMod(llm, timeout_s=timeout_s))
        usar.llm = llm
        return TestClient(api.app, headers={"X-Api-Key": CLAVE_IA})
    return usar


# ── Caso 1: un logro publicable ───────────────────────────────────────────────

def test_un_logro_publicable_trae_los_dos_textos(cliente):
    r = cliente().post("/v1/generar", json=_pedido())

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo == {
        "versionContratoIa": "1.0", "pedidoId": "gen-1", "discordId": LOGRO_ID, "estado": "OK",
        "publicable": True, "motivo": "Es una contratación.", "postLinkedin": POST, "casoExito": CASO,
        "metricas": {"duracionMs": cuerpo["metricas"]["duracionMs"], "tokensIn": 900, "tokensOut": 350},
    }
    contrato_ia.RespuestaGenerar.model_validate(cuerpo)  # cumple el JSON Schema publicado


# ── Caso 2: un logro menor ────────────────────────────────────────────────────

def test_un_logro_menor_no_es_publicable_y_no_trae_textos(cliente):
    r = cliente().post("/v1/generar", json=_pedido(_logro("por fin entendí recursividad 🥲")))

    cuerpo = r.json()
    assert (cuerpo["estado"], cuerpo["publicable"]) == ("OK", False)
    assert cuerpo["motivo"] == "Es un avance de aprendizaje del día a día."
    assert cuerpo["postLinkedin"] is None and cuerpo["casoExito"] is None


def test_si_el_llm_dice_no_publicable_pero_igual_escribe_se_descartan_los_textos(cliente):
    llm = LLMRedactorFalso(redaccion=RedaccionLLM(publicable=False, motivo="menor", post_linkedin="x", caso_exito="y"))

    cuerpo = cliente(llm).post("/v1/generar", json=_pedido()).json()

    assert (cuerpo["publicable"], cuerpo["postLinkedin"], cuerpo["casoExito"]) == (False, None, None)


# ── Caso 3: el LLM falla o se agota el tiempo ─────────────────────────────────

def test_si_el_llm_falla_es_error_sin_textos(cliente):
    r = cliente(LLMRedactorFalso(falla=RuntimeError("429 cupo agotado"))).post("/v1/generar", json=_pedido())

    cuerpo = r.json()
    assert r.status_code == 200
    assert (cuerpo["estado"], cuerpo["publicable"], cuerpo["postLinkedin"], cuerpo["casoExito"]) == ("ERROR", None, None, None)
    assert "RuntimeError" in cuerpo["motivo"] and "429" not in cuerpo["motivo"]  # el detalle va al registro


def test_si_el_llm_no_responde_a_tiempo_es_error_y_no_espera(cliente):
    inicio = time.perf_counter()

    cuerpo = cliente(LLMRedactorFalso(demora_s=1.0), timeout_s=0.2).post("/v1/generar", json=_pedido()).json()

    assert time.perf_counter() - inicio < 0.9
    assert cuerpo["estado"] == "ERROR" and "no respondió en 0.2 s" in cuerpo["motivo"]


def test_publicable_con_un_texto_vacio_es_error_y_no_un_borrador_a_medias(cliente):
    llm = LLMRedactorFalso(redaccion=RedaccionLLM(publicable=True, motivo="sí", post_linkedin=POST, caso_exito="  "))

    cuerpo = cliente(llm).post("/v1/generar", json=_pedido()).json()

    assert cuerpo["estado"] == "ERROR" and cuerpo["postLinkedin"] is None  # F4


def test_sin_llm_configurado_es_error():
    agente = AgenteMod(None, timeout_s=1)

    r = agente.redactar(contrato_ia.MensajeContrato.model_validate(_logro()), [])

    assert r.error and "no está configurado" in r.error and r.publicable is None


# ── Caso 4: lo que recibe el LLM (DEC-81) ─────────────────────────────────────

def test_el_llm_recibe_solo_el_primer_nombre_y_ningun_dato_personal(cliente):
    respuesta = _respuesta("1556321900000000001", f"<@{dp.PERSONA_REAL_ID}> felicitaciones Camila!! 👏")

    cliente().post("/v1/generar", json=_pedido(respuestas=[respuesta]))

    usuario = cliente.llm.usuario
    assert "Primer nombre del alumno: Camila" in usuario
    assert "me contrataron!!!!! después de 6 meses" in usuario  # el texto exacto, para la cita
    assert "felicitaciones Camila!!" in usuario and 'rol="mentor"' in usuario
    assert "Reacciones de la comunidad: 12 (🎉)" in usuario
    for prohibido in ["Camila Rojas", "Rojas", "camila.rojas.dev", "Andrés", "Gómez", "andres.mentor",
                      dp.PERSONA_REAL_ID, MENTOR["id"], LOGRO_ID, "1556321900000000001", dp.CANAL_DUDAS]:
        assert prohibido not in usuario, prohibido
        assert prohibido not in cliente.llm.sistema, prohibido


def test_si_el_alumno_escribio_su_nombre_completo_no_llega_al_borrador(cliente):
    llm = LLMRedactorFalso(redaccion=RedaccionLLM(
        publicable=True, motivo="sí", post_linkedin="Soy Camila Rojas y me contrataron (camila.rojas.dev)",
        caso_exito="En sus palabras: \"Soy CAMILA ROJAS\""))

    cuerpo = cliente(llm).post("/v1/generar", json=_pedido()).json()

    assert cuerpo["postLinkedin"] == "Soy Camila y me contrataron (Camila)"
    assert cuerpo["casoExito"] == "En sus palabras: \"Soy Camila\""


def test_el_primer_nombre_y_las_menciones():
    assert agente_mod.primer_nombre("Camila Rojas") == "Camila"
    assert agente_mod.primer_nombre("camila_dev") == "Camila"
    assert agente_mod.primer_nombre("🦄 ") is None and agente_mod.primer_nombre("") is None
    assert agente_mod.sin_menciones("<@123> <@!45> <@&67> <#89> hola") == "@alguien @alguien @alguien @alguien hola"


def test_sin_nombre_respeta_las_palabras_enteras():
    caja = _logro()
    caja["autor"]["nombreUsuario"] = "ana"  # corto: no se toca
    caja["autor"]["nombreVisible"] = "Luis Ana"
    logro = contrato_ia.MensajeContrato.model_validate(caja)

    assert agente_mod.sin_nombre_completo("Luis Ana vuelve mañana", logro) == "Luis vuelve mañana"


# ── Caso 5: la guía de voz llega al LLM desde el archivo ──────────────────────

def test_la_guia_de_voz_llega_al_llm_desde_el_archivo(cliente, tmp_path):
    cliente().post("/v1/generar", json=_pedido())
    assert agente_mod.ARCHIVO_GUIA.read_text(encoding="utf-8") in cliente.llm.sistema
    assert "#CommunityLab" in cliente.llm.sistema  # una línea de la guía real

    otra = tmp_path / "guia.md"
    otra.write_text("Tono: pirata. Siempre di arrr.", encoding="utf-8")
    llm = LLMRedactorFalso()
    AgenteMod(llm, timeout_s=5, archivo_guia=otra).redactar(contrato_ia.MensajeContrato.model_validate(_logro()), [])
    assert llm.sistema.endswith("Tono: pirata. Siempre di arrr.")  # cambiar el archivo cambia la voz


# ── Caso 6: clave y cuerpo inválido ───────────────────────────────────────────

def test_sin_clave_es_401_y_no_llama_al_llm(cliente):
    cliente()
    r = TestClient(api.app).post("/v1/generar", json=_pedido(), headers={"X-Id-Correlacion": "corr-9"})

    assert r.status_code == 401
    assert r.json()["codigo"] == "NO_AUTORIZADO" and r.json()["idCorrelacion"] == "corr-9"
    assert cliente.llm.entradas == []


def test_un_cuerpo_invalido_es_422_sin_repetir_los_datos(cliente):
    pedido = _pedido()
    pedido["logro"]["autor"]["tipo"] = "HUMANO"
    del pedido["pedidoId"]

    r = cliente().post("/v1/generar", json=pedido, headers={"X-Id-Correlacion": "corr-1"})

    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["codigo"] == "CONTRATO_INVALIDO" and cuerpo["idCorrelacion"] == "corr-1"
    assert {"pedidoId", "logro.autor.tipo"} <= {e["campo"] for e in cuerpo["errores"]}
    assert "HUMANO" not in r.text and "me contrataron" not in r.text  # S7
    assert cliente.llm.entradas == []


def test_mas_de_20_respuestas_es_422(cliente):
    respuestas = [_respuesta(str(1556321900000000000 + i), "felicitaciones") for i in range(21)]

    r = cliente().post("/v1/generar", json=_pedido(respuestas=respuestas))

    assert r.status_code == 422


# ── Contrato: solo agrega ─────────────────────────────────────────────────────

def test_el_json_schema_documenta_generar_y_procesar_no_cambio():
    esquema = contrato_ia.generar_esquema()
    assert set(esquema["generar"]) == {"pedido", "respuesta"}
    assert esquema["respuesta"]["title"] == "RespuestaLote"  # /v1/procesar sigue igual
    assert esquema["generar"]["pedido"]["properties"]["respuestas"]["maxItems"] == 20
