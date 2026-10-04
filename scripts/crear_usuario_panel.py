"""
Crea (o cambia) un usuario del panel de curaduría y escribe su hash, SIN MOSTRAR la contraseña ni el hash,
en la variable PANEL_USUARIOS del .env de la raíz (T07, DEC-110).

La contraseña se pide dos veces sin mostrarla en pantalla (getpass). Nunca se guarda: se guarda un hash
scrypt con sal (panel/auth.py). Solo cambia la línea PANEL_USUARIOS; el resto del .env queda igual.
Si el usuario ya existe, no lo cambia salvo con --reemplazar.

Uso, desde la raíz del repositorio:
    python scripts/crear_usuario_panel.py
    python scripts/crear_usuario_panel.py --usuario harrison
    python scripts/crear_usuario_panel.py --usuario harrison --reemplazar     (cambiar la contraseña)
Después: docker compose up -d panel   (para que el panel tome el usuario nuevo)
"""
import argparse
import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "panel"))

import auth  # noqa: E402  (panel/auth.py: el mismo hash que verifica el panel)
from generar_api_key import con_variable, valor_actual  # noqa: E402

VARIABLE = "PANEL_USUARIOS"
ENV = RAIZ / ".env"


def crear(usuario: str, contrasena: str, ruta_env: Path = ENV, reemplazar: bool = False) -> int:
    if not auth.USUARIO_VALIDO.fullmatch(usuario):
        print("❌ El usuario solo puede tener letras sin tilde, números, '.', '_' y '-' (hasta 40).")
        return 1
    if len(contrasena) < auth.MIN_LARGO_CONTRASENA:
        print(f"❌ La contraseña tiene que tener al menos {auth.MIN_LARGO_CONTRASENA} caracteres.")
        return 1
    if not ruta_env.exists():
        print("❌ No existe el .env de la raíz. Primero copia .env.example como .env.")
        return 1

    # read_bytes y no read_text: read_text convierte \r\n en \n y el archivo cambiaría entero
    texto = ruta_env.read_bytes().decode("utf-8")
    actual = valor_actual(texto, VARIABLE)
    if usuario in auth.leer_usuarios(actual) and not reemplazar:
        print(f"⚠️ El usuario {usuario} ya existe. No se cambió nada.")
        print("   Para cambiar su contraseña, agrega --reemplazar al mismo comando.")
        return 1

    nuevo = auth.con_usuario(actual, usuario, auth.crear_registro(contrasena))
    # newline="" respeta los saltos de línea que ya tenía el archivo
    ruta_env.write_text(con_variable(texto, VARIABLE, nuevo), encoding="utf-8", newline="")
    print(f"✅ Usuario {usuario} guardado en .env ({VARIABLE}). La contraseña no se mostró ni se guardó.")
    print("   Para que el panel lo use: docker compose up -d panel")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea un usuario del panel y guarda su hash en el .env.")
    parser.add_argument("--usuario", help="el nombre para entrar al panel (si no, se pregunta)")
    parser.add_argument("--reemplazar", action="store_true", help="cambiar la contraseña de un usuario que ya existe")
    args = parser.parse_args()

    usuario = (args.usuario or input("Usuario: ")).strip()
    contrasena = getpass.getpass("Contraseña (no se ve al escribir): ")
    if getpass.getpass("Repite la contraseña: ") != contrasena:
        print("❌ Las dos contraseñas no coinciden. No se cambió nada.")
        return 1
    return crear(usuario, contrasena, reemplazar=args.reemplazar)


if __name__ == "__main__":
    sys.exit(main())
