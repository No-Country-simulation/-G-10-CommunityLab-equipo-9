"""
Paso 6 · Envía un lote a la API Java (la "L" del ETL).

Envía el lote del contrato v1 tal cual (decisión D8, 2026-10-03), sin convertirlo:
Java saca de cada mensaje lo que va a columnas y guarda el mensaje completo.
La puerta exige la cabecera X-Api-Key (BACKEND_API_KEY en el .env).

Si Java confirma que recibió el lote, guarda el marcador (el último mensaje
enviado de cada canal) para que la próxima extracción pida solo lo nuevo.
Reenviar un lote es seguro: si Java ya lo tenía, devuelve el mismo recibo con
yaRecibido = true y no duplica nada.

Uso:  python send_batch.py               envía el último lote de data/batches/
      python send_batch.py --prueba      no envía: revisa el lote y muestra qué se enviaría
      python send_batch.py <archivo>     envía ese lote
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

from config import ConfigError, cargar_config
from contract import Lote

CARPETA_DATOS = Path(__file__).parent / "data"
CARPETA_LOTES = CARPETA_DATOS / "batches"
ARCHIVO_MARCADORES = CARPETA_DATOS / "markers.json"
TIMEOUT_SEGUNDOS = 30.0
CABECERA_API_KEY = "X-Api-Key"


class EnvioError(Exception):
    """Java no confirmó la recepción del lote."""


def enviar(lote: Lote, url: str, api_key: str, http: httpx.Client) -> dict:
    """Hace el POST del lote tal cual y devuelve el recibo. No reintenta solo: un reenvío lo decide la persona."""
    respuesta = http.post(
        url,
        json=lote.model_dump(mode="json"),
        headers={CABECERA_API_KEY: api_key},
        timeout=TIMEOUT_SEGUNDOS,
    )
    if respuesta.status_code == 401:
        raise EnvioError("Java rechazó la clave (HTTP 401): revisa BACKEND_API_KEY en el .env")
    if respuesta.is_error:
        raise EnvioError(f"Java respondió HTTP {respuesta.status_code}: {respuesta.text[:500]}")
    recibo = respuesta.json()
    if recibo.get("loteId") != lote.lote_id or "total" not in recibo:
        raise EnvioError(f"Java no confirmó este lote: {recibo}")
    return recibo


def nuevos_marcadores(lote: Lote, actuales: dict[str, str]) -> dict[str, str]:
    """Para cada canal, el ID más alto entre el marcador actual y los mensajes enviados."""
    marcadores = dict(actuales)
    for mensaje in lote.mensajes:
        canal = mensaje.canal.id
        if canal not in marcadores or int(mensaje.id) > int(marcadores[canal]):
            marcadores[canal] = mensaje.id
    return marcadores


def guardar_marcadores(lote: Lote) -> None:
    actuales = json.loads(ARCHIVO_MARCADORES.read_text(encoding="utf-8")) if ARCHIVO_MARCADORES.exists() else {}
    ARCHIVO_MARCADORES.write_text(json.dumps(nuevos_marcadores(lote, actuales), indent=2) + "\n", encoding="utf-8")


def ultimo_lote() -> Path | None:
    lotes = sorted(CARPETA_LOTES.glob("batch_*.json"))
    return lotes[-1] if lotes else None


def describir_recibo(recibo: dict) -> str:
    texto = (
        f"total {recibo['total']} (nuevos {recibo.get('nuevos')}, "
        f"actualizados {recibo.get('actualizados')}, sin cambios {recibo.get('sinCambios')})"
    )
    if recibo.get("yaRecibido"):
        texto += ". Java ya lo tenía: no se guardó nada otra vez"
    return texto


def main() -> int:
    parser = argparse.ArgumentParser(description="Envía un lote del contrato v1 a la API Java.")
    parser.add_argument("archivo", nargs="?", type=Path, help="lote a enviar; por defecto, el último de data/batches/")
    parser.add_argument("--prueba", action="store_true", help="no enviar: solo revisar el lote")
    args = parser.parse_args()

    archivo = args.archivo or ultimo_lote()
    if archivo is None or not archivo.exists():
        print("❌ No hay ningún lote. Corre primero build_batch.py.")
        return 1
    lote = Lote.model_validate_json(archivo.read_text(encoding="utf-8"))

    if args.prueba:
        print(f"🧪 Prueba: no se envió nada. El lote {lote.lote_id} cumple el contrato v1 "
              f"({len(lote.mensajes)} mensajes) y se enviaría tal cual: data/batches/{archivo.name}")
        return 0

    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1
    if not config.url_backend:
        print("❌ Falta BACKEND_INGEST_URL en el .env. Para revisar el lote sin enviarlo, usa --prueba.")
        return 1
    if not config.api_key_backend:
        print("❌ Falta BACKEND_API_KEY en el .env. Genérala con: python scripts/generar_api_key.py (desde la raíz).")
        return 1

    try:
        with httpx.Client() as http:
            recibo = enviar(lote, config.url_backend, config.api_key_backend, http)
    except (EnvioError, httpx.TransportError) as e:
        print(f"❌ No se envió el lote {lote.lote_id}: {e}")
        print("   El marcador no cambió: la próxima extracción volverá a incluir estos mensajes.")
        return 1

    guardar_marcadores(lote)
    print(f"✅ Java recibió el lote {lote.lote_id}: {describir_recibo(recibo)}.")
    print("   Marcador actualizado: la próxima extracción pedirá desde aquí.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
