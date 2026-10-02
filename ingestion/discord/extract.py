"""
Paso 4 · Extrae los mensajes de #dudas y #logros tal como los entrega Discord (la "E" del ETL).

Qué guarda en data/raw/:
- <canal>.json: los mensajes de cada canal, sin modificar.
- context.json: lo que la transformación necesita saber además de los mensajes:
  el ID de nuestro bot, el ID de su rol y los roles de cada autor real (decisiones 2 y 5).

Qué extrae:
- Si nunca se envió un lote a backend, o con --todo: todo el historial.
- Si ya se envió alguno: lo posterior al marcador (el último mensaje enviado) y,
  además, se releen los últimos INGEST_REREAD_DAYS días para captar reacciones
  y ediciones nuevas. Los mensajes releídos se reenvían, y backend los actualiza.

Solo hace peticiones GET: no escribe nada en Discord.
Uso:  python extract.py          (incremental)
      python extract.py --todo   (todo el historial)
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from config import ConfigError, cargar_config
from discord_api import DiscordAPI, DiscordAPIError, snowflake_desde_fecha

CARPETA_DATOS = Path(__file__).parent / "data"
CARPETA_CRUDOS = CARPETA_DATOS / "raw"
ARCHIVO_CONTEXTO = CARPETA_CRUDOS / "context.json"
# El marcador lo escribe send_batch.py cuando backend confirma que recibió un lote.
ARCHIVO_MARCADORES = CARPETA_DATOS / "markers.json"
MENSAJES_POR_PAGINA = 100  # máximo que acepta Discord
NO_ENCONTRADO = 404


def leer_marcadores() -> dict[str, str]:
    """ID de canal → ID del último mensaje que backend confirmó haber recibido."""
    if not ARCHIVO_MARCADORES.exists():
        return {}
    return json.loads(ARCHIVO_MARCADORES.read_text(encoding="utf-8"))


def desde_donde(marcador: str | None, dias_relectura: int, ahora: datetime) -> int | None:
    """Desde qué ID extraer. None significa todo el historial.

    Se toma el más antiguo entre el marcador y el inicio de la ventana de relectura:
    - si el marcador es reciente, se releen los últimos días (reacciones y ediciones nuevas);
    - si es viejo (por ejemplo, la ingesta estuvo apagada una semana), se parte del marcador
      para no perder ningún mensaje.
    """
    if marcador is None:
        return None
    inicio_ventana = snowflake_desde_fecha(ahora - timedelta(days=dias_relectura))
    return min(int(marcador), inicio_ventana)


def extraer_todo(api: DiscordAPI, canal_id: str) -> list[dict]:
    """Recorre el historial hacia atrás (parámetro before) hasta que no quedan más mensajes."""
    mensajes = []
    antes_de = None
    while True:
        params = {"limit": MENSAJES_POR_PAGINA}
        if antes_de:
            params["before"] = antes_de
        pagina = api.get(f"/channels/{canal_id}/messages", params=params)
        mensajes.extend(pagina)
        if len(pagina) < MENSAJES_POR_PAGINA:
            return mensajes
        antes_de = pagina[-1]["id"]


def extraer_desde(api: DiscordAPI, canal_id: str, despues_de: int) -> list[dict]:
    """Recorre el historial hacia adelante (parámetro after) desde un ID hasta el presente."""
    mensajes = []
    cursor = despues_de
    while True:
        pagina = api.get(f"/channels/{canal_id}/messages", params={"limit": MENSAJES_POR_PAGINA, "after": str(cursor)})
        mensajes.extend(pagina)
        if len(pagina) < MENSAJES_POR_PAGINA:
            return mensajes
        cursor = max(int(m["id"]) for m in pagina)


def extraer_contexto(api: DiscordAPI, servidor_id: str, mensajes: list[dict]) -> dict:
    """El ID del bot, el ID de su rol y los roles de cada autor real.

    📘 Por REST, los mensajes no traen los roles del autor: se piden una vez por autor.
    Los webhooks (alumnos simulados) no tienen roles, así que se saltean.
    """
    bot = api.get("/users/@me")
    roles_servidor = api.get(f"/guilds/{servidor_id}/roles")
    # 📘 El rol que Discord crea para un bot lleva tags.bot_id con el ID de ese bot.
    rol_bot = next((r for r in roles_servidor if (r.get("tags") or {}).get("bot_id") == bot["id"]), None)

    autores_reales = sorted({m["author"]["id"] for m in mensajes if not m.get("webhook_id")})
    roles_por_autor = {}
    for autor_id in autores_reales:
        try:
            miembro = api.get(f"/guilds/{servidor_id}/members/{autor_id}")
            roles_por_autor[autor_id] = miembro["roles"]
        except DiscordAPIError as e:
            if e.status != NO_ENCONTRADO:
                raise
            roles_por_autor[autor_id] = []  # ya no está en el servidor: queda como miembro
    return {
        "extraido_en": datetime.now(timezone.utc).isoformat(),
        "servidor_id": servidor_id,
        "bot_id": bot["id"],
        "rol_bot_id": rol_bot["id"] if rol_bot else None,
        "roles_por_autor": roles_por_autor,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrae los mensajes de Discord a data/raw/.")
    parser.add_argument("--todo", action="store_true", help="extraer todo el historial, sin usar el marcador")
    args = parser.parse_args()

    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1

    canales = {"dudas": config.canal_dudas_id, "logros": config.canal_logros_id}
    faltantes = [canal for canal, canal_id in canales.items() if canal_id is None]
    if config.guild_id is None:
        faltantes.append("servidor (DISCORD_GUILD_ID)")
    if faltantes:
        print(f"❌ Falta el ID de: {', '.join(faltantes)}. Corre verify_connection.py y cópialos al .env.")
        return 1

    marcadores = {} if args.todo else leer_marcadores()
    ahora = datetime.now(timezone.utc)
    CARPETA_CRUDOS.mkdir(parents=True, exist_ok=True)
    todos = []
    with DiscordAPI(config.bot_token) as api:
        for canal, canal_id in canales.items():
            desde = desde_donde(marcadores.get(canal_id), config.dias_relectura, ahora)
            crudos = extraer_todo(api, canal_id) if desde is None else extraer_desde(api, canal_id, desde)
            # Los IDs de Discord crecen con el tiempo: ordenarlos es ordenar por fecha.
            mensajes = sorted({m["id"]: m for m in crudos}.values(), key=lambda m: int(m["id"]))
            todos.extend(mensajes)
            # Los metadatos de la extracción van aparte; cada mensaje queda exactamente como lo entregó Discord.
            extraccion = {
                "canal": canal,
                "canal_id": canal_id,
                "extraido_en": ahora.isoformat(),
                "desde_id": str(desde) if desde is not None else None,
                "total": len(mensajes),
                "mensajes": mensajes,
            }
            archivo = CARPETA_CRUDOS / f"{canal}.json"
            archivo.write_text(json.dumps(extraccion, ensure_ascii=False, indent=2), encoding="utf-8")
            alcance = "todo el historial" if desde is None else f"últimos {config.dias_relectura} días o desde el marcador"
            print(f"✅ #{canal:<7} {len(mensajes)} mensajes ({alcance}) → data/raw/{archivo.name}")

        contexto = extraer_contexto(api, config.guild_id, todos)
    ARCHIVO_CONTEXTO.write_text(json.dumps(contexto, ensure_ascii=False, indent=2), encoding="utf-8")
    rol_bot = "encontrado" if contexto["rol_bot_id"] else "no encontrado"
    print(f"✅ Contexto: rol del bot {rol_bot}, roles de {len(contexto['roles_por_autor'])} autores reales → data/raw/context.json")
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
