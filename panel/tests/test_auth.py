"""Contraseñas del panel (T07, DEC-110): hash scrypt con sal, comparación en tiempo constante y freno de intentos."""
import auth

CONTRASENA = "una-clave-larga-123"


def test_la_contrasena_correcta_entra_y_las_otras_no():
    usuarios = {"harrison": auth.crear_registro(CONTRASENA)}

    assert auth.verificar(usuarios, "harrison", CONTRASENA)
    assert not auth.verificar(usuarios, "harrison", CONTRASENA + "x")
    assert not auth.verificar(usuarios, "harrison", "")
    assert not auth.verificar(usuarios, "Harrison", CONTRASENA)  # el usuario se compara exacto
    assert not auth.verificar(usuarios, "nadie", CONTRASENA)


def test_sin_usuarios_nadie_entra():
    assert auth.leer_usuarios("") == {}
    assert auth.leer_usuarios(None) == {}
    assert not auth.verificar({}, "harrison", CONTRASENA)


def test_el_hash_nunca_es_la_contrasena_y_lleva_sal():
    a = auth.crear_registro(CONTRASENA)
    b = auth.crear_registro(CONTRASENA)

    assert CONTRASENA not in a.texto()
    assert CONTRASENA.encode().hex() not in a.texto()
    assert a.hash != CONTRASENA.encode()
    # Misma contraseña, sal distinta: hashes distintos (no se pueden comparar entre usuarios)
    assert a.sal != b.sal and a.hash != b.hash
    # Sin "$": Docker Compose los reemplazaría en el .env
    assert "$" not in a.texto()
    assert a.hash.hex() not in repr(a)


def test_se_lee_lo_que_se_escribe():
    texto = auth.con_usuario("", "harrison", auth.crear_registro(CONTRASENA))
    texto = auth.con_usuario(texto, "ana.m", auth.crear_registro("otra-clave-larga"))

    usuarios = auth.leer_usuarios(texto)

    assert list(usuarios) == ["harrison", "ana.m"]
    assert auth.verificar(usuarios, "harrison", CONTRASENA)
    assert auth.verificar(usuarios, "ana.m", "otra-clave-larga")


def test_cambiar_la_contrasena_reemplaza_solo_ese_usuario():
    texto = auth.con_usuario("", "harrison", auth.crear_registro(CONTRASENA))
    texto = auth.con_usuario(texto, "ana", auth.crear_registro("clave-de-ana-123"))

    texto = auth.con_usuario(texto, "harrison", auth.crear_registro("clave-nueva-456"))

    usuarios = auth.leer_usuarios(texto)
    assert list(usuarios) == ["harrison", "ana"]
    assert auth.verificar(usuarios, "harrison", "clave-nueva-456")
    assert not auth.verificar(usuarios, "harrison", CONTRASENA)
    assert auth.verificar(usuarios, "ana", "clave-de-ana-123")


def test_las_entradas_mal_escritas_se_ignoran():
    bueno = f"harrison:{auth.crear_registro(CONTRASENA).texto()}"
    malos = [
        "sin-dos-puntos",
        "ana:md5:1:2:3:aa:bb",                                        # otro algoritmo
        "beto:scrypt:16384:8:1:zz:" + "00" * 32,                       # sal que no es hex
        "caro:scrypt:3:8:1:" + "00" * 16 + ":" + "00" * 32,            # n no es potencia de 2
        "dani:scrypt:1073741824:8:1:" + "00" * 16 + ":" + "00" * 32,   # n enorme: pediría GB de memoria
        "josé:" + auth.crear_registro(CONTRASENA).texto(),             # usuario con tilde
    ]

    usuarios = auth.leer_usuarios(",".join([*malos, bueno]))

    assert list(usuarios) == ["harrison"]


def test_cinco_fallos_bloquean_al_usuario_cinco_minutos():
    ahora = [1000.0]
    control = auth.ControlIntentos(reloj=lambda: ahora[0])

    for _ in range(4):
        control.fallo("harrison")
    assert not control.bloqueado("harrison")
    control.fallo("harrison")
    assert control.bloqueado("harrison")
    assert not control.bloqueado("ana")  # los demás siguen pudiendo entrar

    ahora[0] += auth.ControlIntentos.BLOQUEO_S
    assert not control.bloqueado("harrison")


def test_un_acierto_reinicia_la_cuenta():
    control = auth.ControlIntentos(reloj=lambda: 0.0)
    for _ in range(4):
        control.fallo("harrison")
    control.exito("harrison")
    control.fallo("harrison")

    assert not control.bloqueado("harrison")
