"""Pruebas unitarias de las reglas de validacion (backend/models/validaciones.py).

Cada prueba verifica UNA regla. El patron es siempre el mismo:
  1. Preparar el dato de entrada.
  2. Ejecutar la funcion.
  3. Comprobar el resultado (que pase, o que lance el error esperado).
"""
import pytest

from backend.models.validaciones import (
    DELITOS, validar_delito, validar_descripcion,
)


def test_validar_delito_acepta_los_tipos_validos():
    # Todos los delitos del catalogo oficial deben pasar sin lanzar error.
    for delito in DELITOS:
        validar_delito(delito)   # si lanzara una excepcion, la prueba fallaria


def test_validar_delito_rechaza_un_tipo_invalido():
    # Un delito que no esta en el catalogo debe lanzar ValueError.
    with pytest.raises(ValueError):
        validar_delito("SECUESTRO")


def test_validar_descripcion_acepta_un_texto_normal():
    # Una descripcion con largo adecuado no debe lanzar error.
    validar_descripcion("Robo de celular en la avenida principal")


def test_validar_descripcion_rechaza_texto_muy_corto():
    # Menos de 10 caracteres debe lanzar ValueError.
    with pytest.raises(ValueError):
        validar_descripcion("corto")


def test_validar_descripcion_rechaza_texto_muy_largo():
    # Mas de 500 caracteres debe lanzar ValueError.
    with pytest.raises(ValueError):
        validar_descripcion("a" * 501)
