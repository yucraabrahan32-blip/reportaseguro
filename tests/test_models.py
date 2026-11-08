from datetime import date, timedelta

import pandas as pd
import pytest

from backend.models import CalculadoraRiesgo, Incidente, RepositorioIncidentes, Ubicacion
from backend.regional import _fila
from backend.ubigeo import normalizar
from database import db

UBICACION = Ubicacion("AREQUIPA", "AREQUIPA", "CAYMA")


def un_incidente(**cambios):
    datos = dict(
        ubicacion=UBICACION, delito="ROBO", fecha_hecho=date.today(),
        hora_hecho="08:30", descripcion="Robo de celular en el paradero",
    )
    datos.update(cambios)
    return Incidente(**datos)


def datos_oficiales(extra=()):
    filas = []
    base = [("A", 10, 100, 200), ("B", 1, 10, 20), ("C", 0, 1, 2), *extra]
    for distrito, homicidio, robo, hurto in base:
        for delito, cantidad in (("HOMICIDIO", homicidio), ("ROBO", robo), ("HURTO", hurto)):
            filas.append({"distrito": distrito, "delito": delito, "periodo": "2025",
                          "cantidad": cantidad, "correccion_manual": 0})
    return pd.DataFrame(filas)


# ---------- Incidente ----------

def test_incidente_valido():
    un_incidente().validar()


@pytest.mark.parametrize("cambios", [
    {"descripcion": "corto"},
    {"descripcion": "x" * 501},
    {"delito": "INVENTADO"},
    {"hora_hecho": "25:99"},
    {"fecha_hecho": date.today() + timedelta(days=1)},
    {"ubicacion": Ubicacion("AREQUIPA", "AREQUIPA", "")},
])
def test_incidente_invalido(cambios):
    with pytest.raises(ValueError):
        un_incidente(**cambios).validar()


# ---------- Normalización ----------

def test_normalizar_quita_tildes_y_signos():
    assert normalizar("Ancón") == "ANCON"
    assert normalizar("LURIGANCHO - CHOSICA") == "LURIGANCHO CHOSICA"
    assert normalizar("  Breña ") == "BRENA"


# ---------- Índice de riesgo y alertas ----------

def test_indice_niveles_y_orden():
    resultado = CalculadoraRiesgo().indice(datos_oficiales(), "2025")
    assert resultado["distrito"].tolist() == ["A", "B", "C"]
    niveles = resultado.set_index("distrito")["nivel"].astype(str).to_dict()
    assert niveles == {"A": "Alto", "B": "Medio", "C": "Bajo"}


def test_indice_incluye_callao_por_defecto_y_permite_excluir():
    datos = datos_oficiales(extra=[("CALLAO", 5, 50, 100)])
    assert "CALLAO" in CalculadoraRiesgo().indice(datos, "2025")["distrito"].tolist()
    sin = CalculadoraRiesgo(excluir={"CALLAO"}).indice(datos, "2025")
    assert "CALLAO" not in sin["distrito"].tolist()


def test_alertas_respetan_umbral_y_minimo():
    filas = []
    for distrito, anual, enero in [("X", 120, 15), ("Y", 120, 10), ("Z", 12, 5)]:
        filas.append({"distrito": distrito, "delito": "ROBO", "periodo": "2025",
                      "cantidad": anual, "correccion_manual": 0})
        filas.append({"distrito": distrito, "delito": "ROBO", "periodo": "2026-01",
                      "cantidad": enero, "correccion_manual": 0})
    alertas = CalculadoraRiesgo().alertas(pd.DataFrame(filas))
    assert alertas["distrito"].tolist() == ["X"]  # Y no sube; Z sube pero tiene menos de 10


# ---------- Repositorio (CRUD sobre una base temporal) ----------

@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    return RepositorioIncidentes()


def test_crud_completo(repo):
    nuevo = un_incidente()
    nuevo_id = repo.agregar(nuevo)
    assert nuevo.id == nuevo_id
    assert len(repo.listar()) == 1
    assert repo.actualizar(nuevo_id, "HURTO", "Descripción actualizada del hecho")
    assert repo.listar().iloc[0]["delito"] == "HURTO"
    assert repo.eliminar(nuevo_id)
    assert repo.listar().empty


def test_repositorio_rechaza_incidente_invalido(repo):
    with pytest.raises(ValueError):
        repo.agregar(un_incidente(descripcion="x"))
    assert repo.listar().empty


# ---------- Lectura de filas del PDF regional ----------

def test_fila_regional_simple():
    assert _fila("AMAZONAS 166 21 52 32 4 27 302") == (
        "AMAZONAS", [166, 21, 52, 32, 4, 27, 302], [])


def test_fila_regional_con_nota_al_pie():
    region, cifras, _ = _fila("LIMA METROPOLITANA 1/ 10,322 1,071 1,376 1,107 344 254 14,474")
    assert region == "LIMA METROPOLITANA"
    assert cifras[0] == 10322 and cifras[-1] == 14474


def test_fila_regional_descarta_lineas_que_no_son_datos():
    assert _fila("II. DENUNCIAS POR HECHOS DELICTIVOS") is None
    assert _fila("2024 2025 2024 2025") is None
