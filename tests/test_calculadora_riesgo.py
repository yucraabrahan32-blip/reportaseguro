"""Pruebas unitarias de la CalculadoraRiesgo (backend/models/calculadora.py).

El puntaje de riesgo de un distrito se calcula ponderando los delitos por gravedad:
por defecto HOMICIDIO=10, ROBO=3, HURTO=1. Verificamos que el calculo y el orden
sean correctos usando datos de ejemplo.
"""
import pandas as pd

from backend.models.calculadora import CalculadoraRiesgo


def _datos_ejemplo():
    """Dos distritos con denuncias del periodo 2025."""
    return pd.DataFrame([
        {"distrito": "ALTO", "delito": "HOMICIDIO", "periodo": "2025", "cantidad": 5},
        {"distrito": "ALTO", "delito": "ROBO", "periodo": "2025", "cantidad": 10},
        {"distrito": "BAJO", "delito": "HURTO", "periodo": "2025", "cantidad": 2},
    ])


def test_puntaje_pondera_por_gravedad():
    # ALTO: 5*10 + 10*3 = 80 ; BAJO: 2*1 = 2
    resultado = CalculadoraRiesgo().indice(_datos_ejemplo(), "2025")
    fila_alto = resultado[resultado["distrito"] == "ALTO"].iloc[0]
    fila_bajo = resultado[resultado["distrito"] == "BAJO"].iloc[0]
    assert fila_alto["puntaje"] == 80
    assert fila_bajo["puntaje"] == 2


def test_el_distrito_mas_peligroso_queda_primero():
    # El resultado se ordena de mayor a menor puntaje.
    resultado = CalculadoraRiesgo().indice(_datos_ejemplo(), "2025")
    assert resultado.iloc[0]["distrito"] == "ALTO"


def test_periodo_sin_datos_devuelve_tabla_vacia():
    # Si no hay denuncias de ese periodo, el resultado es un DataFrame vacio.
    resultado = CalculadoraRiesgo().indice(_datos_ejemplo(), "2099")
    assert resultado.empty
