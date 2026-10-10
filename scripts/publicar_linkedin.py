"""
Script para probar la automatización de posts en LinkedIn directamente por código.

Uso:
    python scripts/probar_linkedin.py
    python scripts/probar_linkedin.py --texto "¡Felicidades a Camila por conseguir su primer empleo tech! 🎉"
    python scripts/probar_linkedin.py --archivo ruta/al/borrador.json

Lee LINKEDIN_ACCESS_TOKEN y LINKEDIN_AUTHOR_URN del .env de la raíz.
Si no hay credenciales, muestra el JSON oficial preparado y explica cómo configurarlo.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# En Windows, stdout puede usar cp1252 por defecto; aseguramos UTF-8
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
ENV_PATH = RAIZ / ".env"


def cargar_env():
    valores = {}
    if ENV_PATH.exists():
        for linea in ENV_PATH.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip()
    return valores


def armar_payload_linkedin(author_urn: str, texto: str) -> dict:
    return {
        "author": author_urn or "urn:li:person:ID_DE_EJEMPLO",
        "commentary": texto,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }


def main():
    parser = argparse.ArgumentParser(description="Prueba la publicación directa en LinkedIn por código.")
    parser.add_argument("--texto", help="Texto del post para publicar")
    parser.add_argument("--archivo", help="Ruta a un archivo JSON con el borrador")
    args = parser.parse_args()

    texto = args.texto
    if args.archivo:
        ruta = Path(args.archivo)
        if not ruta.exists():
            print(f"❌ No se encontró el archivo: {args.archivo}")
            return 1
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        texto = contenido.get("textoFinal") or contenido.get("textoIa") or contenido.get("texto")

    if not texto:
        texto = (
            "¡Felicitaciones a Camila por su nuevo rol como Desarrolladora Fullstack! 🎉 "
            "Su constancia y dedicación en CommunityLab dieron frutos. ¡A romperla en esta nueva etapa! 🚀"
        )

    env = cargar_env()
    token = env.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author = env.get("LINKEDIN_AUTHOR_URN", "").strip()

    payload = armar_payload_linkedin(author, texto)

    print("=" * 65)
    print("📢 Automatización de Posts en LinkedIn (InsightEdu Lab)")
    print("=" * 65)
    print("\n📦 Payload JSON generado para LinkedIn API (POST https://api.linkedin.com/rest/posts):\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("\n" + "-" * 65)

    if not token or not author:
        print("🟡 MODO SIMULADO (Local):")
        print("   No se detectaron LINKEDIN_ACCESS_TOKEN y LINKEDIN_AUTHOR_URN en el .env.")
        print("   El sistema backend en Java procesará los posts en modo simulado sin errores.")
        print("\n   Para publicar en vivo en tu cuenta de LinkedIn:")
        print("   1. Agrega a tu .env:")
        print("      LINKEDIN_ACCESS_TOKEN=tu_token_aqui")
        print("      LINKEDIN_AUTHOR_URN=urn:li:person:tu_id_o_empresa")
        print("=" * 65)
        return 0

    print("🟢 Credenciales detectadas en .env. Enviando post a LinkedIn en vivo...")
    req = urllib.request.Request(
        "https://api.linkedin.com/rest/posts",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            id_post = resp.headers.get("x-restli-id") or resp.headers.get("Location") or "Post publicado"
            print(f"✅ ¡Post publicado exitosamente en LinkedIn! ID/URN: {id_post}")
            return 0
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", errors="replace")
        print(f"❌ Error HTTP {e.code} de LinkedIn API:")
        print(f"   {cuerpo}")
        return 1
    except Exception as e:
        print(f"❌ Error de conexión con LinkedIn: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
