"""Modelos de dominio de ReportaSeguro. Cada clase vive en su propio archivo."""
from backend.models.calculadora import CalculadoraRiesgo
from backend.models.incidente import Incidente
from backend.models.repositorio import RepositorioIncidentes
from backend.models.ubicacion import Ubicacion
from backend.models.validaciones import DELITOS, validar_delito, validar_descripcion
