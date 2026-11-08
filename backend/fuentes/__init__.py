"""Conectores de datos: cada fuente externa es una subclase de ConectorDatos."""
from backend.fuentes.base import ConectorDatos, ResultadoSincronizacion
from backend.fuentes.sidpol_distrital import ConectorSIDPOLDistrital
from backend.fuentes.sidpol_regional import ConectorSIDPOLRegional

CONECTORES = [ConectorSIDPOLDistrital, ConectorSIDPOLRegional]


def sincronizar_todos():
    """Ejecuta todos los conectores; si uno falla, los demás continúan."""
    resultados, errores = [], []
    for clase in CONECTORES:
        conector = clase()
        try:
            resultados.append(conector.sincronizar())
        except Exception as error:
            errores.append((conector.nombre, str(error)))
    return resultados, errores
