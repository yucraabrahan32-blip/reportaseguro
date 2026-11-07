"""Sincronización y análisis de denuncias por región."""
import pandas as pd

from backend.conectores import URL_SIDPOL, descargar_pdf
from backend.regional import extraer_regiones
from backend.ubigeo import normalizar
from database import db


def sincronizar_regional() -> dict:
    archivo = descargar_pdf(URL_SIDPOL)
    df, rechazadas = extraer_regiones(archivo)
    if df.empty:
        raise ValueError("No se extrajo ninguna región; el formato del PDF pudo haber cambiado.")
    filas = db.guardar_denuncias_regionales(df, "SIDPOL - Mininter", URL_SIDPOL, archivo.name)
    return {"filas_guardadas": filas, "regiones": df["region"].nunique(), "rechazadas": rechazadas}


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


if __name__ == "__main__":
    print(sincronizar_regional())
    totales = totales_por_region(db.denuncias_regionales_df(), "2026-01")
    print(totales.head(5).to_string(index=False))
    control = totales[totales["region"].isin(["LIMA METROPOLITANA", "AREQUIPA"])]
    print("\nControl (esperado: Lima Metropolitana 14474, Arequipa 1821):")
    print(control.to_string(index=False))