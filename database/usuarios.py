import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime

from database import db

ITERACIONES = 600_000
CLAVE_MIN = 10
_FALSO = None


def hashear(clave: str) -> str:
    sal = secrets.token_bytes(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, ITERACIONES).hex()
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${resumen}"


def comprobar(clave: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = guardado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        calculado = hashlib.pbkdf2_hmac(
            "sha256", clave.encode(), bytes.fromhex(sal), int(iteraciones)
        ).hex()
    except ValueError:
        return False
    return hmac.compare_digest(calculado, esperado)


def _hash_falso() -> str:
    global _FALSO
    if _FALSO is None:
        _FALSO = hashear("relleno")
    return _FALSO


def _asegurar_tabla(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS administradores (
            id         INTEGER PRIMARY KEY,
            usuario    TEXT NOT NULL UNIQUE,
            clave_hash TEXT NOT NULL,
            creado_en  TEXT NOT NULL
        )
        """
    )


def crear_admin(usuario: str, clave: str) -> None:
    usuario = usuario.strip().lower()
    if not usuario:
        raise ValueError("El usuario no puede estar vacío.")
    if len(clave) < CLAVE_MIN:
        raise ValueError(f"La clave debe tener al menos {CLAVE_MIN} caracteres.")
    db.inicializar()
    con = db.conectar()
    try:
        with con:
            _asegurar_tabla(con)
            con.execute(
                "INSERT INTO administradores (usuario, clave_hash, creado_en) VALUES (?, ?, ?)",
                (usuario, hashear(clave), datetime.now().isoformat(timespec="seconds")),
            )
    except sqlite3.IntegrityError:
        raise ValueError("Ese usuario ya existe.") from None
    finally:
        con.close()


def hay_admins() -> bool:
    db.inicializar()
    con = db.conectar()
    try:
        _asegurar_tabla(con)
        return con.execute("SELECT COUNT(*) FROM administradores").fetchone()[0] > 0
    finally:
        con.close()


def verificar(usuario: str, clave: str) -> bool:
    db.inicializar()
    con = db.conectar()
    try:
        _asegurar_tabla(con)
        fila = con.execute(
            "SELECT clave_hash FROM administradores WHERE usuario = ?",
            (usuario.strip().lower(),),
        ).fetchone()
    finally:
        con.close()
    if fila is None:
        comprobar(clave, _hash_falso())  # gasta el mismo tiempo que un usuario real
        return False
    return comprobar(clave, fila[0])
