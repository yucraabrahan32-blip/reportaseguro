"""Lógica de negocio: sincronización de datos oficiales, índice de riesgo y alertas."""
import pandas as pd

from backend.conectores import (
    CORRECCIONES, URL_SIDPOL, aplicar_correcciones, descargar_pdf, extraer_distritos,
)
from database import db

# Pesos por gravedad: criterio propio, debe justificarse en el informe.
PESOS = {"HOMICIDIO": 10, "ROBO": 3, "HURTO": 1}
# Filas que son totales y no distritos (evita contar dos veces el Callao).
EXCLUIR = set()
NIVELES = ["Bajo", "Medio", "Alto"]


def sincronizar_sidpol() -> dict:
    archivo = descargar_pdf(URL_SIDPOL)
    df, dudosas = extraer_distritos(archivo, 30, ["HOMICIDIO", "HURTO", "ROBO"])
    df = aplicar_correcciones(df, CORRECCIONES)
    filas = db.guardar_denuncias_oficiales(df, "SIDPOL - Mininter", URL_SIDPOL, archivo.name)
    return {"filas_guardadas": filas, "lineas_dudosas": len(dudosas)}


def indice_riesgo(oficial: pd.DataFrame, periodo: str = "2025") -> pd.DataFrame:
    """Índice de 0 a 100 por distrito, según el puesto relativo de su puntaje ponderado."""
    datos = oficial[(oficial["periodo"] == periodo) & (~oficial["distrito"].isin(EXCLUIR))]
    if datos.empty:
        return pd.DataFrame()
    tabla = datos.pivot_table(
        index="distrito", columns="delito", values="cantidad", aggfunc="sum", fill_value=0
    )
    puntaje = pd.Series(0.0, index=tabla.index)
    for delito, peso in PESOS.items():
        if delito not in tabla.columns:
            tabla[delito] = 0
        puntaje += tabla[delito] * peso
    tabla["puntaje"] = puntaje
    tabla["indice"] = (puntaje.rank(pct=True) * 100).round(1)
    tabla["nivel"] = pd.cut(tabla["indice"], bins=[0, 100 / 3, 200 / 3, 100], labels=NIVELES)
    return tabla.sort_values("puntaje", ascending=False).reset_index()


def alertas_aumento(oficial: pd.DataFrame, umbral: float = 1.2, minimo: int = 10) -> pd.DataFrame:
    """Distritos y delitos donde enero 2026 supera al promedio mensual de 2025."""
    datos = oficial[~oficial["distrito"].isin(EXCLUIR)]
    tabla = datos.pivot_table(
        index=["distrito", "delito"], columns="periodo", values="cantidad", aggfunc="sum"
    )
    if not {"2025", "2026-01"}.issubset(tabla.columns):
        return pd.DataFrame()
    tabla = tabla.dropna(subset=["2025", "2026-01"])
    tabla = tabla[tabla["2025"] > 0]
    tabla["prom_mensual_2025"] = (tabla["2025"] / 12).round(1)
    tabla["razon"] = (tabla["2026-01"] / tabla["prom_mensual_2025"]).round(2)
    alertas = tabla[(tabla["razon"] >= umbral) & (tabla["2026-01"] >= minimo)]
    return (
        alertas[["2026-01", "prom_mensual_2025", "razon"]]
        .rename(columns={"2026-01": "ene_2026"})
        .sort_values("razon", ascending=False)
        .reset_index()
    )


if __name__ == "__main__":
    print(sincronizar_sidpol())
    print(indice_riesgo(db.denuncias_oficiales_df()).head())