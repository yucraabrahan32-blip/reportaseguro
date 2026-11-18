"""Límite de intentos fallidos de inicio de sesión (se guarda en la base, no en el navegador)."""
import sqlite3
import time
from typing import NamedTuple

from database import db, usuarios

MAX_FALLOS = 5
BLOQUEO_SEG = 300
RETENCION_SEG = 86_400


class ResultadoLogin(NamedTuple):
    estado: str  # "ok", "incorrecto" o "bloqueado"
    segundos: int = 0  # espera restante, si está bloqueado
    restantes: int = 0  # intentos que quedan antes del bloqueo


def _asegurar_tabla(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS intentos_login (
            usuario         TEXT PRIMARY KEY,
            fallos          INTEGER NOT NULL,
            bloqueado_hasta REAL NOT NULL DEFAULT 0,
            ultimo_intento  REAL NOT NULL
        )
        """
    )


def _nombre(usuario: str) -> str:
    return usuario.strip().lower()[:64]


def _borrar(nombre: str) -> None:
    con = db.conectar()
    try:
        with con:
            _asegurar_tabla(con)
            con.execute("DELETE FROM intentos_login WHERE usuario = ?", (nombre,))
    finally:
        con.close()


def _registrar_fallo(nombre: str, fila, ahora: float) -> ResultadoLogin:
    previos = fila[0] if fila else 0
    if fila and 0 < fila[1] <= ahora:
        previos = 0  # el bloqueo anterior ya venció: se empieza de cero
    fallos = previos + 1
    hasta = ahora + BLOQUEO_SEG if fallos >= MAX_FALLOS else 0.0
    con = db.conectar()
    try:
        with con:
            _asegurar_tabla(con)
            con.execute("DELETE FROM intentos_login WHERE ultimo_intento < ?", (ahora - RETENCION_SEG,))
            con.execute(
                "INSERT INTO intentos_login (usuario, fallos, bloqueado_hasta, ultimo_intento) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT (usuario) DO UPDATE SET fallos = excluded.fallos, "
                "bloqueado_hasta = excluded.bloqueado_hasta, ultimo_intento = excluded.ultimo_intento",
                (nombre, fallos, hasta, ahora),
            )
    finally:
        con.close()
    if hasta:
        return ResultadoLogin("bloqueado", BLOQUEO_SEG)
    return ResultadoLogin("incorrecto", restantes=MAX_FALLOS - fallos)


def verificar_con_limite(usuario: str, clave: str, ahora: float | None = None) -> ResultadoLogin:
    """Verifica la clave respetando el límite de intentos. También cuenta los usuarios que no existen."""
    ahora = time.time() if ahora is None else ahora
    nombre = _nombre(usuario)
    db.inicializar()
    con = db.conectar()
    try:
        with con:
            _asegurar_tabla(con)
            fila = con.execute(
                "SELECT fallos, bloqueado_hasta FROM intentos_login WHERE usuario = ?", (nombre,)
            ).fetchone()
    finally:
        con.close()
    if fila and fila[1] > ahora:
        return ResultadoLogin("bloqueado", int(fila[1] - ahora) + 1)
    if usuarios.verificar(usuario, clave):
        _borrar(nombre)
        return ResultadoLogin("ok")
    return _registrar_fallo(nombre, fila, ahora)
