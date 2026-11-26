"""Pruebas unitarias de la funcion normalizar (backend/ubigeo.py).

normalizar() limpia un texto: lo pasa a mayusculas, le quita tildes y signos,
y deja espacios simples. Sirve para comparar nombres de distritos sin importar
como fueron escritos.
"""
from backend.ubigeo import normalizar


def test_normalizar_pasa_a_mayusculas():
    assert normalizar("miraflores") == "MIRAFLORES"


def test_normalizar_quita_tildes():
    assert normalizar("Áncash") == "ANCASH"


def test_normalizar_quita_signos_y_espacios_extra():
    # Los signos se vuelven espacios y los espacios dobles se colapsan.
    assert normalizar("San  Juan-de  Lurigancho") == "SAN JUAN DE LURIGANCHO"
