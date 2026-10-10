"""
Pruebas del bot (T05), sin conectarse a Discord ni a Java: usan mensajes, canales y una sesión HTTP falsos.
Los mensajes crudos son los de las pruebas de la ingesta (datos_prueba.py).
Correr desde la raíz del repositorio:  python -m pytest agents/bot_discord/tests -q
"""
import asyncio
import logging
import sys
from pathlib import Path

import aiohttp
import pytest

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "agents" / "bot_discord"))
sys.path.insert(0, str(RAIZ / "ingestion" / "discord" / "tests"))

import bot_communitylab as bot  # noqa: E402  (agrega ingestion/discord a sys.path)
import datos_prueba as dp  # noqa: E402
from transform import a_contrato  # noqa: E402

SERVIDOR = "1554157903701741700"
CANAL_LOGROS = "1554158212742127999"
TEXTO_ALUMNO = dp.crudo()["content"]
TEXTO_IA = "Marca la casilla 'Add python.exe to PATH'. @everyone"

AJUSTES = bot.Ajustes(
    token="token-falso", api_key="clave-bot-falsa", url_java="http://api-java:8080",
    canales={dp.CANAL_DUDAS: "dudas", CANAL_LOGROS: "logros"},
    webhooks_propios=frozenset({dp.WEBHOOK_DUDAS}),
    roles_mentor=frozenset({dp.ROL_MENTOR_ID}), roles_staff=frozenset({dp.ROL_STAFF_ID}),
    mentores_simulados=frozenset({"sim-andres-mentor"}),
)


# ── Dobles de prueba ──────────────────────────────────────────────────────────

class Rol:
    def __init__(self, id_, por_defecto=False):
        self.id, self._por_defecto = int(id_), por_defecto

    def is_default(self):
        return self._por_defecto


class Autor:
    def __init__(self, id_, bot_=False, roles=()):
        self.id, self.bot, self.roles = int(id_), bot_, list(roles)


class Escribiendo:
    def __init__(self, canal):
        self.canal = canal

    async def __aenter__(self):
        self.canal.escribiendo += 1

    async def __aexit__(self, *_):
        return False


class Canal:
    def __init__(self, id_):
        self.id, self.escribiendo = int(id_), 0

    def typing(self):
        return Escribiendo(self)


class Servidor:
    def __init__(self):
        self.id, self.self_role = int(SERVIDOR), Rol(dp.ROL_BOT_ID)


class Mensaje:
    """Lo que el bot usa de un discord.Message."""

    def __init__(self, crudo, canal_id=dp.CANAL_DUDAS, autor=None, servidor=True):
        self.crudo = crudo
        self.id = int(crudo["id"])
        self.channel = Canal(canal_id)
        self.guild = Servidor() if servidor else None
        self.webhook_id = int(crudo["webhook_id"]) if crudo.get("webhook_id") else None
        a = crudo["author"]
        self.author = autor or Autor(a["id"], a.get("bot", False))
        self.respuestas, self.reacciones = [], []

    async def reply(self, texto, **opciones):
        self.respuestas.append((texto, opciones))

    async def add_reaction(self, emoji):
        self.reacciones.append(emoji)


class RespuestaHttp:
    def __init__(self, status, cuerpo):
        self.status, self._cuerpo = status, cuerpo

    async def json(self):
        return self._cuerpo


class Pedido:
    def __init__(self, sesion):
        self.sesion = sesion

    async def __aenter__(self):
        if self.sesion.error:
            raise self.sesion.error
        return RespuestaHttp(self.sesion.status, self.sesion.cuerpo)

    async def __aexit__(self, *_):
        return False


class SesionFalsa:
    """Imita a aiohttp.ClientSession.post y guarda lo que se envió a Java."""

    def __init__(self, status=200, cuerpo=None, error=None):
        self.status, self.cuerpo, self.error = status, cuerpo, error
        self.pedidos = []

    def post(self, url, json, headers, timeout):
        self.pedidos.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return Pedido(self)


def orden(tipo, texto=None, reaccion=None):
    return {"versionContratoBot": "1.0", "discordId": "1554205178671009863", "orden": tipo,
            "texto": texto, "reaccion": reaccion}


def atender(mensaje, sesion):
    return asyncio.run(bot.atender(mensaje, AJUSTES, int(dp.BOT_ID), sesion, leer=lambda *_: mensaje.crudo))


# ── Qué mensajes se procesan ─────────────────────────────────────────────────

def test_un_canal_no_permitido_se_ignora():
    assert not bot.debe_procesar(Mensaje(dp.crudo_real(), canal_id="123"), int(dp.BOT_ID), AJUSTES)


def test_un_mensaje_propio_se_ignora():
    propio = dp.crudo_real(author={"id": dp.BOT_ID, "username": "CommunityLab", "bot": True})
    assert not bot.debe_procesar(Mensaje(propio), int(dp.BOT_ID), AJUSTES)


def test_otro_bot_o_un_webhook_ajeno_se_ignoran():
    otro_bot = dp.crudo_real(author={"id": "222", "username": "github", "bot": True})
    ajeno = dp.crudo(webhook_id=dp.WEBHOOK_AJENO)
    assert not bot.debe_procesar(Mensaje(otro_bot), int(dp.BOT_ID), AJUSTES)
    assert not bot.debe_procesar(Mensaje(ajeno), int(dp.BOT_ID), AJUSTES)


def test_un_webhook_propio_se_procesa():
    assert bot.debe_procesar(Mensaje(dp.crudo()), int(dp.BOT_ID), AJUSTES)  # alumna simulada


def test_una_persona_en_logros_se_procesa_y_un_mensaje_directo_no():
    assert bot.debe_procesar(Mensaje(dp.crudo_real(), canal_id=CANAL_LOGROS), int(dp.BOT_ID), AJUSTES)
    assert not bot.debe_procesar(Mensaje(dp.crudo_real(), servidor=False), int(dp.BOT_ID), AJUSTES)


def test_un_mensaje_sin_texto_se_procesa():
    assert bot.debe_procesar(Mensaje(dp.crudo_real(content="")), int(dp.BOT_ID), AJUSTES)


# ── El contrato es el mismo que arma la ingesta (C2) ─────────────────────────

def _igual_que_la_ingesta(crudo, mensaje):
    ctx_bot = bot.contexto_para(mensaje, int(dp.BOT_ID), AJUSTES)
    del_bot = bot.armar_lote_en_vivo(crudo, "dudas", ctx_bot, SERVIDOR)
    de_la_ingesta = a_contrato(crudo, "dudas", dp.contexto()).model_dump(mode="json")
    assert del_bot["modo"] == "tiempoReal" and del_bot["servidorId"] == SERVIDOR
    assert len(del_bot["mensajes"]) == 1
    assert del_bot["mensajes"][0] == de_la_ingesta
    return del_bot["mensajes"][0]


def test_el_contrato_de_una_alumna_simulada_es_igual_al_de_la_ingesta():
    caja = _igual_que_la_ingesta(dp.crudo(), Mensaje(dp.crudo()))
    assert caja["esSimulado"] is True and caja["autor"]["tipo"] == "persona"


def test_el_contrato_de_un_mentor_real_que_menciona_al_bot_es_igual_al_de_la_ingesta():
    crudo = dp.crudo_real(mention_roles=[dp.ROL_BOT_ID], content="@CommunityLab ¿cuándo es la clase?")
    # discord.py incluye @everyone en los roles; la ingesta no: no tiene que cambiar nada
    mentor = Autor(dp.PERSONA_REAL_ID, roles=[Rol(SERVIDOR, por_defecto=True), Rol(dp.ROL_MENTOR_ID)])

    caja = _igual_que_la_ingesta(crudo, Mensaje(crudo, autor=mentor))

    assert caja["autor"]["rol"] == "mentor" and caja["mencionaAlBot"] is True


# ── Lo que se envía a Java ────────────────────────────────────────────────────

def test_envia_a_java_el_contrato_con_la_clave_y_espera_40_s():
    mensaje, sesion = Mensaje(dp.crudo()), SesionFalsa(cuerpo=orden("NADA"))

    atender(mensaje, sesion)

    (pedido,) = sesion.pedidos
    assert pedido["url"] == "http://api-java:8080/api/v1/mensajes/en-vivo"
    assert pedido["headers"]["X-Api-Key"] == "clave-bot-falsa"
    assert pedido["headers"]["X-Id-Correlacion"] == pedido["json"]["loteId"]
    assert pedido["timeout"].total == 40
    assert pedido["json"]["modo"] == "tiempoReal"
    assert [m["id"] for m in pedido["json"]["mensajes"]] == ["1554205178671009863"]
    assert mensaje.channel.escribiendo == 1  # "escribiendo…" mientras espera


# ── Las órdenes de Java ───────────────────────────────────────────────────────

def test_responder_responde_al_mensaje_con_las_menciones_desactivadas():
    mensaje = Mensaje(dp.crudo())

    assert atender(mensaje, SesionFalsa(cuerpo=orden("RESPONDER", texto=TEXTO_IA))) == "RESPONDER"

    ((texto, opciones),) = mensaje.respuestas
    assert texto == TEXTO_IA
    menciones = opciones["allowed_mentions"]
    assert (menciones.everyone, menciones.users, menciones.roles, menciones.replied_user) == (False, False, False, False)
    assert opciones["mention_author"] is False
    assert mensaje.reacciones == []


def test_derivar_responde_con_el_texto_de_java():
    mensaje = Mensaje(dp.crudo())

    atender(mensaje, SesionFalsa(cuerpo=orden("DERIVAR", texto="Un mentor te responderá pronto.")))

    assert [t for t, _ in mensaje.respuestas] == ["Un mentor te responderá pronto."]
    assert mensaje.respuestas[0][1]["allowed_mentions"].everyone is False


def test_reaccionar_pone_la_reaccion_sin_texto():
    mensaje = Mensaje(dp.crudo(content="me contrataron!!!"), canal_id=CANAL_LOGROS)

    assert atender(mensaje, SesionFalsa(cuerpo=orden("REACCIONAR", reaccion="🎉"))) == "REACCIONAR"

    assert mensaje.reacciones == ["🎉"]
    assert mensaje.respuestas == []  # F5


def test_nada_no_responde():
    mensaje = Mensaje(dp.crudo())

    assert atender(mensaje, SesionFalsa(cuerpo=orden("NADA"))) == "NADA"

    assert mensaje.respuestas == [] and mensaje.reacciones == []


@pytest.mark.parametrize("sesion", [
    SesionFalsa(status=500, cuerpo={"codigo": "ERROR_INTERNO"}),
    SesionFalsa(status=401, cuerpo={"codigo": "NO_AUTORIZADO"}),
    SesionFalsa(error=aiohttp.ClientConnectionError("Java caído")),
    SesionFalsa(error=asyncio.TimeoutError()),
    SesionFalsa(cuerpo={"orden": "PUBLICAR_EN_LINKEDIN"}),
], ids=["500", "401", "caido", "tiempo-agotado", "orden-desconocida"])
def test_si_java_falla_no_responde_nada(sesion):
    mensaje = Mensaje(dp.crudo())

    assert atender(mensaje, sesion) == "NADA"  # DEC-67

    assert mensaje.respuestas == [] and mensaje.reacciones == []


# ── S11: los registros no tienen el texto ─────────────────────────────────────

def test_los_registros_no_contienen_el_texto(caplog):
    caplog.set_level(logging.DEBUG)
    mensaje = Mensaje(dp.crudo())

    atender(mensaje, SesionFalsa(cuerpo=orden("RESPONDER", texto=TEXTO_IA)))
    atender(Mensaje(dp.crudo(id="1554205178671009999")), SesionFalsa(status=500))

    assert "1554205178671009863" in caplog.text and "RESPONDER" in caplog.text
    assert TEXTO_ALUMNO not in caplog.text and "pyhton" not in caplog.text
    assert TEXTO_IA not in caplog.text and "PATH" not in caplog.text


def test_un_error_inesperado_se_registra_sin_el_texto(caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    cliente = bot.BotCommunityLab(AJUSTES)
    cliente._connection.user = Autor(dp.BOT_ID, bot_=True)
    mensaje = Mensaje(dp.crudo())

    async def atender_que_falla(*_):
        # Como un ValidationError de pydantic, que repite el valor que no cumple el contrato
        raise ValueError(f"input_value='{TEXTO_ALUMNO}'")

    monkeypatch.setattr(bot, "atender", atender_que_falla)
    asyncio.run(cliente.on_message(mensaje))

    assert "no se pudo atender (ValueError)" in caplog.text
    assert TEXTO_ALUMNO not in caplog.text
    assert mensaje.respuestas == []


# ── Ajustes ───────────────────────────────────────────────────────────────────

def test_sin_api_key_del_bot_no_arranca(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token-falso")
    monkeypatch.setenv("DISCORD_CHANNEL_DUDAS_ID", dp.CANAL_DUDAS)
    monkeypatch.setenv("DISCORD_CHANNEL_LOGROS_ID", CANAL_LOGROS)
    monkeypatch.setenv("API_KEY_BOT", "")

    with pytest.raises(bot.AjustesError, match="API_KEY_BOT"):
        bot.cargar_ajustes()


def test_los_ajustes_no_muestran_secretos():
    assert "token-falso" not in repr(AJUSTES) and "clave-bot-falsa" not in repr(AJUSTES)
