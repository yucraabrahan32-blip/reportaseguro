"""Límite de intentos fallidos de inicio de sesión (se guarda en la base, no en el navegador)."""
import time
from typing import NamedTuple

from sqlalchemy import delete, select

from database import db, usuarios
from database.modelos import IntentoLogin, Session

MAX_FALLOS = 5
BLOQUEO_SEG = 300
RETENCION_SEG = 86_400


class ResultadoLogin(NamedTuple):
    estado: str  # "ok", "incorrecto" o "bloqueado"
    segundos: int = 0  # espera restante, si está bloqueado
    restantes: int = 0  # intentos que quedan antes del bloqueo


def _nombre(usuario: str) -> str:
    return usuario.strip().lower()[:64]


def _borrar(nombre: str) -> None:
    with Session.begin() as s:
        s.execute(delete(IntentoLogin).where(IntentoLogin.usuario == nombre))


def _registrar_fallo(nombre: str, fila, ahora: float) -> ResultadoLogin:
    previos = fila[0] if fila else 0
    if fila and 0 < fila[1] <= ahora:
        previos = 0  # el bloqueo anterior ya venció: se empieza de cero
    fallos = previos + 1
    hasta = ahora + BLOQUEO_SEG if fallos >= MAX_FALLOS else 0.0
    with Session.begin() as s:
        s.execute(delete(IntentoLogin).where(IntentoLogin.ultimo_intento < ahora - RETENCION_SEG))
        s.merge(IntentoLogin(
            usuario=nombre, fallos=fallos, bloqueado_hasta=hasta, ultimo_intento=ahora
        ))
    if hasta:
        return ResultadoLogin("bloqueado", BLOQUEO_SEG)
    return ResultadoLogin("incorrecto", restantes=MAX_FALLOS - fallos)


def verificar_con_limite(usuario: str, clave: str, ahora: float | None = None) -> ResultadoLogin:
    """Verifica la clave respetando el límite de intentos. También cuenta los usuarios que no existen."""
    ahora = time.time() if ahora is None else ahora
    nombre = _nombre(usuario)
    db.inicializar()
    with Session() as s:
        fila = s.execute(
            select(IntentoLogin.fallos, IntentoLogin.bloqueado_hasta)
            .where(IntentoLogin.usuario == nombre)
        ).first()
    if fila and fila[1] > ahora:
        return ResultadoLogin("bloqueado", int(fila[1] - ahora) + 1)
    if usuarios.verificar(usuario, clave):
        _borrar(nombre)
        return ResultadoLogin("ok")
    return _registrar_fallo(nombre, fila, ahora)