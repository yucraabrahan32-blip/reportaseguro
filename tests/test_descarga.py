from backend import conectores


class _Respuesta:
    content = b"%PDF"

    def raise_for_status(self):
        pass


def test_el_nombre_del_archivo_ignora_los_parametros_de_la_url(tmp_path, monkeypatch):
    monkeypatch.setattr(conectores, "CARPETA", tmp_path)
    monkeypatch.setattr(conectores.requests, "get", lambda url, **kw: _Respuesta())
    ruta = conectores.descargar_pdf("https://cdn.ejemplo.org/a/reporte.pdf?v=123")
    assert ruta.name == "reporte.pdf"
    assert ruta.read_bytes() == b"%PDF"
