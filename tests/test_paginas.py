import pytest

from backend import paginas


class _Pagina:
    def __init__(self, texto):
        self.texto = texto

    def extract_text(self):
        return self.texto


class _PDF:
    def __init__(self, textos):
        self.pages = [_Pagina(t) for t in textos]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _falso(monkeypatch, textos):
    monkeypatch.setattr(paginas.pdfplumber, "open", lambda ruta: _PDF(textos))


def test_localiza_la_pagina_con_todas_las_marcas(monkeypatch):
    _falso(monkeypatch, ["II.3 Indice", "portada", "II.3 Denuncias AMAZONAS 166"])
    assert paginas.localizar_pagina("x.pdf", ["II.3", "AMAZONAS"]) == 3


def test_falla_si_no_encuentra_la_pagina(monkeypatch):
    _falso(monkeypatch, ["una", "dos"])
    with pytest.raises(ValueError):
        paginas.localizar_pagina("x.pdf", ["II.3"])
