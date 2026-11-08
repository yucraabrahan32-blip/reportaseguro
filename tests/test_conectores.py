from pathlib import Path

import pandas as pd
import pytest

import backend.fuentes as fuentes
from backend.fuentes import ConectorDatos, ResultadoSincronizacion


class ConectorFalso(ConectorDatos):
    nombre = "Falso"
    fuente = "Falso"
    url = "http://ejemplo.invalid"

    def __init__(self):
        self.llamadas = []

    def descargar(self):
        self.llamadas.append("descargar")
        return Path("falso.pdf")

    def extraer(self, archivo):
        self.llamadas.append("extraer")
        return pd.DataFrame({"a": [1, 2]}), ["una advertencia"]

    def guardar(self, datos, archivo):
        self.llamadas.append("guardar")
        return len(datos)


class ConectorRoto(ConectorFalso):
    nombre = "Roto"

    def descargar(self):
        raise RuntimeError("sin internet")


def test_la_clase_base_no_se_puede_instanciar():
    with pytest.raises(TypeError):
        ConectorDatos()


def test_el_flujo_es_descargar_extraer_guardar():
    conector = ConectorFalso()
    resultado = conector.sincronizar()
    assert conector.llamadas == ["descargar", "extraer", "guardar"]
    assert resultado == ResultadoSincronizacion("Falso", 2, ["una advertencia"])


def test_un_conector_que_falla_no_detiene_a_los_demas(monkeypatch):
    monkeypatch.setattr(fuentes, "CONECTORES", [ConectorRoto, ConectorFalso])
    resultados, errores = fuentes.sincronizar_todos()
    assert [r.fuente for r in resultados] == ["Falso"]
    assert errores == [("Roto", "sin internet")]


def test_los_conectores_reales_son_subclases_de_la_base():
    assert all(issubclass(clase, ConectorDatos) for clase in fuentes.CONECTORES)
