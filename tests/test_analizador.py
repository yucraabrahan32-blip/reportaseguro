import pandas as pd

from backend.models import AnalizadorIncidentes

COLUMNAS = ["id", "departamento", "provincia", "distrito", "delito", "fecha_hecho", "hora_hecho"]


def datos():
    return pd.DataFrame({
        "id": [1, 2, 3, 4],
        "departamento": ["LIMA", "LIMA", "AREQUIPA", "AREQUIPA"],
        "provincia": ["LIMA", "LIMA", "AREQUIPA", "AREQUIPA"],
        "distrito": ["ATE", "ATE", "CAYMA", "CAYMA"],
        "delito": ["ROBO", "ROBO", "HURTO", "ROBO"],
        "fecha_hecho": ["2026-11-01"] * 4,
        "hora_hecho": ["08:30", "19:00", "02:15", "23:59"],
    })


def test_por_tipo_ordena_de_mayor_a_menor():
    resultado = AnalizadorIncidentes(datos()).por_tipo()
    assert resultado.iloc[0]["delito"] == "ROBO"
    assert resultado.iloc[0]["reportes"] == 3


def test_por_hora_cubre_las_24_horas():
    resultado = AnalizadorIncidentes(datos()).por_hora()
    assert len(resultado) == 24
    assert resultado.loc[resultado["hora"] == 8, "reportes"].iloc[0] == 1
    assert resultado.loc[resultado["hora"] == 0, "reportes"].iloc[0] == 0


def test_por_franja_agrupa_las_horas():
    resultado = AnalizadorIncidentes(datos()).por_franja().set_index("franja")["reportes"]
    assert resultado["Madrugada (0-5 h)"] == 1
    assert resultado["Mañana (6-11 h)"] == 1
    assert resultado["Tarde (12-17 h)"] == 0
    assert resultado["Noche (18-23 h)"] == 2


def test_por_distrito_suma_todos_los_reportes():
    resultado = AnalizadorIncidentes(datos()).por_distrito()
    assert len(resultado) == 2
    assert resultado["reportes"].sum() == 4


def test_filtrar_por_departamento_y_tipo():
    analisis = AnalizadorIncidentes(datos())
    assert len(analisis.filtrar(departamento="AREQUIPA").df) == 2
    assert len(analisis.filtrar(departamento="AREQUIPA", delito="HURTO").df) == 1


def test_sin_reportes_no_falla():
    vacio = AnalizadorIncidentes(pd.DataFrame(columns=COLUMNAS))
    assert vacio.por_hora()["reportes"].sum() == 0
    assert vacio.por_tipo().empty
