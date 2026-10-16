"""
El servicio `ingesta` de Docker (T14, DEC-167): la ingesta por lotes corre sola.

Corre la ingesta completa (extraer → armar → enviar) una vez al arrancar y después cada hora en punto,
en hora de Bogotá. Reutiliza extract.py, build_batch.py y send_batch.py: no copia su lógica.

- Nunca corre dos a la vez: un bloqueo en data/ (corrida.lock) frena una segunda corrida, por ejemplo
  un --una-vez a mano mientras el servicio está trabajando.
- Si una corrida falla (Discord o Java caídos), lo registra y espera a la hora siguiente: no se cae.
- El registro lleva solo números, IDs y estados, nunca textos de los mensajes (AGENTS.md).
- Solo lee Discord (GET): no es un segundo bot, nunca escribe en un canal y convive con el bot encendido.

Uso:  python programador.py             servicio: al arrancar y después cada hora en punto
      python programador.py --una-vez   una sola corrida y termina: 0 si salió bien, 1 si falló,
                                        2 si había otra corrida en curso
"""
import argparse
import logging
import os
import signal
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

import build_batch
import extract
import send_batch
from config import ConfigError, cargar_config
from discord_api import DiscordAPIError

log = logging.getLogger("ingesta")

ZONA = ZoneInfo("America/Bogota")
CARPETA_DATOS = Path(__file__).parent / "data"
ARCHIVO_BLOQUEO = "corrida.lock"
# Una corrida tarda segundos. Un bloqueo más viejo quedó de una corrida cortada (por ejemplo, un reinicio)
BLOQUEO_VENCE = timedelta(minutes=30)
# Lotes que se guardan en data/batches/: uno por hora, un día. Los más viejos se borran (traen datos personales)
LOTES_A_CONSERVAR = 24

BIEN, FALLO, EN_CURSO = 0, 1, 2


def proxima_corrida(ahora: datetime) -> datetime:
    """La hora en punto siguiente, en Bogotá. Justo a las 15:00:00, la siguiente es 16:00."""
    local = ahora.astimezone(ZONA)
    return local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def habilitada() -> bool:
    """INGESTA_HABILITADA=false apaga el reloj sin quitar el servicio. Por defecto, encendido."""
    return os.getenv("INGESTA_HABILITADA", "true").strip().lower() != "false"


@contextmanager
def bloqueo(carpeta: Path, ahora: datetime):
    """Da True si esta corrida tomó el bloqueo, y False si hay otra en curso."""
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / ARCHIVO_BLOQUEO
    if archivo.exists():
        try:
            tomado = datetime.fromisoformat(archivo.read_text(encoding="utf-8").strip())
        except ValueError:
            tomado = None
        if tomado is not None and ahora - tomado < BLOQUEO_VENCE:
            yield False
            return
        archivo.unlink(missing_ok=True)  # vencido: la corrida que lo dejó ya no existe
    try:
        # O_EXCL: si dos corridas llegan a la vez, solo una crea el archivo
        descriptor = os.open(archivo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        yield False
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as f:
        f.write(ahora.isoformat())
    try:
        yield True
    finally:
        archivo.unlink(missing_ok=True)


def _cliente_java() -> httpx.Client:
    """Separado para que las pruebas usen una API Java de mentira."""
    return httpx.Client()


def _borrar_lotes_viejos() -> None:
    lotes = sorted(send_batch.CARPETA_LOTES.glob("batch_*.json"))
    for viejo in lotes[:-LOTES_A_CONSERVAR]:
        viejo.unlink(missing_ok=True)


def _corrida(ahora: datetime) -> int:
    inicio = time.monotonic()
    try:
        config = cargar_config()
    except ConfigError:
        log.error("Falta DISCORD_BOT_TOKEN: la ingesta no puede leer Discord")
        return FALLO
    faltantes = extract.ids_faltantes(config)
    if faltantes:
        log.error("Faltan IDs en el .env: %s", ", ".join(faltantes))
        return FALLO
    if not config.url_backend or not config.api_key_backend:
        log.error("Falta BACKEND_INGEST_URL o BACKEND_API_KEY: no hay a dónde enviar el lote")
        return FALLO

    try:
        resumen = extract.extraer(config, ahora=ahora)
    except DiscordAPIError as e:
        log.error("Discord rechazó la extracción (HTTP %s): se reintenta en la hora siguiente", e.status)
        return FALLO
    except httpx.TransportError as e:
        log.error("No se pudo conectar con Discord (%s): se reintenta en la hora siguiente", type(e).__name__)
        return FALLO
    leidos = ", ".join(f"#{canal} {datos['mensajes']}" for canal, datos in resumen["canales"].items())

    try:
        armado = build_batch.construir_lote(config)
    except build_batch.LoteInvalido as e:
        ids = ", ".join(str(mensaje_id) for _, mensaje_id, _ in e.errores[:10])
        log.error("%d mensajes no cumplen el contrato (IDs: %s): no se envió nada", len(e.errores), ids)
        return FALLO
    if armado is None:
        log.info("Corrida terminada en %.1f s: leídos %s; no hay mensajes para enviar",
                 time.monotonic() - inicio, leidos)
        return BIEN
    lote, _ = armado

    try:
        with _cliente_java() as http:
            recibo = send_batch.enviar(lote, config.url_backend, config.api_key_backend, http)
    except send_batch.EnvioError as e:
        # Los errores de Java nunca repiten los datos recibidos (formato común de errores)
        log.error("Java no confirmó el lote %s: %s. El marcador no cambió", lote.lote_id, str(e)[:200])
        return FALLO
    except httpx.TransportError as e:
        log.error("No se pudo conectar con Java (%s). El marcador no cambió", type(e).__name__)
        return FALLO

    send_batch.guardar_marcadores(lote)
    log.info("Corrida terminada en %.1f s: leídos %s; lote %s: total %s, nuevos %s, actualizados %s, "
             "sin cambios %s%s", time.monotonic() - inicio, leidos, lote.lote_id, recibo.get("total"),
             recibo.get("nuevos"), recibo.get("actualizados"), recibo.get("sinCambios"),
             " (Java ya lo tenía)" if recibo.get("yaRecibido") else "")
    return BIEN


def correr_una_vez(ahora: datetime | None = None) -> int:
    """Una corrida completa. Nunca lanza: cualquier error queda en el registro y se devuelve FALLO."""
    ahora = ahora or datetime.now(timezone.utc)
    with bloqueo(CARPETA_DATOS, ahora) as tomado:
        if not tomado:
            log.warning("Otra corrida de la ingesta sigue en curso: esta no arranca")
            return EN_CURSO
        try:
            return _corrida(ahora)
        except Exception as e:  # el servicio no se cae; solo el tipo, por si el mensaje trajera datos
            log.error("La corrida falló por un error inesperado (%s)", type(e).__name__)
            return FALLO
        finally:
            _borrar_lotes_viejos()


def servir(dormir=time.sleep, reloj=lambda: datetime.now(timezone.utc), vueltas: int | None = None) -> None:
    """El servicio: corre al arrancar y después cada hora en punto. vueltas limita el bucle en las pruebas."""
    if not habilitada():
        log.info("INGESTA_HABILITADA=false: el reloj está apagado (python programador.py --una-vez sigue funcionando)")
        hechas = 0
        while vueltas is None or hechas < vueltas:
            dormir(3600)
            hechas += 1
        return

    log.info("Servicio de ingesta encendido: corre ahora y después cada hora en punto (hora de Bogotá)")
    objetivo = None
    hechas = 0
    while vueltas is None or hechas < vueltas:
        correr_una_vez(reloj())
        hechas += 1
        # Desde el objetivo, si lo hay: si el reloj despertara un instante antes, no corre dos veces la misma hora
        ahora = reloj()
        objetivo = proxima_corrida(max(ahora, objetivo) if objetivo else ahora)
        log.info("Próxima corrida: %s (hora de Bogotá)", objetivo.strftime("%Y-%m-%d %H:%M"))
        dormir(max((objetivo - reloj()).total_seconds(), 0))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="La ingesta por lotes: al arrancar y cada hora en punto.")
    parser.add_argument("--una-vez", action="store_true", help="una sola corrida y termina")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx registra cada petición; es ruido para este registro
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.una_vez:
        return correr_una_vez()
    # docker compose stop envía SIGTERM: se termina enseguida (una corrida a medias suelta su bloqueo)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    servir()
    return 0


if __name__ == "__main__":
    sys.exit(main())
