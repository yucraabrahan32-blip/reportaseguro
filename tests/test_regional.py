from pathlib import Path

import pandas as pd
import pytest

from backend.fuentes import novedades, sidpol_regional
from backend.regional import leer_corte
from database import db


@pytest.mark.parametrize("texto, esperado", [
    ("II.3 ... a nivel regional: (ene.-jul.) 2026", "2026-07"),
    ("II.3 ... a nivel regional: (ene.) 2026", "2026-01"),
    ("(ene.-dic.) 2025", "2025-12"),
    ("(ene.-set.) 2025", "2025-09"),
])
def test_leer_corte(texto, esperado):
    assert leer_corte(texto) == esperado


def test_leer_corte_sin_periodo_falla():
    with pytest.raises(ValueError):
        leer_corte("una tabla sin periodo")


def test_el_conector_regional_descarga_el_reporte_mas_reciente(monkeypatch):
    monkeypatch.setattr(
        sidpol_regional, "ultimo_reporte", lambda: novedades.ReporteSidpol(2026, 7, "https://x/ficha")
    )
    monkeypatch.setattr(sidpol_regional, "url_pdf", lambda reporte: "https://cdn/x-julio.pdf")
    monkeypatch.setattr(sidpol_regional, "descargar_pdf", lambda url: Path("x-julio.pdf"))
    conector = sidpol_regional.ConectorSIDPOLRegional()
    assert conector.descargar() == Path("x-julio.pdf")
    assert conector.url == "https://cdn/x-julio.pdf"


def test_el_conector_regional_sin_listado_falla_con_mensaje(monkeypatch):
    monkeypatch.setattr(sidpol_regional, "ultimo_reporte", lambda: None)
    with pytest.raises(RuntimeError):
        sidpol_regional.ConectorSIDPOLRegional().descargar()


def test_no_se_reemplazan_datos_si_se_validan_pocas_regiones(monkeypatch):
    df = pd.DataFrame({"region": ["A", "B"], "categoria": ["x", "x"], "periodo": ["2026", "2026"],
                       "cantidad": [1, 2], "corte": ["2026-07", "2026-07"]})
    monkeypatch.setattr(sidpol_regional, "extraer_regiones", lambda ruta: (df, [("C", "no suma")]))
    with pytest.raises(ValueError):
        sidpol_regional.ConectorSIDPOLRegional().extraer(Path("x.pdf"))


def _tabla_vieja(tmp_path, monkeypatch):
    """Crea la tabla regional como era antes de registrar el mes de corte."""
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    db.inicializar()
    con = db.conectar()
    with con:
        con.execute(
            """CREATE TABLE denuncias_regionales (
                id INTEGER PRIMARY KEY,
                fuente_id INTEGER NOT NULL REFERENCES fuentes(id),
                sincronizacion_id INTEGER NOT NULL REFERENCES sincronizaciones(id),
                region TEXT NOT NULL, categoria TEXT NOT NULL, periodo TEXT NOT NULL,
                cantidad INTEGER NOT NULL CHECK (cantidad >= 0),
                UNIQUE (fuente_id, region, categoria, periodo))"""
        )
        con.execute(
            "INSERT INTO sincronizaciones (fuente_id, url, archivo, fecha_descarga, filas_cargadas) "
            "VALUES (1, 'u', 'a.pdf', '2026-11-08T00:00:00', 2)"
        )
        con.executemany(
            "INSERT INTO denuncias_regionales (fuente_id, sincronizacion_id, region, categoria, "
            "periodo, cantidad) VALUES (1, 1, 'AREQUIPA', 'X', ?, ?)",
            [("2025-01", 1614), ("2026-01", 1090)],
        )
    con.close()


def test_la_tabla_vieja_se_migra_con_su_corte(tmp_path, monkeypatch):
    _tabla_vieja(tmp_path, monkeypatch)
    df = db.denuncias_regionales_df()
    assert sorted(df["periodo"]) == ["2025", "2026"]
    assert set(df["corte"]) == {"2026-01"}


def test_una_carga_nueva_reemplaza_las_cifras_y_cambia_el_corte(tmp_path, monkeypatch):
    _tabla_vieja(tmp_path, monkeypatch)
    nuevo = pd.DataFrame({
        "region": ["AREQUIPA", "AREQUIPA"], "categoria": ["X", "X"],
        "periodo": ["2025", "2026"], "cantidad": [10000, 10356], "corte": ["2026-07", "2026-07"],
    })
    db.guardar_denuncias_regionales(nuevo, "SIDPOL - Mininter", "https://cdn/julio.pdf", "julio.pdf")
    df = db.denuncias_regionales_df()
    assert len(df) == 2 and set(df["corte"]) == {"2026-07"}
    assert db.cortes_cargados()["regional"] == "2026-07"
