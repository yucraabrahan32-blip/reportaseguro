import pytest

from database import db, usuarios
from database.limite_login import BLOQUEO_SEG, MAX_FALLOS, verificar_con_limite

CLAVE = "clave-segura-123"
MALA = "clave-equivocada-1"


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    monkeypatch.setattr(usuarios, "ITERACIONES", 1000)  # rápido en las pruebas
    usuarios.crear_admin("admin", CLAVE)
    usuarios.crear_admin("otro", CLAVE)


def fallar(veces, usuario="admin", t=1000.0):
    return [verificar_con_limite(usuario, MALA, ahora=t) for _ in range(veces)]


def test_cinco_fallos_bloquean_y_cuentan_los_intentos_restantes(base):
    resultados = fallar(MAX_FALLOS)
    assert [r.estado for r in resultados] == ["incorrecto"] * (MAX_FALLOS - 1) + ["bloqueado"]
    assert [r.restantes for r in resultados[:-1]] == [4, 3, 2, 1]
    assert resultados[-1].segundos == BLOQUEO_SEG


def test_bloqueado_ni_la_clave_correcta_entra(base):
    fallar(MAX_FALLOS, t=1000.0)
    r = verificar_con_limite("admin", CLAVE, ahora=1100.0)
    assert r.estado == "bloqueado"
    assert 200 <= r.segundos <= 201


def test_pasado_el_bloqueo_se_puede_entrar(base):
    fallar(MAX_FALLOS, t=1000.0)
    assert verificar_con_limite("admin", CLAVE, ahora=1000.0 + BLOQUEO_SEG + 1).estado == "ok"


def test_despues_del_bloqueo_un_fallo_cuenta_como_el_primero(base):
    fallar(MAX_FALLOS, t=1000.0)
    r = verificar_con_limite("admin", MALA, ahora=1000.0 + BLOQUEO_SEG + 1)
    assert r.estado == "incorrecto" and r.restantes == MAX_FALLOS - 1


def test_entrar_bien_reinicia_el_contador(base):
    fallar(3)
    assert verificar_con_limite("admin", CLAVE, ahora=1000.0).estado == "ok"
    assert {r.estado for r in fallar(MAX_FALLOS - 1)} == {"incorrecto"}


def test_un_usuario_inexistente_tambien_se_bloquea(base):
    assert fallar(MAX_FALLOS, usuario="nadie")[-1].estado == "bloqueado"


def test_mayusculas_y_espacios_comparten_contador(base):
    for _ in range(3):
        verificar_con_limite("Admin ", MALA, ahora=1000.0)
    verificar_con_limite("ADMIN", MALA, ahora=1000.0)
    assert verificar_con_limite("admin", MALA, ahora=1000.0).estado == "bloqueado"


def test_el_bloqueo_de_un_usuario_no_afecta_a_otro(base):
    fallar(MAX_FALLOS, usuario="admin")
    assert verificar_con_limite("otro", CLAVE, ahora=1000.0).estado == "ok"
