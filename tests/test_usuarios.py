import pytest

from database import db, usuarios

CLAVE = "clave-segura-123"


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    monkeypatch.setattr(usuarios, "ITERACIONES", 1000)  # rápido en las pruebas


def test_crear_y_verificar(base):
    usuarios.crear_admin("admin", CLAVE)
    assert usuarios.verificar("admin", CLAVE)


def test_clave_incorrecta(base):
    usuarios.crear_admin("admin", CLAVE)
    assert not usuarios.verificar("admin", "otra-clave-larga")


def test_usuario_inexistente(base):
    assert not usuarios.verificar("nadie", CLAVE)


def test_usuario_sin_distinguir_mayusculas_ni_espacios(base):
    usuarios.crear_admin("Admin ", CLAVE)
    assert usuarios.verificar(" ADMIN", CLAVE)


def test_la_clave_no_se_guarda_en_texto(base):
    usuarios.crear_admin("admin", CLAVE)
    con = db.conectar()
    try:
        guardado = con.execute("SELECT clave_hash FROM administradores").fetchone()[0]
    finally:
        con.close()
    assert guardado.startswith("pbkdf2_sha256$")
    assert CLAVE not in guardado


def test_la_misma_clave_da_hashes_distintos():
    assert usuarios.hashear(CLAVE) != usuarios.hashear(CLAVE)


@pytest.mark.parametrize("usuario, clave", [("admin", "corta"), ("  ", CLAVE)])
def test_datos_invalidos_se_rechazan(base, usuario, clave):
    with pytest.raises(ValueError):
        usuarios.crear_admin(usuario, clave)


def test_usuario_duplicado(base):
    usuarios.crear_admin("admin", CLAVE)
    with pytest.raises(ValueError):
        usuarios.crear_admin("admin", CLAVE)


def test_hay_admins(base):
    assert not usuarios.hay_admins()
    usuarios.crear_admin("admin", CLAVE)
    assert usuarios.hay_admins()


def test_formato_de_hash_invalido():
    assert not usuarios.comprobar(CLAVE, "basura")
    assert not usuarios.comprobar(CLAVE, "md5$1$aa$bb")
    assert not usuarios.comprobar(CLAVE, "pbkdf2_sha256$x$zz$bb")
