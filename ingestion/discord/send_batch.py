"""
Paso 6 · Envía un lote a la puerta de backend (la "L" del ETL).

Usa la opción C de docs/INGESTION_GUIDE.md, "etiqueta + caja":
- la etiqueta: los campos que backend ya recibe, con sus nombres;
- la caja (mensajeContrato): el mensaje completo del contrato v1.
Así backend no renombra nada y no se pierde ningún dato. El contrato no cambia:
esta es solo la forma de entregárselo a backend.

Si backend confirma que recibió el lote, guarda el marcador (el último mensaje
enviado de cada canal) para que la próxima extracción pida solo lo nuevo.

Uso:  python send_batch.py               envía el último lote de data/batches/
      python send_batch.py --prueba      no envía: guarda lo que enviaría en data/batches/
      python send_batch.py <archivo>     envía ese lote
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

from config import ConfigError, cargar_config
from contract import Lote, Mensaje

CARPETA_DATOS = Path(__file__).parent / "data"
CARPETA_LOTES = CARPETA_DATOS / "batches"
ARCHIVO_MARCADORES = CARPETA_DATOS / "markers.json"
TIMEOUT_SEGUNDOS = 30.0
# autor.tipo del contrato → TipoAutor de backend. BOT es el cambio 3 que se le propone a backend.
TIPO_AUTOR_BACKEND = {"persona": "HUMANO", "botPropio": "AI", "otroBot": "BOT"}


class EnvioError(Exception):
    """Backend no confirmó la recepción del lote."""


def a_interaccion(mensaje: Mensaje) -> dict:
    """Un mensaje del contrato → una interacción de backend: etiqueta + caja."""
    return {
        # La etiqueta: los campos de InteractionInputDto, con los nombres de backend.
        "discordId": mensaje.id,
        "channelId": mensaje.canal.id,
        "authorId": mensaje.autor.id,
        "authorUsername": mensaje.autor.nombre_usuario,
        "autorNombre": mensaje.autor.nombre_visible,
        "autorRol": mensaje.autor.rol,
        "textoMensaje": mensaje.texto_original,
        "tipoAutor": TIPO_AUTOR_BACKEND[mensaje.autor.tipo],
        "clasificacionSentimiento": None,  # la calcula la IA, no la ingesta
        "timestampMensaje": mensaje.fecha,
        # La caja: el mensaje completo, con los nombres del contrato.
        "mensajeContrato": mensaje.model_dump(mode="json"),
    }


def a_formato_backend(lote: Lote) -> dict:
    """El lote del contrato → el cuerpo que recibe POST /api/v1/community/process."""
    return {
        "loteId": lote.lote_id,
        "tipoServidor": lote.fuente,
        "versionContrato": lote.version_contrato,
        "modo": lote.modo,
        "servidorId": lote.servidor_id,
        "generadoEn": lote.generado_en,
        "interacciones": [a_interaccion(m) for m in lote.mensajes],
    }


def enviar(cuerpo: dict, url: str, http: httpx.Client) -> dict:
    """Hace el POST y devuelve el recibo de backend. No reintenta solo: un reenvío lo decide la persona."""
    respuesta = http.post(url, json=cuerpo, timeout=TIMEOUT_SEGUNDOS)
    if respuesta.is_error:
        raise EnvioError(f"backend respondió HTTP {respuesta.status_code}: {respuesta.text[:500]}")
    recibo = respuesta.json()
    if recibo.get("status") != "exitoso":
        raise EnvioError(f"backend no confirmó el lote: {recibo}")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Envía un lote a backend (opción C: etiqueta + caja).")
    parser.add_argument("archivo", nargs="?", type=Path, help="lote a enviar; por defecto, el último de data/batches/")
    parser.add_argument("--prueba", action="store_true", help="no enviar: guardar en un archivo lo que se enviaría")
    args = parser.parse_args()

    archivo = args.archivo or ultimo_lote()
    if archivo is None or not archivo.exists():
        print("❌ No hay ningún lote. Corre primero build_batch.py.")
        return 1
    lote = Lote.model_validate_json(archivo.read_text(encoding="utf-8"))
    cuerpo = a_formato_backend(lote)

    if args.prueba:
        destino = archivo.with_name(archivo.stem.replace("batch_", "request_") + ".json")
        destino.write_text(json.dumps(cuerpo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"🧪 Prueba: no se envió nada. El cuerpo del POST está en data/batches/{destino.name}")
        return 0

    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1
    if not config.url_backend:
        print("❌ Falta BACKEND_INGEST_URL en el .env. Para ver lo que se enviaría, usa --prueba.")
        return 1

    try:
        with httpx.Client() as http:
            recibo = enviar(cuerpo, config.url_backend, http)
    except (EnvioError, httpx.TransportError) as e:
        print(f"❌ No se envió el lote {lote.lote_id}: {e}")
        print("   El marcador no cambió: la próxima extracción volverá a incluir estos mensajes.")
        return 1

    guardar_marcadores(lote)
    print(f"✅ Backend recibió el lote {lote.lote_id}: {recibo.get('totalMensajesRecibidos')} mensajes.")
    print("   Marcador actualizado: la próxima extracción pedirá desde aquí.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
