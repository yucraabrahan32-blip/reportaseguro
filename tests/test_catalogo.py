import pytest

from backend import ubigeo
from backend.ubigeo import CatalogoUbigeo
from database import db

CSV = """inei,reniec,departamento,provincia,distrito,superficie,pob_densidad_2020,altitude,latitude,longitude
000001,000001,AREQUIPA,AREQUIPA,CAYMA,10,1000,2400,-16.37,-71.53
000002,000002,AREQUIPA,AREQUIPA,YANAHUARA,5,2000,2350,-16.39,-71.54
000003,000003,LIMA,LIMA,LURIGANCHO,100,500,400,-11.9,-76.9
000004,000004,LIMA,LIMA,ANCON,200,50,50,-11.7,-77.1
"""


@pytest.fixture
def catalogo(tmp_path, monkeypatch):
    archivo = tmp_path / "ubigeo.csv"
    archivo.write_text(CSV, encoding="utf-8")
    monkeypatch.setattr(ubigeo, "RUTA_CSV", archivo)
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    return CatalogoUbigeo()


def test_cargar_devuelve_la_cantidad_de_distritos(catalogo):
    assert catalogo.cargar() == 4


def test_consulta_en_cascada(catalogo):
    catalogo.cargar()
    assert catalogo.departamentos() == ["AREQUIPA", "LIMA"]
    assert catalogo.provincias("AREQUIPA") == ["AREQUIPA"]
    assert catalogo.distritos("AREQUIPA", "AREQUIPA") == ["CAYMA", "YANAHUARA"]


def test_clave_normaliza_y_aplica_alias(catalogo):
    assert catalogo.clave("Ancón") == "ANCON"
    assert catalogo.clave("LURIGANCHO - CHOSICA") == "LURIGANCHO"


def test_sin_cargar_el_catalogo_las_consultas_salen_vacias(catalogo):
    assert catalogo.departamentos() == []
