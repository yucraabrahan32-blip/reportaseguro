"""SIDPOL (Mininter): denuncias por distrito de Lima Metropolitana y Callao."""
from pathlib import Path

import pandas as pd

from backend.conectores import (
    CORRECCIONES, URL_SIDPOL, aplicar_correcciones, extraer_distritos,
)
from backend.fuentes.base import ConectorDatos
from backend.paginas import localizar_pagina
from database import db


class ConectorSIDPOLDistrital(ConectorDatos):
    nombre = "SIDPOL - distritos de Lima y Callao"
    fuente = "SIDPOL - Mininter"
    url = URL_SIDPOL
    MARCAS = ["V.2.1", "HOMICIDIO HURTO ROBO"]  # identifican la página por su contenido
    DELITOS = ["HOMICIDIO", "HURTO", "ROBO"]

    def extraer(self, archivo: Path) -> tuple[pd.DataFrame, list[str]]:
        df, dudosas = extraer_distritos(
            archivo, localizar_pagina(archivo, self.MARCAS), self.DELITOS
        )
        df = aplicar_correcciones(df, CORRECCIONES)
        advertencias = [f"[{delito}] {texto} -> {motivo}" for delito, texto, motivo in dudosas]
        return df, advertencias

    def guardar(self, datos: pd.DataFrame, archivo: Path) -> int:
        return db.guardar_denuncias_oficiales(datos, self.fuente, self.url, archivo.name)
