"""Clase base de los conectores de datos (patrón Template Method)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from backend.conectores import descargar_pdf


@dataclass
class ResultadoSincronizacion:
    fuente: str
    filas_guardadas: int
    advertencias: list[str] = field(default_factory=list)


class ConectorDatos(ABC):
    """Toda fuente de datos sigue el mismo flujo: descargar, extraer y guardar."""

    nombre: str  # texto que ve el usuario
    fuente: str  # nombre registrado en la tabla 'fuentes'
    url: str

    def sincronizar(self) -> ResultadoSincronizacion:
        archivo = self.descargar()
        datos, advertencias = self.extraer(archivo)
        filas = self.guardar(datos, archivo)
        return ResultadoSincronizacion(self.nombre, filas, advertencias)

    def descargar(self) -> Path:
        return descargar_pdf(self.url)

    @abstractmethod
    def extraer(self, archivo: Path) -> tuple[pd.DataFrame, list[str]]:
        """Devuelve los datos limpios y una lista de advertencias."""

    @abstractmethod
    def guardar(self, datos: pd.DataFrame, archivo: Path) -> int:
        """Guarda los datos en la base y devuelve cuántas filas se guardaron."""
