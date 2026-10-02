"""
Paso 5 · Transforma los mensajes extraídos al contrato y arma el lote (la "T" del ETL).

Lee data/raw/ (lo que guardó extract.py), convierte cada mensaje al contrato v1,
lo valida y escribe el lote en data/batches/batch_<fecha>.json.
Si un solo mensaje no cumple el contrato, no escribe nada y muestra qué falló.

No se conecta a internet.
Uso:  python build_batch.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from config import ConfigError, cargar_config
from contract import Lote, Mensaje
from transform import Contexto, a_contrato, armar_lote

CARPETA_DATOS = Path(__file__).parent / "data"
CARPETA_CRUDOS = CARPETA_DATOS / "raw"
CARPETA_LOTES = CARPETA_DATOS / "batches"
CANALES = ("dudas", "logros")


def leer_json(archivo: Path) -> dict:
    return json.loads(archivo.read_text(encoding="utf-8"))


def mostrar_resumen(lote: Lote) -> None:
    """Cuenta los mensajes por canal, tipo, origen y rol, sin mostrar datos personales."""
    mensajes = lote.mensajes
    por_canal = Counter(m.canal.nombre for m in mensajes)
    por_tipo = Counter(m.tipo for m in mensajes)
    simulados = sum(m.es_simulado for m in mensajes)
    autores = {m.autor.id for m in mensajes}
    por_rol = Counter(m.autor.rol for m in mensajes)
    print(f"   Por canal:  {dict(por_canal)}")
    print(f"   Por tipo:   {dict(por_tipo)}")
    print(f"   Origen:     {simulados} simulados y {len(mensajes) - simulados} reales")
    print(f"   Autores:    {len(autores)} distintos · mensajes por rol: {dict(por_rol)}")
    print(f"   Sin texto:  {sum(not m.tiene_texto for m in mensajes)} · con adjuntos: {sum(bool(m.adjuntos) for m in mensajes)}"
          f" · respuestas: {sum(m.responde_a is not None for m in mensajes)}"
          f" · mencionan al bot: {sum(m.menciona_al_bot for m in mensajes)}")


def main() -> int:
    try:
        config = cargar_config()
    except ConfigError as e:
        print(f"❌ {e}")
        return 1

    archivo_contexto = CARPETA_CRUDOS / "context.json"
    if not archivo_contexto.exists():
        print("❌ Falta data/raw/context.json. Corre primero extract.py.")
        return 1
    contexto_crudo = leer_json(archivo_contexto)
    contexto = Contexto(
        webhooks_propios=config.webhooks_propios,
        bot_id=contexto_crudo["bot_id"],
        rol_bot_id=contexto_crudo["rol_bot_id"],
        roles_por_autor=contexto_crudo["roles_por_autor"],
        roles_mentor=config.roles_mentor,
        roles_staff=config.roles_staff,
        mentores_simulados=config.mentores_simulados,
    )

    mensajes: list[Mensaje] = []
    errores = []
    for canal in CANALES:
        extraccion = leer_json(CARPETA_CRUDOS / f"{canal}.json")
        for crudo in extraccion["mensajes"]:
            try:
                mensajes.append(a_contrato(crudo, canal, contexto))
            except ValidationError as e:
                errores.append((canal, crudo.get("id"), e))

    if errores:
        print(f"❌ {len(errores)} mensajes no cumplen el contrato. No se escribió el lote.")
        for canal, mensaje_id, error in errores:
            print(f"\n   #{canal} · mensaje {mensaje_id}:")
            for detalle in error.errors():
                campo = ".".join(str(p) for p in detalle["loc"])
                print(f"     - {campo}: {detalle['msg']}")
        return 1
    if not mensajes:
        print("ℹ️  No hay mensajes nuevos: no se armó ningún lote.")
        return 0

    lote = armar_lote(mensajes, modo="historial", servidor_id=contexto_crudo["servidor_id"])
    CARPETA_LOTES.mkdir(parents=True, exist_ok=True)
    nombre = "batch_" + lote.generado_en.replace(":", "").replace("-", "").replace(".", "") + ".json"
    archivo = CARPETA_LOTES / nombre
    archivo.write_text(lote.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"✅ {len(lote.mensajes)} mensajes cumplen el contrato v{lote.version_contrato} → data/batches/{nombre}")
    mostrar_resumen(lote)
    return 0


if __name__ == "__main__":
    sys.exit(main())
