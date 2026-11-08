"""Incidente: un reporte ciudadano que se valida a sí mismo."""
from dataclasses import dataclass
from datetime import date, datetime

from backend.models.ubicacion import Ubicacion
from backend.models.validaciones import validar_delito, validar_descripcion


@dataclass
class Incidente:
    ubicacion: Ubicacion
    delito: str
    fecha_hecho: date
    hora_hecho: str
    descripcion: str
    id: int | None = None

    def validar(self) -> None:
        self.ubicacion.validar()
        validar_delito(self.delito)
        if self.fecha_hecho > date.today():
            raise ValueError("La fecha del hecho no puede ser futura.")
        try:
            datetime.strptime(self.hora_hecho, "%H:%M")
        except ValueError:
            raise ValueError("La hora debe tener el formato HH:MM.") from None
        validar_descripcion(self.descripcion)
