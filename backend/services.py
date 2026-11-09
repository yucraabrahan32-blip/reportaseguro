"""Servicios de análisis sobre los datos oficiales."""
import pandas as pd

from backend.models import CalculadoraRiesgo

_calculadora = CalculadoraRiesgo()


def indice_riesgo(oficial: pd.DataFrame, periodo: str = "2025") -> pd.DataFrame:
    return _calculadora.indice(oficial, periodo)


def alertas_aumento(oficial: pd.DataFrame, umbral: float = 1.2, minimo: int = 10) -> pd.DataFrame:
    return _calculadora.alertas(oficial, umbral, minimo)
