"""El servicio `ingesta` (T14): cada hora en punto, nunca dos corridas a la vez, no se cae y no registra textos.

Usan un Discord y una API Java de mentira, una carpeta temporal y un reloj simulado: no salen a internet
ni esperan de verdad.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import build_batch
import extract
import programador
import send_batch
from datos_prueba import BOT_ID, CANAL_DUDAS, ROL_BOT_ID, crudo

UTC = timezone.utc
TEXTO_RECONOCIBLE = "TEXTO-DE-ALUMNO-QUE-NUNCA-DEBE-IR-AL-REGISTRO"
CANAL_LOGROS = "1554158212742127822"
SERVIDOR = "1554157903701741700"


def bogota(hora: str, dia: int = 16) -> datetime:
    """Una hora de Bogotá (UTC-5) del 2026-10-<dia>, pasada a UTC como la entrega el reloj."""
    h, m, s = (int(x) for x in (hora + ":00")[:8].split(":"))
    return datetime(2026, 10, dia, h, m, s, tzinfo=programador.ZONA).astimezone(UTC)


# ── 1. La próxima corrida ─────────────────────────────────────────────────────

@pytest.mark.parametrize("ahora, esperada", [
    ("14:20", "2026-10-16 15:00"),
    ("14:59:59", "2026-10-16 15:00"),
    ("15:00:00", "2026-10-16 16:00"),  # justo en punto: esta ya es la de las 15:00
    ("23:59", "2026-10-17 00:00"),
    ("00:00:01", "2026-10-16 01:00"),
], ids=["14:20", "14:59:59", "en-punto", "23:59", "medianoche"])
def test_la_proxima_corrida_es_la_hora_en_punto_siguiente_en_bogota(ahora, esperada):
    proxima = programador.proxima_corrida(bogota(ahora))

    assert proxima.strftime("%Y-%m-%d %H:%M") == esperada
    assert proxima.utcoffset() == timedelta(hours=-5)


# ── Dobles de prueba ──────────────────────────────────────────────────────────

class DiscordFalso:
    """Responde como la API REST de Discord con un mensaje de #dudas que tiene un texto reconocible."""

    def __init__(self, *_):
        self.rutas = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def get(self, ruta, params=None):
        self.rutas.append(ruta)
        if ruta == "/users/@me":
            return {"id": BOT_ID}
        if ruta.endswith("/roles"):
            return [{"id": ROL_BOT_ID, "tags": {"bot_id": BOT_ID}}]
        if ruta == f"/channels/{CANAL_DUDAS}/messages":
            return [crudo(content=TEXTO_RECONOCIBLE)]
        return []


def java_que_responde(estado: int = 200):
    def responder(pedido: httpx.Request) -> httpx.Response:
        lote = json.loads(pedido.content)
        if estado != 200:
            return httpx.Response(estado, json={"codigo": "ERROR_INTERNO", "mensaje": "Falló Java"})
        return httpx.Response(200, json={"loteId": lote["loteId"], "total": 1, "nuevos": 1, "actualizados": 0,
                                         "sinCambios": 0, "yaRecibido": False})
    return lambda: httpx.Client(transport=httpx.MockTransport(responder))


@pytest.fixture
def ingesta(tmp_path, monkeypatch):
    """La ingesta completa apuntando a una carpeta temporal, con Discord y Java de mentira."""
    datos = tmp_path / "data"
    monkeypatch.setattr(programador, "CARPETA_DATOS", datos)
    monkeypatch.setattr(extract, "CARPETA_CRUDOS", datos / "raw")
    monkeypatch.setattr(extract, "ARCHIVO_CONTEXTO", datos / "raw" / "context.json")
    monkeypatch.setattr(extract, "ARCHIVO_MARCADORES", datos / "markers.json")
    monkeypatch.setattr(build_batch, "CARPETA_CRUDOS", datos / "raw")
    monkeypatch.setattr(build_batch, "CARPETA_LOTES", datos / "batches")
    monkeypatch.setattr(send_batch, "CARPETA_LOTES", datos / "batches")
    monkeypatch.setattr(send_batch, "ARCHIVO_MARCADORES", datos / "markers.json")
    monkeypatch.setattr(extract, "DiscordAPI", DiscordFalso)
    monkeypatch.setattr(programador, "_cliente_java", java_que_responde())
    for nombre, valor in {
        "DISCORD_BOT_TOKEN": "token-falso", "DISCORD_GUILD_ID": SERVIDOR,
        "DISCORD_CHANNEL_DUDAS_ID": CANAL_DUDAS, "DISCORD_CHANNEL_LOGROS_ID": CANAL_LOGROS,
        "DISCORD_WEBHOOK_DUDAS_URL": "https://discord.com/api/webhooks/1554160711800717417/clave",
        "BACKEND_INGEST_URL": "http://api-java:8080/api/v1/lotes", "BACKEND_API_KEY": "clave-falsa",
    }.items():
        monkeypatch.setenv(nombre, valor)
    return datos


# ── Una corrida completa, y 5. el registro ────────────────────────────────────

def test_una_corrida_extrae_arma_envia_y_mueve_el_marcador(ingesta):
    assert programador.correr_una_vez(bogota("15:00")) == programador.BIEN

    marcadores = json.loads((ingesta / "markers.json").read_text(encoding="utf-8"))
    assert marcadores == {CANAL_DUDAS: crudo()["id"]}
    assert not (ingesta / programador.ARCHIVO_BLOQUEO).exists()  # suelta el bloqueo


def test_el_registro_lleva_numeros_y_nunca_el_texto_de_un_mensaje(ingesta, caplog, capsys):
    with caplog.at_level(logging.INFO, logger="ingesta"):
        programador.correr_una_vez(bogota("15:00"))

    assert "#dudas 1" in caplog.text and "nuevos 1" in caplog.text
    salida = caplog.text + "".join(capsys.readouterr())
    assert TEXTO_RECONOCIBLE not in salida


# ── 2. Una corrida que falla ──────────────────────────────────────────────────

@pytest.mark.parametrize("falla, se_espera", [
    ("discord-caido", "No se pudo conectar con Discord (ConnectError)"),
    ("java-500", "Java no confirmó el lote"),
    ("inesperado", "error inesperado (KeyError)"),
])
def test_una_corrida_que_falla_se_registra_y_no_mueve_el_marcador(ingesta, monkeypatch, caplog, falla, se_espera):
    if falla == "discord-caido":
        def caido(*_, **__):
            raise httpx.ConnectError("sin red")
        monkeypatch.setattr(extract, "extraer", caido)
    elif falla == "java-500":
        monkeypatch.setattr(programador, "_cliente_java", java_que_responde(500))
    else:
        def roto(*_, **__):
            raise KeyError(TEXTO_RECONOCIBLE)  # aunque el error traiga un texto, no va al registro
        monkeypatch.setattr(extract, "extraer", roto)

    with caplog.at_level(logging.INFO, logger="ingesta"):
        resultado = programador.correr_una_vez(bogota("15:00"))

    assert resultado == programador.FALLO
    assert se_espera in caplog.text and TEXTO_RECONOCIBLE not in caplog.text
    assert not (ingesta / "markers.json").exists()
    assert not (ingesta / programador.ARCHIVO_BLOQUEO).exists()


def test_el_servicio_sigue_despues_de_una_corrida_que_falla(monkeypatch):
    corridas, esperas = [], []
    reloj = iter([bogota("14:20"), bogota("14:21"), bogota("14:21"),
                  bogota("15:00"), bogota("15:00:05"), bogota("15:00:05")])

    def corrida(ahora):
        corridas.append(ahora)
        return programador.FALLO if len(corridas) == 1 else programador.BIEN

    monkeypatch.setattr(programador, "correr_una_vez", corrida)
    monkeypatch.setenv("INGESTA_HABILITADA", "true")

    programador.servir(dormir=esperas.append, reloj=lambda: next(reloj), vueltas=2)

    assert len(corridas) == 2  # la que falló no detuvo el servicio
    assert esperas == [39 * 60, 3600 - 5]  # de 14:21 a 15:00, y de 15:00:05 a 16:00


def test_si_el_reloj_despierta_un_instante_antes_no_corre_dos_veces_la_misma_hora(monkeypatch):
    corridas, esperas = [], []
    reloj = iter([bogota("14:20"), bogota("14:20"), bogota("14:20"),
                  bogota("14:59:59"), bogota("14:59:59"), bogota("14:59:59")])
    monkeypatch.setattr(programador, "correr_una_vez", corridas.append)

    programador.servir(dormir=esperas.append, reloj=lambda: next(reloj), vueltas=2)

    assert esperas[1] == 3600 + 1  # la siguiente es la de las 16:00, no otra vez la de las 15:00


def test_con_el_interruptor_apagado_no_corre(monkeypatch):
    corridas = []
    monkeypatch.setattr(programador, "correr_una_vez", corridas.append)
    monkeypatch.setenv("INGESTA_HABILITADA", "false")

    programador.servir(dormir=lambda _: None, vueltas=3)

    assert corridas == []


# ── 3. Nunca dos corridas a la vez ────────────────────────────────────────────

def test_una_segunda_corrida_no_arranca_mientras_la_primera_sigue(ingesta, monkeypatch, caplog):
    llamadas = []
    monkeypatch.setattr(extract, "extraer", lambda *a, **k: llamadas.append(1))

    with programador.bloqueo(ingesta, bogota("15:00")) as primera:
        assert primera is True
        with caplog.at_level(logging.INFO, logger="ingesta"):
            segunda = programador.correr_una_vez(bogota("15:01"))

    assert segunda == programador.EN_CURSO and llamadas == []
    assert "sigue en curso" in caplog.text


def test_un_bloqueo_viejo_de_una_corrida_cortada_no_frena_para_siempre(ingesta):
    ingesta.mkdir(parents=True)
    (ingesta / programador.ARCHIVO_BLOQUEO).write_text(bogota("13:00").isoformat(), encoding="utf-8")

    assert programador.correr_una_vez(bogota("15:00")) == programador.BIEN


# ── 4. --una-vez ──────────────────────────────────────────────────────────────

def test_una_vez_termina_con_0_si_salio_bien_y_1_si_fallo(ingesta, monkeypatch):
    assert programador.main(["--una-vez"]) == 0

    monkeypatch.setattr(programador, "_cliente_java", java_que_responde(500))
    assert programador.main(["--una-vez"]) == 1


# ── Los lotes viejos se borran ────────────────────────────────────────────────

def test_se_conservan_solo_los_ultimos_lotes(ingesta):
    lotes = ingesta / "batches"
    lotes.mkdir(parents=True)
    for i in range(programador.LOTES_A_CONSERVAR + 5):
        (lotes / f"batch_2026101{i:03d}.json").write_text("{}", encoding="utf-8")

    programador.correr_una_vez(bogota("15:00"))

    assert len(list(lotes.glob("batch_*.json"))) == programador.LOTES_A_CONSERVAR
