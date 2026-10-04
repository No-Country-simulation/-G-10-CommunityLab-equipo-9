"""scripts/crear_usuario_panel.py: escribe el hash sin mostrar la contraseña y conserva el resto del .env."""
import auth
import crear_usuario_panel as script

CONTRASENA = "mi-clave-secreta-789"
ENV_ORIGINAL = "POSTGRES_DB=insightedu\r\nAPI_KEY_PANEL=algo\r\n# comentario\r\nPANEL_USUARIOS=\r\nOTRA=1\r\n"


def _env(tmp_path, texto=ENV_ORIGINAL):
    ruta = tmp_path / ".env"
    ruta.write_bytes(texto.encode("utf-8"))
    return ruta


def _usuarios(ruta):
    texto = ruta.read_bytes().decode("utf-8")
    return auth.leer_usuarios(script.valor_actual(texto, script.VARIABLE))


def test_crea_el_usuario_sin_mostrar_la_contrasena_ni_el_hash(tmp_path, capsys):
    ruta = _env(tmp_path)

    assert script.crear("harrison", CONTRASENA, ruta) == 0

    salida = capsys.readouterr().out
    usuarios = _usuarios(ruta)
    assert auth.verificar(usuarios, "harrison", CONTRASENA)
    assert CONTRASENA not in salida
    assert usuarios["harrison"].hash.hex() not in salida
    assert CONTRASENA not in ruta.read_bytes().decode("utf-8")


def test_conserva_el_resto_del_env_y_sus_saltos_de_linea(tmp_path):
    ruta = _env(tmp_path)

    script.crear("harrison", CONTRASENA, ruta)

    texto = ruta.read_bytes().decode("utf-8")
    lineas = texto.split("\r\n")
    assert lineas[0] == "POSTGRES_DB=insightedu"
    assert lineas[1] == "API_KEY_PANEL=algo"
    assert lineas[2] == "# comentario"
    assert lineas[3].startswith("PANEL_USUARIOS=harrison:scrypt:")
    assert lineas[4] == "OTRA=1"
    assert "\n" not in texto.replace("\r\n", "")


def test_agrega_la_variable_si_no_estaba(tmp_path):
    ruta = _env(tmp_path, "POSTGRES_DB=insightedu\n")

    script.crear("harrison", CONTRASENA, ruta)

    texto = ruta.read_bytes().decode("utf-8")
    assert texto.startswith("POSTGRES_DB=insightedu\nPANEL_USUARIOS=harrison:scrypt:")
    assert "\r" not in texto


def test_un_usuario_que_ya_existe_no_se_pisa_sin_reemplazar(tmp_path):
    ruta = _env(tmp_path)
    script.crear("harrison", CONTRASENA, ruta)
    script.crear("ana", "clave-de-ana-123", ruta)
    antes = ruta.read_bytes()

    assert script.crear("harrison", "otra-clave-larga", ruta) == 1
    assert ruta.read_bytes() == antes

    assert script.crear("harrison", "otra-clave-larga", ruta, reemplazar=True) == 0
    usuarios = _usuarios(ruta)
    assert auth.verificar(usuarios, "harrison", "otra-clave-larga")
    assert auth.verificar(usuarios, "ana", "clave-de-ana-123")


def test_rechaza_usuarios_raros_y_contrasenas_cortas(tmp_path):
    ruta = _env(tmp_path)

    assert script.crear("josé", CONTRASENA, ruta) == 1
    assert script.crear("ana maría", CONTRASENA, ruta) == 1
    assert script.crear("harrison", "corta", ruta) == 1
    assert ruta.read_bytes().decode("utf-8") == ENV_ORIGINAL


def test_main_pide_la_contrasena_con_getpass_y_no_la_muestra(tmp_path, monkeypatch, capsys):
    ruta = _env(tmp_path)
    monkeypatch.setattr(script.crear, "__defaults__", (ruta, False))
    pedidas = []
    monkeypatch.setattr(script.getpass, "getpass", lambda texto: pedidas.append(texto) or CONTRASENA)
    monkeypatch.setattr("sys.argv", ["crear_usuario_panel.py", "--usuario", "harrison"])

    assert script.main() == 0

    assert len(pedidas) == 2  # la pide dos veces, para no guardar una con un error de tipeo
    assert CONTRASENA not in capsys.readouterr().out
    assert auth.verificar(_usuarios(ruta), "harrison", CONTRASENA)


def test_main_no_guarda_nada_si_las_contrasenas_no_coinciden(tmp_path, monkeypatch):
    ruta = _env(tmp_path)
    monkeypatch.setattr(script.crear, "__defaults__", (ruta, False))
    respuestas = iter([CONTRASENA, CONTRASENA + "x"])
    monkeypatch.setattr(script.getpass, "getpass", lambda texto: next(respuestas))
    monkeypatch.setattr("sys.argv", ["crear_usuario_panel.py", "--usuario", "harrison"])

    assert script.main() == 1
    assert ruta.read_bytes().decode("utf-8") == ENV_ORIGINAL
