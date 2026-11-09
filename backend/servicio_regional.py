"""Análisis de denuncias por región."""
import pandas as pd

from backend.ubigeo import normalizar


def totales_por_region(df: pd.DataFrame, periodo: str) -> pd.DataFrame:
    datos = df[df["periodo"] == periodo]
    totales = datos.groupby("region", as_index=False)["cantidad"].sum()
    return totales.rename(columns={"cantidad": "total"}).sort_values(
        "total", ascending=False
    ).reset_index(drop=True)


def coordenadas_regiones(catalogo: pd.DataFrame, regiones: list) -> pd.DataFrame:
    """Promedio simple de las coordenadas de los distritos de cada región (es aproximado)."""
    columnas = ["region", "latitud", "longitud"]
    if catalogo.empty:
        return pd.DataFrame(columns=columnas)
    cat = catalogo.dropna(subset=["latitud", "longitud"])
    dep = cat["departamento"].map(normalizar)
    prov = cat["provincia"].map(normalizar)
    especiales = {
        "LIMA METROPOLITANA": cat[prov == "LIMA"],
        "REGIÓN LIMA": cat[(dep == "LIMA") & (prov != "LIMA") & (prov != "CALLAO")],
        "PROV. CONST. DEL CALLAO": cat[prov == "CALLAO"],
    }
    filas = []
    for region in regiones:
        sub = especiales[region] if region in especiales else cat[dep == normalizar(region)]
        if not sub.empty:
            filas.append({
                "region": region,
                "latitud": sub["latitud"].mean(),
                "longitud": sub["longitud"].mean(),
            })
    return pd.DataFrame(filas, columns=columnas)
