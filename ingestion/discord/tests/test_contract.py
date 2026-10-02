"""Reglas del contrato: qué acepta y qué rechaza (docs/CONTRACT.md §1)."""
import json

import pytest
from pydantic import ValidationError

from contract import ARCHIVO_ESQUEMA, Lote, Mensaje, generar_esquema
from datos_prueba import contexto, crudo
from transform import a_contrato, armar_lote


def mensaje_valido() -> dict:
    return a_contrato(crudo(), "dudas", contexto()).model_dump(mode="json")


def test_lote_valido_y_ordenado():
    nuevo = a_contrato(crudo(id="1554205178671009999"), "dudas", contexto())
    viejo = a_contrato(crudo(), "dudas", contexto())
    lote = armar_lote([nuevo, viejo], modo="historial", servidor_id="1554157903701741700")
    assert lote.version_contrato == "1.0"
    assert [m.id for m in lote.mensajes] == [viejo.id, nuevo.id]  # del más antiguo al más reciente
    # Lo que se escribe en JSON se puede volver a leer sin perder nada.
    assert Lote.model_validate_json(lote.model_dump_json()) == lote


def test_un_campo_que_no_esta_en_el_contrato_es_un_error():
    with pytest.raises(ValidationError):
        Mensaje.model_validate({**mensaje_valido(), "campoNuevo": 1})


def test_siempre_van_todos_los_campos():
    # Regla 3: si Discord no manda un dato, el campo va igual con [], null o false.
    datos = mensaje_valido()
    del datos["reacciones"]
    with pytest.raises(ValidationError):
        Mensaje.model_validate(datos)


def test_las_fechas_van_en_utc_con_z():
    with pytest.raises(ValidationError):
        Mensaje.model_validate({**mensaje_valido(), "fecha": "2026-09-28T18:56:30+00:00"})


def test_los_ids_van_como_texto_de_digitos():
    with pytest.raises(ValidationError):
        Mensaje.model_validate({**mensaje_valido(), "id": "abc"})


def test_un_lote_sin_mensajes_es_un_error():
    with pytest.raises(ValidationError):
        armar_lote([], modo="historial", servidor_id="1554157903701741700")


def test_el_esquema_usa_los_nombres_del_contrato():
    propiedades = generar_esquema()["$defs"]["Mensaje"]["properties"]
    assert "textoOriginal" in propiedades and "respondeA" in propiedades


def test_el_esquema_publicado_esta_al_dia():
    # Si esta prueba falla, el contrato cambió en el código: corre "python contract.py" y sube el esquema nuevo.
    assert json.loads(ARCHIVO_ESQUEMA.read_text(encoding="utf-8")) == generar_esquema()
