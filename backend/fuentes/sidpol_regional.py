"""SIDPOL (Mininter): denuncias por región de todo el país."""
from pathlib import Path

import pandas as pd

from backend.conectores import URL_SIDPOL
from backend.fuentes.base import ConectorDatos
from backend.regional import extraer_regiones
from database import db


class ConectorSIDPOLRegional(ConectorDatos):
    nombre = "SIDPOL - regiones del Perú"
    fuente = "SIDPOL - Mininter"
    url = URL_SIDPOL

    def extraer(self, archivo: Path) -> tuple[pd.DataFrame, list[str]]:
        df, rechazadas = extraer_regiones(archivo)
        if df.empty:
            raise ValueError("No se extrajo ninguna región; el formato del PDF pudo haber cambiado.")
        advertencias = [f"{region}: {motivo}" for region, motivo in rechazadas]
        return df, advertencias

    def guardar(self, datos: pd.DataFrame, archivo: Path) -> int:
        return db.guardar_denuncias_regionales(datos, self.fuente, self.url, archivo.name)
