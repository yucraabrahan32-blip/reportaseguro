"""Administradores del sistema. Las claves se guardan solo como hash con sal (PBKDF2)."""
import hashlib
import hmac
import secrets
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database import db
from database.modelos import Administrador, Session

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


def crear_admin(usuario: str, clave: str) -> None:
    usuario = usuario.strip().lower()
    if not usuario:
        raise ValueError("El usuario no puede estar vacío.")
    if len(clave) < CLAVE_MIN:
        raise ValueError(f"La clave debe tener al menos {CLAVE_MIN} caracteres.")
    db.inicializar()
    try:
        with Session.begin() as s:
            s.add(Administrador(
                usuario=usuario, clave_hash=hashear(clave),
                creado_en=datetime.now().isoformat(timespec="seconds"),
            ))
    except IntegrityError:
        raise ValueError("Ese usuario ya existe.") from None


def hay_admins() -> bool:
    db.inicializar()
    with Session() as s:
        return s.scalar(select(func.count()).select_from(Administrador)) > 0


def verificar(usuario: str, clave: str) -> bool:
    db.inicializar()
    with Session() as s:
        guardado = s.scalar(
            select(Administrador.clave_hash).where(Administrador.usuario == usuario.strip().lower())
        )
    if guardado is None:
        comprobar(clave, _hash_falso())  # gasta el mismo tiempo que un usuario real
        return False
    return comprobar(clave, guardado)