"""
Genera la API key de la ingesta (S1) y la escribe, SIN MOSTRARLA, en los dos .env:

    .env (raíz)              API_KEY_INGESTA=...   la lee la API Java (docker compose)
    ingestion/discord/.env   BACKEND_API_KEY=...   la envía send_batch.py en la cabecera X-Api-Key

Solo cambia esas dos líneas; el resto de cada .env queda igual.
Si ya hay una clave, no la pisa salvo con --reemplazar.

Uso, desde la raíz del repositorio:
    python scripts/generar_api_key.py
    python scripts/generar_api_key.py --reemplazar
Después: docker compose up -d api-java   (para que la API Java tome la clave nueva)
"""
import argparse
import re
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINOS = (
    (RAIZ / ".env", "API_KEY_INGESTA"),
    (RAIZ / "ingestion" / "discord" / ".env", "BACKEND_API_KEY"),
)


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


def generar(destinos=DESTINOS, reemplazar: bool = False) -> int:
    faltan = [str(ruta.relative_to(RAIZ)) if ruta.is_relative_to(RAIZ) else str(ruta)
              for ruta, _ in destinos if not ruta.exists()]
    if faltan:
        print(f"❌ No existe: {', '.join(faltan)}. Primero copia el .env.example correspondiente como .env.")
        return 1

    # read_bytes y no read_text: read_text convierte \r\n en \n y el archivo cambiaría entero
    textos = [(ruta, variable, ruta.read_bytes().decode("utf-8")) for ruta, variable in destinos]
    con_clave = [variable for _, variable, texto in textos if valor_actual(texto, variable)]
    if con_clave and not reemplazar:
        print(f"⚠️ Ya hay una clave en: {', '.join(con_clave)}. No se cambió nada.")
        print("   Para crear una nueva en los dos .env: python scripts/generar_api_key.py --reemplazar")
        return 1

    clave = secrets.token_urlsafe(32)  # 256 bits al azar, solo letras, números, - y _
    for ruta, variable, texto in textos:
        # newline="" respeta los saltos de línea que ya tenía el archivo
        ruta.write_text(con_variable(texto, variable, clave), encoding="utf-8", newline="")
    print("✅ Clave nueva escrita en .env (API_KEY_INGESTA) y en ingestion/discord/.env (BACKEND_API_KEY).")
    print("   No se mostró en pantalla. Para que la API Java la use: docker compose up -d api-java")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera la API key de la ingesta y la escribe en los dos .env.")
    parser.add_argument("--reemplazar", action="store_true", help="crear una clave nueva aunque ya haya una")
    return generar(reemplazar=parser.parse_args().reemplazar)


if __name__ == "__main__":
    sys.exit(main())
