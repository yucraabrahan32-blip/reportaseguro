"""Pruebas unitarias de los modelos de dominio (Incidente y Ubicacion).

Estos objetos se validan a si mismos con el metodo .validar(). Aqui comprobamos
que aceptan los datos correctos y rechazan los incorrectos.
"""
from datetime import date, timedelta

import pytest

from backend.models import Incidente, Ubicacion


def _incidente_valido(**cambios):
    """Crea un incidente correcto; 'cambios' permite alterar un campo para probar errores."""
    datos = dict(
        ubicacion=Ubicacion("LIMA", "LIMA", "MIRAFLORES"),
        delito="ROBO",
        fecha_hecho=date(2025, 1, 1),
        hora_hecho="14:30",
        descripcion="Robo de celular cerca del parque",
    )
    datos.update(cambios)
    return Incidente(**datos)


# ---------- Ubicacion ----------
def test_ubicacion_valida_no_lanza_error():
    Ubicacion("LIMA", "LIMA", "MIRAFLORES").validar()


def test_ubicacion_incompleta_lanza_error():
    # Si falta el distrito, debe lanzar ValueError.
    with pytest.raises(ValueError):
        Ubicacion("LIMA", "LIMA", "").validar()


# ---------- Incidente ----------
def test_incidente_valido_no_lanza_error():
    _incidente_valido().validar()


def test_incidente_rechaza_fecha_futura():
    # La fecha del hecho no puede ser posterior a hoy.
    manana = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        _incidente_valido(fecha_hecho=manana).validar()


def test_incidente_rechaza_hora_mal_escrita():
    # La hora debe tener formato HH:MM.
    with pytest.raises(ValueError):
        _incidente_valido(hora_hecho="25h").validar()


def test_incidente_rechaza_delito_invalido():
    with pytest.raises(ValueError):
        _incidente_valido(delito="SECUESTRO").validar()
