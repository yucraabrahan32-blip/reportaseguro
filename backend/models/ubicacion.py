"""Ubicación geográfica de un incidente."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ubicacion:
    departamento: str
    provincia: str
    distrito: str

    def validar(self) -> None:
        if not (self.departamento and self.provincia and self.distrito):
            raise ValueError("Selecciona departamento, provincia y distrito.")
