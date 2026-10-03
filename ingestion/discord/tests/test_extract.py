"""Desde dónde se extrae: el marcador y la ventana de relectura."""
from datetime import datetime, timedelta, timezone

from discord_api import snowflake_desde_fecha
from extract import desde_donde

AHORA = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def test_el_id_fabricado_coincide_con_uno_real():
    # El mensaje 1554205178671009863 se escribió el 2026-09-28 a las 18:56:30.331 UTC.
    fecha = datetime(2026, 9, 28, 18, 56, 30, 331000, tzinfo=timezone.utc)
    assert snowflake_desde_fecha(fecha) >> 22 == 1554205178671009863 >> 22


def test_sin_marcador_se_extrae_todo():
    assert desde_donde(None, 7, AHORA) is None


def test_marcador_reciente_relee_los_ultimos_dias():
    marcador = str(snowflake_desde_fecha(AHORA - timedelta(hours=1)))
    assert desde_donde(marcador, 7, AHORA) == snowflake_desde_fecha(AHORA - timedelta(days=7))


def test_marcador_viejo_no_pierde_mensajes():
    marcador = str(snowflake_desde_fecha(AHORA - timedelta(days=30)))
    assert desde_donde(marcador, 7, AHORA) == int(marcador)
