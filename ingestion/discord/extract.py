"""
Paso 4 · Extrae todos los mensajes de #dudas y #logros tal como los entrega Discord.

Recorre el historial de cada canal de 100 en 100 mensajes (el máximo que
permite Discord por petición) y guarda cada mensaje sin modificar en
data/raw/<canal>.json. Es la "E" del ETL y la materia prima para conocer
los datos (O3) y diseñar el contrato (O4).

Solo hace peticiones GET: no escribe nada en Discord.
Uso:  python extract.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import ConfigError, cargar_config
from discord_api import DiscordAPI, DiscordAPIError

CARPETA_CRUDOS = Path(__file__).parent / "data" / "raw"
MENSAJES_POR_PAGINA = 100  # máximo que acepta Discord


def extraer_canal(api: DiscordAPI, canal_id: str) -> list[dict]:
    """Devuelve todos los mensajes del canal, del más antiguo al más reciente.

    Discord entrega los mensajes del más reciente al más antiguo. Cada página
    pide los anteriores al último recibido (parámetro before) hasta que llega
    una página incompleta, que significa que no quedan más.
    """
    mensajes = []
    antes_de = None
    while True:
        params = {"limit": MENSAJES_POR_PAGINA}
        if antes_de:
            params["before"] = antes_de
        pagina = api.get(f"/channels/{canal_id}/messages", params=params)
        mensajes.extend(pagina)
        if len(pagina) < MENSAJES_POR_PAGINA:
            break
        antes_de = pagina[-1]["id"]
    # Los IDs de Discord (snowflakes) crecen con el tiempo: ordenarlos es ordenar por fecha.
    return sorted(mensajes, key=lambda m: int(m["id"]))


def main() -> int:
    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1

    canales = {"dudas": config.canal_dudas_id, "logros": config.canal_logros_id}
    faltantes = [canal for canal, canal_id in canales.items() if canal_id is None]
    if faltantes:
        print(f"❌ Falta el ID de: {', '.join(faltantes)}. Corre verify_connection.py y cópialos al .env.")
        return 1

    CARPETA_CRUDOS.mkdir(parents=True, exist_ok=True)
    with DiscordAPI(config.bot_token) as api:
        for canal, canal_id in canales.items():
            mensajes = extraer_canal(api, canal_id)
            # Los metadatos del lote van aparte. Cada mensaje queda exactamente como lo entregó Discord;
            # solo cambia el orden de la lista (Discord los entrega del más reciente al más antiguo).
            lote = {
                "canal": canal,
                "canal_id": canal_id,
                "extraido_en": datetime.now(timezone.utc).isoformat(),
                "total": len(mensajes),
                "mensajes": mensajes,
            }
            archivo = CARPETA_CRUDOS / f"{canal}.json"
            archivo.write_text(json.dumps(lote, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✅ #{canal:<7} {len(mensajes)} mensajes → data/raw/{archivo.name}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DiscordAPIError as e:
        print(f"❌ Discord rechazó la petición: {e}")
        sys.exit(1)
    except httpx.TransportError as e:
        print(f"❌ No se pudo conectar con Discord: {e}")
        sys.exit(1)
