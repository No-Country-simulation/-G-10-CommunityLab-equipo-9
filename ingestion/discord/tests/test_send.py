"""El envío a la API Java: el lote del contrato v1 tal cual (D8), con la API key, y el marcador."""
import json

import httpx
import pytest

from datos_prueba import crudo, contexto
from send_batch import EnvioError, describir_recibo, enviar, nuevos_marcadores
from transform import a_contrato, armar_lote

URL = "http://java.prueba/api/v1/lotes"
CLAVE = "clave-de-prueba"


def lote_de_prueba(*crudos):
    mensajes = [a_contrato(c, "dudas", contexto()) for c in (crudos or [crudo()])]
    return armar_lote(mensajes, modo="historial", servidor_id="1554157903701741700")


def recibo_de(lote, **cambios) -> dict:
    recibo = {"loteId": lote.lote_id, "total": len(lote.mensajes), "nuevos": len(lote.mensajes),
              "actualizados": 0, "sinCambios": 0, "recibidoEn": "2026-10-03T20:00:00.123456Z", "yaRecibido": False}
    recibo.update(cambios)
    return recibo


def java_falso(estado: int, cuerpo: dict, pedidos: list | None = None) -> httpx.Client:
    """Una API Java de mentira: guarda los pedidos y responde siempre lo mismo, sin salir a internet."""
    def responder(pedido: httpx.Request) -> httpx.Response:
        if pedidos is not None:
            pedidos.append(pedido)
        return httpx.Response(estado, json=cuerpo)

    return httpx.Client(transport=httpx.MockTransport(responder))


def test_envia_el_lote_tal_cual_con_la_api_key():
    lote = lote_de_prueba()
    pedidos = []

    with java_falso(200, recibo_de(lote), pedidos) as http:
        enviar(lote, URL, CLAVE, http)

    (pedido,) = pedidos
    assert pedido.method == "POST" and str(pedido.url) == URL
    assert pedido.headers["X-Api-Key"] == CLAVE
    # El cuerpo es el contrato v1 sin convertir: los mismos nombres y valores que el lote
    assert json.loads(pedido.content) == lote.model_dump(mode="json")
    assert "interacciones" not in json.loads(pedido.content)  # ya no se usa la opción C


def test_envio_confirmado_devuelve_el_recibo():
    lote = lote_de_prueba()
    with java_falso(200, recibo_de(lote)) as http:
        assert enviar(lote, URL, CLAVE, http)["nuevos"] == 1


def test_un_lote_que_java_ya_tenia_tambien_se_confirma():
    lote = lote_de_prueba()
    with java_falso(200, recibo_de(lote, nuevos=0, sinCambios=1, yaRecibido=True)) as http:
        recibo = enviar(lote, URL, CLAVE, http)
    assert recibo["yaRecibido"] is True
    assert "ya lo tenía" in describir_recibo(recibo)


def test_clave_rechazada():
    lote = lote_de_prueba()
    error = {"codigo": "NO_AUTORIZADO", "mensaje": "…", "errores": [], "idCorrelacion": "x"}
    with java_falso(401, error) as http, pytest.raises(EnvioError, match="BACKEND_API_KEY") as e:
        enviar(lote, URL, CLAVE, http)
    assert CLAVE not in str(e.value)  # la clave nunca aparece en un mensaje


def test_envio_rechazado_por_el_contrato():
    lote = lote_de_prueba()
    error = {"codigo": "CONTRATO_INVALIDO", "mensaje": "…", "errores": [], "idCorrelacion": "x"}
    with java_falso(422, error) as http, pytest.raises(EnvioError, match="422"):
        enviar(lote, URL, CLAVE, http)


def test_un_recibo_de_otro_lote_no_confirma():
    lote = lote_de_prueba()
    with java_falso(200, recibo_de(lote, loteId="otro-lote")) as http, pytest.raises(EnvioError):
        enviar(lote, URL, CLAVE, http)


def test_el_marcador_avanza_y_nunca_retrocede():
    lote = lote_de_prueba(crudo(id="200"), crudo(id="300"))
    canal = lote.mensajes[0].canal.id
    assert nuevos_marcadores(lote, {}) == {canal: "300"}
    assert nuevos_marcadores(lote, {canal: "500"}) == {canal: "500"}
