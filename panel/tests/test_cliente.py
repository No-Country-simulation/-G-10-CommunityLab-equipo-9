"""cliente_java.py contra un Java simulado (httpx.MockTransport): cabeceras, cuerpos y errores (PANEL_JAVA_v1.md)."""
import json

import httpx
import pytest

from cliente_java import ClienteJava, ErrorJava

CLAVE = "clave-del-panel-de-prueba"


def _cliente(responder):
    pedidos = []

    def manejar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return responder(pedido)

    return ClienteJava("http://java:8080/", CLAVE, transport=httpx.MockTransport(manejar)), pedidos


def _ok(cuerpo):
    return lambda pedido: httpx.Response(200, json=cuerpo)


def test_cada_pedido_lleva_la_clave_y_los_cambios_llevan_el_usuario():
    cliente, pedidos = _cliente(_ok({"borradores": []}))

    cliente.listar_borradores(estado="APROBADO", tipo="FAQ")
    cliente.aprobar(5, "harrison", True, 42)

    listar, aprobar = pedidos
    assert listar.method == "GET"
    assert listar.url.path == "/api/v1/borradores"
    assert dict(listar.url.params) == {"estado": "APROBADO", "tipo": "FAQ", "limite": "100"}
    assert listar.headers["X-Api-Key"] == CLAVE
    assert "X-Usuario" not in listar.headers
    assert aprobar.headers["X-Api-Key"] == CLAVE
    assert aprobar.headers["X-Usuario"] == "harrison"


def test_aprobar_envia_consentimiento_tiempo_y_la_edicion_solo_si_hay():
    cliente, pedidos = _cliente(_ok({}))

    cliente.aprobar(5, "harrison", True, 42)
    cliente.aprobar(6, "harrison", False, 3, texto_final="Texto editado")

    assert pedidos[0].url.path == "/api/v1/borradores/5/aprobar"
    assert json.loads(pedidos[0].content) == {"consentimiento": True, "tiempoCuraduriaSeg": 42}
    assert json.loads(pedidos[1].content) == {"consentimiento": False, "tiempoCuraduriaSeg": 3,
                                              "textoFinal": "Texto editado"}


def test_los_post_y_put_llevan_content_length_aunque_no_tengan_datos():
    # Java responde 411 sin Content-Length (LimiteCuerpoFilter, observación de T03)
    cliente, pedidos = _cliente(_ok({}))

    cliente.reintentar("generacion", 9, "harrison")
    cliente.rechazar(5, "harrison", None, None)
    cliente.editar(5, "harrison", "nuevo")

    reintentar, rechazar, editar = pedidos
    assert reintentar.url.path == "/api/v1/errores/generacion/9/reintentar"
    assert reintentar.method == "POST" and reintentar.headers["Content-Length"] == "2"  # {}
    assert json.loads(rechazar.content) == {}
    assert int(rechazar.headers["Content-Length"]) > 0
    assert editar.method == "PUT" and json.loads(editar.content) == {"textoFinal": "nuevo"}
    assert int(editar.headers["Content-Length"]) > 0


def test_un_error_de_java_se_convierte_en_error_java_con_su_campo():
    cuerpo = {"codigo": "DATO_INVALIDO", "mensaje": "Hay que confirmar el consentimiento (D6).",
              "errores": [{"campo": "consentimiento", "problema": "…"}], "idCorrelacion": "x"}
    cliente, _ = _cliente(lambda pedido: httpx.Response(422, json=cuerpo))

    with pytest.raises(ErrorJava) as e:
        cliente.aprobar(5, "harrison", False, 1)

    assert e.value.estado == 422
    assert e.value.codigo == "DATO_INVALIDO"
    assert e.value.campo == "consentimiento"
    assert "consentimiento" in e.value.mensaje


def test_un_409_y_una_respuesta_que_no_es_json():
    cliente, _ = _cliente(lambda pedido: httpx.Response(409, json={"codigo": "CONFLICTO", "mensaje": "Ya no está PENDIENTE"}))
    with pytest.raises(ErrorJava) as e:
        cliente.rechazar(5, "harrison", "x", 1)
    assert e.value.estado == 409

    cliente, _ = _cliente(lambda pedido: httpx.Response(502, text="<html>Bad gateway</html>"))
    with pytest.raises(ErrorJava) as e:
        cliente.errores()
    assert e.value.estado == 502
    assert "<html>" not in e.value.mensaje


def test_sin_conexion_da_un_mensaje_claro_sin_detalles_internos():
    def caido(pedido):
        raise httpx.ConnectError("Connection refused to api-java:8080")

    cliente, _ = _cliente(caido)

    with pytest.raises(ErrorJava) as e:
        cliente.listar_borradores()

    assert e.value.estado == 0
    assert "api-java" not in e.value.mensaje


def test_una_etapa_desconocida_no_sale_del_panel():
    cliente, pedidos = _cliente(_ok({}))

    with pytest.raises(ValueError):
        cliente.reintentar("../borradores", 1, "harrison")

    assert pedidos == []


def test_el_dashboard_envia_fechas_iso_y_booleanos_de_java_sin_usuario():
    from datetime import date

    cliente, pedidos = _cliente(_ok({}))

    cliente.dashboard_sentimiento(date(2026, 9, 1), date(2026, 9, 30), "semana", True)
    cliente.dashboard_dudas(date(2026, 9, 1), date(2026, 9, 30), 48, False)
    cliente.dashboard_desercion(3)

    sentimiento, dudas, desercion = pedidos
    assert sentimiento.url.path == "/api/v1/dashboard/sentimiento"
    assert dict(sentimiento.url.params) == {"desde": "2026-09-01", "hasta": "2026-09-30", "agrupar": "semana",
                                            "excluirOtro": "true"}
    assert dudas.url.path == "/api/v1/dashboard/dudas-sin-responder"
    assert dict(dudas.url.params)["excluirOtro"] == "false"
    assert dict(dudas.url.params)["horas"] == "48"
    assert dict(desercion.url.params) == {"dias": "3"}
    for p in pedidos:
        assert p.method == "GET"
        assert p.headers["X-Api-Key"] == CLAVE
        assert "X-Usuario" not in p.headers  # solo lectura
