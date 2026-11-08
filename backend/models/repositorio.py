"""Patrón Repository: el resto del sistema no conoce SQL ni SQLite."""
import pandas as pd

from backend.models.incidente import Incidente
from backend.models.validaciones import validar_delito, validar_descripcion
from database import db


class RepositorioIncidentes:
    def agregar(self, incidente: Incidente) -> int:
        incidente.validar()
        u = incidente.ubicacion
        nuevo_id = db.guardar_incidente(
            u.departamento, u.provincia, u.distrito, incidente.delito,
            incidente.fecha_hecho.isoformat(), incidente.hora_hecho, incidente.descripcion,
        )
        incidente.id = nuevo_id
        return nuevo_id

    def listar(self, limite: int = 10) -> pd.DataFrame:
        return db.listar_incidentes(limite)

    def actualizar(self, id_incidente: int, delito: str, descripcion: str) -> bool:
        validar_delito(delito)
        validar_descripcion(descripcion)
        return db.actualizar_incidente(id_incidente, delito, descripcion)

    def eliminar(self, id_incidente: int) -> bool:
        return db.eliminar_incidente(id_incidente)
