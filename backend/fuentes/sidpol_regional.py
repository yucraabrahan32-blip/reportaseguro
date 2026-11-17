"""SIDPOL (Mininter): denuncias por región de todo el país, del reporte más reciente."""
from pathlib import Path

import pandas as pd

from backend.conectores import URL_SIDPOL, descargar_pdf
from backend.fuentes.base import ConectorDatos
from backend.fuentes.novedades import ultimo_reporte, url_pdf
from backend.regional import REGIONES_ESPERADAS, extraer_regiones
from database import db


class ConectorSIDPOLRegional(ConectorDatos):
    nombre = "SIDPOL - regiones del Perú"
    fuente = "SIDPOL - Mininter"
    url = URL_SIDPOL  # se reemplaza por la dirección real del reporte descargado

    def descargar(self) -> Path:
        reporte = ultimo_reporte()
        if reporte is None:
            raise RuntimeError("No se pudo consultar el listado del Observatorio (¿sin internet?).")
        self.url = url_pdf(reporte)
        return descargar_pdf(self.url)

    def extraer(self, archivo: Path) -> tuple[pd.DataFrame, list[str]]:
        df, rechazadas = extraer_regiones(archivo)
        validadas = df["region"].nunique() if not df.empty else 0
        if validadas < REGIONES_ESPERADAS:
            detalle = "; ".join(f"{r}: {m}" for r, m in rechazadas[:5])
            raise ValueError(
                f"Solo se validaron {validadas} de {REGIONES_ESPERADAS} regiones; "
                f"no se reemplazan los datos actuales. {detalle}"
            )
        return df, [f"{region}: {motivo}" for region, motivo in rechazadas]

    def guardar(self, datos: pd.DataFrame, archivo: Path) -> int:
        return db.guardar_denuncias_regionales(datos, self.fuente, self.url, archivo.name)
