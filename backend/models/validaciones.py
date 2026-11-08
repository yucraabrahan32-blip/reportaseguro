"""Reglas de validación compartidas por los modelos."""

DELITOS = ("ROBO", "HURTO", "HOMICIDIO", "OTRO")
DESCRIPCION_MIN = 10
DESCRIPCION_MAX = 500


def validar_delito(delito: str) -> None:
    if delito not in DELITOS:
        raise ValueError(f"Tipo de incidente no válido: {delito!r}.")


def validar_descripcion(descripcion: str) -> None:
    largo = len(descripcion.strip())
    if largo < DESCRIPCION_MIN:
        raise ValueError(f"La descripción debe tener al menos {DESCRIPCION_MIN} caracteres.")
    if largo > DESCRIPCION_MAX:
        raise ValueError(f"La descripción no puede superar {DESCRIPCION_MAX} caracteres.")
