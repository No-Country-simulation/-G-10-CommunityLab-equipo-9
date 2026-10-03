"""El envío a backend con la opción C (etiqueta + caja) y el marcador."""
import httpx
import pytest

from datos_prueba import WEBHOOK_AJENO, contexto, crudo
from send_batch import EnvioError, a_formato_backend, enviar, nuevos_marcadores
from transform import a_contrato, armar_lote

URL = "http://backend.prueba/api/v1/community/process"


def lote_de_prueba(*crudos):
    mensajes = [a_contrato(c, "dudas", contexto()) for c in (crudos or [crudo()])]
    return armar_lote(mensajes, modo="historial", servidor_id="1554157903701741700")


def test_etiqueta_y_caja():
    lote = lote_de_prueba()
    cuerpo = a_formato_backend(lote)
    interaccion = cuerpo["interacciones"][0]
    assert cuerpo["loteId"] == lote.lote_id and cuerpo["tipoServidor"] == "discord"
    # La etiqueta: los campos de backend, con sus nombres.
    assert interaccion["discordId"] == "1554205178671009863"
    assert interaccion["authorId"] == "sim-ana-perez"
    assert interaccion["tipoAutor"] == "HUMANO"
    assert interaccion["timestampMensaje"] == "2026-09-28T18:56:30.331Z"
    # La caja: el mensaje completo del contrato, sin cambios.
    assert interaccion["mensajeContrato"] == lote.mensajes[0].model_dump(mode="json")


def test_otro_bot_se_envia_como_bot():
    otro = crudo(webhook_id=WEBHOOK_AJENO, author={"id": WEBHOOK_AJENO, "username": "GitHub", "bot": True})
    assert a_formato_backend(lote_de_prueba(otro))["interacciones"][0]["tipoAutor"] == "BOT"


def cliente_falso(estado: int, cuerpo: dict) -> httpx.Client:
    """Un backend de mentira: responde siempre lo mismo, sin salir a internet."""
    return httpx.Client(transport=httpx.MockTransport(lambda peticion: httpx.Response(estado, json=cuerpo)))


def test_envio_confirmado():
    recibo = {"status": "exitoso", "loteId": "x", "totalMensajesRecibidos": 1}
    with cliente_falso(200, recibo) as http:
        assert enviar({"interacciones": []}, URL, http) == recibo


def test_envio_rechazado():
    with cliente_falso(400, {"status": 400, "error": "Bad Request"}) as http, pytest.raises(EnvioError):
        enviar({"interacciones": []}, URL, http)


def test_el_marcador_avanza_y_nunca_retrocede():
    lote = lote_de_prueba(crudo(id="200"), crudo(id="300"))
    canal = lote.mensajes[0].canal.id
    assert nuevos_marcadores(lote, {}) == {canal: "300"}
    assert nuevos_marcadores(lote, {canal: "500"}) == {canal: "500"}
