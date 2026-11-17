import requests

from backend.fuentes import novedades

HTML = """
<a href="/institucion/mininter/informes-publicaciones/8482979-reporte-de-denuncias-registradas-en-el-sidpol-a-julio-del-2026">Julio</a>
<a href="/institucion/mininter/informes-publicaciones/8338000-reporte-de-denuncias-registradas-en-el-sidpol-a-mayo-del-2026">Mayo</a>
<a href="/institucion/mininter/informes-publicaciones/8510793-reporte-de-la-ejecucion-presupuestal-pp0030-a-julio-de-2026">Otro reporte</a>
<a href="/institucion/mininter/informes-publicaciones/8482979-reporte-de-denuncias-registradas-en-el-sidpol-a-julio-del-2026">Julio repetido</a>
<a href="/institucion/mininter/informes-publicaciones/7000000-reporte-de-denuncias-registradas-en-el-sidpol-a-diciembre-2025">Diciembre</a>
"""


class Respuesta:
    def __init__(self, texto):
        self.text = texto

    def raise_for_status(self):
        pass


def test_extrae_solo_reportes_sidpol_ordenados_y_sin_repetir():
    reportes = novedades.extraer_reportes(HTML)
    assert [(r.anio, r.mes) for r in reportes] == [(2026, 7), (2026, 5), (2025, 12)]
    assert reportes[0].url.startswith("https://www.gob.pe/institucion/mininter/")
    assert reportes[0].etiqueta == "julio de 2026"


def test_html_sin_reportes():
    assert novedades.extraer_reportes("<p>nada</p>") == []


def test_periodo_en_uso_lee_el_nombre_del_archivo():
    archivo = "7729200-reporte-de-denuncias-registradas-en-el-sidpol-a-enero-del-2026.pdf"
    assert novedades.periodo_en_uso(archivo) == (2026, 1)
    assert novedades.periodo_en_uso("otro.pdf") is None


def test_ultimo_reporte_elige_el_mas_reciente(monkeypatch):
    monkeypatch.setattr(novedades.requests, "get", lambda url, **kw: Respuesta(HTML))
    assert (novedades.ultimo_reporte(hojas=2).anio, novedades.ultimo_reporte(hojas=2).mes) == (2026, 7)


def test_sin_internet_devuelve_none(monkeypatch):
    def falla(url, **kw):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr(novedades.requests, "get", falla)
    assert novedades.ultimo_reporte() is None


def test_url_pdf_elige_el_pdf_del_reporte_y_no_el_organigrama(monkeypatch):
    ficha = (
        '<a href="/rails/active_storage/blobs/x/ORGANIGRAMA.pdf">Organigrama</a>'
        '<a href="https://cdn.www.gob.pe/uploads/document/file/1/8482979-reporte-de-denuncias-'
        'registradas-en-el-sistema-de-denuncias-policiales-sidpol-a-julio-del-2026.pdf?v=1">PDF</a>'
    )
    monkeypatch.setattr(novedades.requests, "get", lambda url, **kw: Respuesta(ficha))
    reporte = novedades.ReporteSidpol(2026, 7, "https://www.gob.pe/x")
    assert novedades.url_pdf(reporte).endswith("a-julio-del-2026.pdf?v=1")


def test_url_pdf_sin_pdf_del_sidpol_falla(monkeypatch):
    import pytest

    monkeypatch.setattr(
        novedades.requests, "get",
        lambda url, **kw: Respuesta('<a href="/a/organigrama.pdf">x</a>'),
    )
    with pytest.raises(ValueError):
        novedades.url_pdf(novedades.ReporteSidpol(2026, 7, "https://www.gob.pe/x"))
