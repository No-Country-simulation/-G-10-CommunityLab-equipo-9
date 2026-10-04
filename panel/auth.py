"""
Inicio de sesión del panel (T07, DEC-110, S3): usuario y contraseña por persona.

Las contraseñas nunca se guardan: se guarda un hash scrypt con sal en la variable PANEL_USUARIOS del .env
de la raíz, que escribe scripts/crear_usuario_panel.py. Formato (sin "$": Docker Compose los reemplaza):

    PANEL_USUARIOS=harrison:scrypt:16384:8:1:<sal en hex>:<hash en hex>,ana:scrypt:...

- scrypt es lento a propósito (unos 50 ms y 16 MB por intento): adivinar por fuerza bruta sale caro.
- La comparación es en tiempo constante (hmac.compare_digest), y un usuario que no existe cuesta lo mismo
  que uno que existe (se calcula un hash de relleno): midiendo tiempos no se sabe qué usuarios hay.
- Sin usuarios configurados, nadie entra.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import threading
import time
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# El mismo formato que valida Java en X-Usuario (CuraduriaService.USUARIO_VALIDO)
USUARIO_VALIDO = re.compile(r"[A-Za-z0-9._-]{1,40}")
MIN_LARGO_CONTRASENA = 10
# Una pausa después de cada contraseña equivocada (la hace app.py): frena a quien prueba muchas
PAUSA_FALLO_S = 2.0

ALGORITMO = "scrypt"
N, R, P = 2**14, 8, 1
LARGO_SAL = 16
LARGO_HASH = 32
# Topes al leer un registro: un PANEL_USUARIOS alterado no puede pedir un scrypt de varios GB
MAX_N, MAX_R, MAX_P = 2**20, 16, 4


@dataclass(frozen=True)
class Registro:
    """El hash de una contraseña, con lo necesario para volver a calcularlo."""
    n: int
    r: int
    p: int
    sal: bytes
    hash: bytes = field(repr=False)

    def texto(self) -> str:
        return f"{ALGORITMO}:{self.n}:{self.r}:{self.p}:{self.sal.hex()}:{self.hash.hex()}"


def _scrypt(contrasena: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, n=n, r=r, p=p,
                          maxmem=256 * 1024 * 1024, dklen=LARGO_HASH)


def crear_registro(contrasena: str, sal: bytes | None = None) -> Registro:
    """El hash de una contraseña nueva, con una sal al azar."""
    sal = sal if sal is not None else secrets.token_bytes(LARGO_SAL)
    return Registro(N, R, P, sal, _scrypt(contrasena, sal, N, R, P))


def leer_registro(texto: str) -> Registro | None:
    """El registro "scrypt:n:r:p:sal:hash", o None si no tiene el formato."""
    partes = texto.strip().split(":")
    if len(partes) != 6 or partes[0] != ALGORITMO:
        return None
    try:
        n, r, p = int(partes[1]), int(partes[2]), int(partes[3])
        sal, hash_ = bytes.fromhex(partes[4]), bytes.fromhex(partes[5])
    except ValueError:
        return None
    # n tiene que ser potencia de 2 (lo exige scrypt)
    if not (1 < n <= MAX_N and n & (n - 1) == 0 and 0 < r <= MAX_R and 0 < p <= MAX_P):
        return None
    if len(sal) < 8 or len(hash_) != LARGO_HASH:
        return None
    return Registro(n, r, p, sal, hash_)


def leer_usuarios(texto: str | None) -> dict[str, Registro]:
    """Los usuarios de PANEL_USUARIOS. Las entradas mal escritas se ignoran (y se avisa, sin mostrarlas)."""
    usuarios: dict[str, Registro] = {}
    for entrada in (texto or "").split(","):
        entrada = entrada.strip()
        if not entrada:
            continue
        usuario, _, resto = entrada.partition(":")
        registro = leer_registro(resto)
        if not USUARIO_VALIDO.fullmatch(usuario) or registro is None:
            log.warning("PANEL_USUARIOS tiene una entrada mal escrita: se ignora.")
            continue
        usuarios[usuario] = registro
    return usuarios


def con_usuario(texto: str | None, usuario: str, registro: Registro) -> str:
    """El valor de PANEL_USUARIOS con el usuario agregado, o con su contraseña cambiada si ya estaba."""
    entradas = [e.strip() for e in (texto or "").split(",") if e.strip()]
    nueva = f"{usuario}:{registro.texto()}"
    for i, entrada in enumerate(entradas):
        if entrada.partition(":")[0] == usuario:
            entradas[i] = nueva
            return ",".join(entradas)
    return ",".join([*entradas, nueva])


# Un hash de relleno para los usuarios que no existen: así tardan lo mismo que los que existen
_RELLENO = Registro(N, R, P, b"\x00" * LARGO_SAL, b"\x00" * LARGO_HASH)


def verificar(usuarios: dict[str, Registro], usuario: str, contrasena: str) -> bool:
    """True solo si el usuario existe y la contraseña es la suya."""
    registro = usuarios.get(usuario)
    existe = registro is not None
    registro = registro or _RELLENO
    calculado = _scrypt(contrasena, registro.sal, registro.n, registro.r, registro.p)
    coincide = hmac.compare_digest(calculado, registro.hash)
    return existe and coincide


class ControlIntentos:
    """
    Frena a quien prueba contraseñas: después de MAX_FALLOS fallos seguidos con el mismo usuario, ese usuario
    queda bloqueado BLOQUEO_S segundos (exista o no, para no revelar cuáles existen). Es uno por proceso del
    panel, compartido por todas las pestañas. Contra: alguien podría bloquear a otra persona unos minutos.
    """

    MAX_FALLOS = 5
    BLOQUEO_S = 300

    def __init__(self, reloj=time.monotonic):
        self._reloj = reloj
        self._lock = threading.Lock()
        self._fallos: dict[str, int] = {}
        self._bloqueado_hasta: dict[str, float] = {}

    def bloqueado(self, usuario: str) -> bool:
        with self._lock:
            hasta = self._bloqueado_hasta.get(usuario)
            if hasta is None:
                return False
            if self._reloj() >= hasta:
                del self._bloqueado_hasta[usuario]
                self._fallos.pop(usuario, None)
                return False
            return True

    def fallo(self, usuario: str) -> None:
        with self._lock:
            # Tope de usuarios distintos en memoria: alguien podría inventar millones
            if len(self._fallos) > 10_000:
                self._fallos.clear()
            self._fallos[usuario] = self._fallos.get(usuario, 0) + 1
            if self._fallos[usuario] >= self.MAX_FALLOS:
                self._bloqueado_hasta[usuario] = self._reloj() + self.BLOQUEO_S

    def exito(self, usuario: str) -> None:
        with self._lock:
            self._fallos.pop(usuario, None)
            self._bloqueado_hasta.pop(usuario, None)
