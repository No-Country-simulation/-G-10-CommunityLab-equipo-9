"""
Genera una API key y la escribe, SIN MOSTRARLA, en los .env que la necesitan.

    --cliente ingesta (por defecto, S1)
        .env (raíz)              API_KEY_INGESTA=...   la lee la API Java (docker compose)
        ingestion/discord/.env   BACKEND_API_KEY=...   la envía send_batch.py en la cabecera X-Api-Key

    --cliente ia (S2, T04)
        .env (raíz)              API_KEY_IA=...        docker compose se la pasa a la IA (que la exige)
                                                       y a la API Java (que la envía)

    --cliente bot (T05)
        .env (raíz)              API_KEY_BOT=...       docker compose se la pasa a la API Java (que la exige
                                                       en /api/v1/mensajes/en-vivo) y al bot (que la envía)

    --cliente panel (T07)
        .env (raíz)              API_KEY_PANEL=...     docker compose se la pasa a la API Java (que la exige
                                                       en /api/v1/borradores y /api/v1/errores) y al panel

Solo cambia esas líneas; el resto de cada .env queda igual.
Si ya hay una clave, no la pisa salvo con --reemplazar.

Uso, desde la raíz del repositorio:
    python scripts/generar_api_key.py
    python scripts/generar_api_key.py --cliente ia
    python scripts/generar_api_key.py --cliente bot
    python scripts/generar_api_key.py --cliente panel
    python scripts/generar_api_key.py --cliente ia --reemplazar
Después: docker compose up -d   (para que los servicios tomen la clave nueva)
"""
import argparse
import re
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CLIENTES = {
    "ingesta": (
        (RAIZ / ".env", "API_KEY_INGESTA"),
        (RAIZ / "ingestion" / "discord" / ".env", "BACKEND_API_KEY"),
    ),
    "ia": (
        (RAIZ / ".env", "API_KEY_IA"),
    ),
    "bot": (
        (RAIZ / ".env", "API_KEY_BOT"),
    ),
    "panel": (
        (RAIZ / ".env", "API_KEY_PANEL"),
    ),
}
DESTINOS = CLIENTES["ingesta"]


def valor_actual(texto: str, variable: str) -> str:
    coincidencia = re.search(rf"^{variable}=([^\r\n]*)", texto, flags=re.MULTILINE)
    return coincidencia.group(1).strip() if coincidencia else ""


def con_variable(texto: str, variable: str, valor: str) -> str:
    """El texto del .env con la variable cambiada, o agregada al final si no estaba."""
    salto = "\r\n" if "\r\n" in texto else "\n"
    # [^\r\n]* y no .*: en un archivo de Windows, .* se llevaría el \r del final de la línea
    patron = re.compile(rf"^{variable}=[^\r\n]*", flags=re.MULTILINE)
    if patron.search(texto):
        return patron.sub(lambda _: f"{variable}={valor}", texto, count=1)
    if texto and not texto.endswith(("\n", "\r")):
        texto += salto
    return texto + f"{variable}={valor}{salto}"


def _nombre(ruta: Path) -> str:
    return str(ruta.relative_to(RAIZ)) if ruta.is_relative_to(RAIZ) else str(ruta)


def generar(destinos=DESTINOS, reemplazar: bool = False) -> int:
    faltan = [_nombre(ruta) for ruta, _ in destinos if not ruta.exists()]
    if faltan:
        print(f"❌ No existe: {', '.join(faltan)}. Primero copia el .env.example correspondiente como .env.")
        return 1

    # read_bytes y no read_text: read_text convierte \r\n en \n y el archivo cambiaría entero
    textos = [(ruta, variable, ruta.read_bytes().decode("utf-8")) for ruta, variable in destinos]
    con_clave = [variable for _, variable, texto in textos if valor_actual(texto, variable)]
    if con_clave and not reemplazar:
        print(f"⚠️ Ya hay una clave en: {', '.join(con_clave)}. No se cambió nada.")
        print("   Para crear una nueva, agrega --reemplazar al mismo comando.")
        return 1

    clave = secrets.token_urlsafe(32)  # 256 bits al azar, solo letras, números, - y _
    for ruta, variable, texto in textos:
        # newline="" respeta los saltos de línea que ya tenía el archivo
        ruta.write_text(con_variable(texto, variable, clave), encoding="utf-8", newline="")
    donde = " y ".join(f"{_nombre(ruta)} ({variable})" for ruta, variable in destinos)
    print(f"✅ Clave nueva escrita en {donde}.")
    print("   No se mostró en pantalla. Para que los servicios la usen: docker compose up -d")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera una API key y la escribe en los .env, sin mostrarla.")
    parser.add_argument("--cliente", choices=sorted(CLIENTES), default="ingesta",
                        help="ingesta (S1, por defecto), ia (S2), bot (T05) o panel (T07)")
    parser.add_argument("--reemplazar", action="store_true", help="crear una clave nueva aunque ya haya una")
    args = parser.parse_args()
    return generar(CLIENTES[args.cliente], reemplazar=args.reemplazar)


if __name__ == "__main__":
    sys.exit(main())
