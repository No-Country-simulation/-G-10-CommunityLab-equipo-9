"""
Prototipo desechable del contrato de ingesta v1.

Convierte los mensajes de data/raw/ al formato propuesto en docs/CONTRACT.md y
muestra los ejemplos de su §7. Sirvió para comprobar el contrato con datos
reales antes de programarlo.

NO es el código definitivo:
- no aplica todas las reglas del contrato: autor.tipo solo distingue
  persona/bot, autor.rol siempre es "miembro", mencionaAlBot siempre es False
  y encuesta siempre es None;
- oculta los datos de las personas reales para poder copiar la salida a la
  documentación.

La transformación definitiva se programa con pydantic después de validar el contrato.

Uso (desde ingestion/discord, después de correr extract.py):
    .\\.venv\\Scripts\\python.exe prototypes\\contract_prototype.py
"""
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CARPETA_CRUDOS = Path(__file__).resolve().parent.parent / "data" / "raw"
OCULTO = "<oculto>"
TIPOS = {0: "mensaje", 19: "respuesta", 6: "avisoSistema", 7: "avisoSistema", 18: "avisoSistema", 46: "avisoSistema"}


def fecha_utc(iso: str | None) -> str | None:
    """Convierte una fecha ISO 8601 a UTC con milisegundos y terminada en Z."""
    if iso is None:
        return None
    return datetime.fromisoformat(iso).astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalizar(texto: str) -> str:
    """'Ana Pérez' → 'ana-perez'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def expiracion(url: str) -> str | None:
    """Lee el vencimiento de la URL de un adjunto: el parámetro ex es un tiempo Unix en hexadecimal."""
    ex = parse_qs(urlparse(url).query).get("ex")
    return fecha_utc(datetime.fromtimestamp(int(ex[0], 16), tz=timezone.utc).isoformat()) if ex else None


def a_contrato(m: dict, canal_nombre: str) -> dict:
    a = m["author"]
    simulado = bool(m.get("webhook_id"))
    texto = m["content"]
    return {
        "id": m["id"],
        "canal": {"id": m["channel_id"], "nombre": canal_nombre},
        "fecha": fecha_utc(m["timestamp"]),
        "tipo": TIPOS.get(m["type"], "otro"),
        "tipoDiscord": m["type"],
        "esSimulado": simulado,
        "autor": {
            # En la simulación, author.id es el del webhook: la identidad sale del nombre.
            "id": f"sim-{normalizar(a['username'])}" if simulado else a["id"],
            "idDiscord": a["id"],
            "nombreUsuario": a["username"],
            "nombreVisible": a.get("global_name") or a["username"],
            "tipo": "persona" if simulado or not a.get("bot") else "bot",
            "rol": "miembro",
        },
        "textoOriginal": texto,
        "tieneTexto": bool(texto.strip()),
        "tieneBloqueCodigo": "```" in texto,
        "enlaces": [
            {"url": u, "dominio": urlparse(u).netloc.lower().removeprefix("www.")}
            for u in re.findall(r"https?://\S+", texto)
        ],
        "menciones": {"usuarios": [u["id"] for u in m["mentions"]], "roles": m["mention_roles"], "todos": m["mention_everyone"]},
        "mencionaAlBot": False,
        "respondeA": (m.get("message_reference") or {}).get("message_id") if m["type"] == 19 else None,
        "adjuntos": [
            {
                "id": x["id"], "nombre": x["filename"], "tipoContenido": x.get("content_type"),
                "tamanoBytes": x["size"], "ancho": x.get("width"), "alto": x.get("height"),
                "url": x["url"], "urlExpiraEn": expiracion(x["url"]),
            }
            for x in m["attachments"]
        ],
        "reacciones": [
            {"emoji": r["emoji"]["name"], "emojiId": r["emoji"]["id"], "cantidad": r["count"]}
            for r in m.get("reactions", [])
        ],
        "fijado": m["pinned"],
        "editado": m["edited_timestamp"] is not None,
        "editadoEn": fecha_utc(m["edited_timestamp"]),
        "stickers": [s["name"] for s in m.get("sticker_items", [])],
        "vistasPrevias": [
            {"tipo": e.get("type"), "url": e.get("url"), "titulo": e.get("title"), "descripcion": e.get("description")}
            for e in m["embeds"]
        ],
        "encuesta": None,
    }


def ocultar(c: dict) -> dict:
    """Oculta los datos de las personas reales y acorta las URLs de los adjuntos."""
    if not c["esSimulado"]:
        c["autor"].update(id=OCULTO, idDiscord=OCULTO, nombreUsuario=OCULTO, nombreVisible=OCULTO)
    for x in c["adjuntos"]:
        x.update(nombre="captura.jpg", url="https://cdn.discordapp.com/attachments/…/captura.jpg?ex=…&is=…&hm=…")
    return c


def main() -> None:
    mensajes = {}
    for canal in ("dudas", "logros"):
        lote = json.loads((CARPETA_CRUDOS / f"{canal}.json").read_text(encoding="utf-8"))
        for m in lote["mensajes"]:
            mensajes[m["id"]] = (m, canal)

    # Los 4 ejemplos de CONTRACT.md §7: duda simulada, respuesta real, imagen y logro con reacción.
    ejemplos = [
        next(k for k, (m, _) in mensajes.items() if m["content"].startswith("como instalo pyhton")),
        next(k for k, (m, _) in mensajes.items() if m["type"] == 19),
        next(k for k, (m, _) in mensajes.items() if m["attachments"]),
        next(k for k, (m, _) in mensajes.items() if m.get("reactions")),
    ]
    for k in ejemplos:
        m, canal = mensajes[k]
        print(json.dumps(ocultar(a_contrato(m, canal)), ensure_ascii=False, indent=2))
        print("-----")

    todos = [a_contrato(m, canal) for m, canal in mensajes.values()]
    simulados = sorted({t["autor"]["id"] for t in todos if t["esSimulado"]})
    print(f"Convertidos: {len(todos)} | autores simulados: {simulados}")


if __name__ == "__main__":
    main()
