"""Servicios: sincronización de datos oficiales, índice de riesgo y alertas."""
import pandas as pd

from backend.conectores import (
    CORRECCIONES, URL_SIDPOL, aplicar_correcciones, descargar_pdf, extraer_distritos,
)
from backend.models import CalculadoraRiesgo
from database import db

_calculadora = CalculadoraRiesgo()


def sincronizar_sidpol() -> dict:
    archivo = descargar_pdf(URL_SIDPOL)
    df, dudosas = extraer_distritos(archivo, 30, ["HOMICIDIO", "HURTO", "ROBO"])
    df = aplicar_correcciones(df, CORRECCIONES)
    filas = db.guardar_denuncias_oficiales(df, "SIDPOL - Mininter", URL_SIDPOL, archivo.name)
    return {"filas_guardadas": filas, "lineas_dudosas": len(dudosas)}


def indice_riesgo(oficial: pd.DataFrame, periodo: str = "2025") -> pd.DataFrame:
    return _calculadora.indice(oficial, periodo)


def alertas_aumento(oficial: pd.DataFrame, umbral: float = 1.2, minimo: int = 10) -> pd.DataFrame:
    return _calculadora.alertas(oficial, umbral, minimo)


if __name__ == "__main__":
    print(sincronizar_sidpol())
    print(indice_riesgo(db.denuncias_oficiales_df()).head())
