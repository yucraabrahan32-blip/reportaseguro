import pytest

from backend.fuentes import carga_asistida
from backend.fuentes.base import ConectorDatos, ResultadoSincronizacion
from backend.fuentes.carga_asistida import CargaAsistidaCSV
from database import db

CABECERA = "ambito,lugar,indicador,periodo,valor,unidad\n"
CSV = CABECERA + "region,AREQUIPA,Victimización,2025,25.5,%\nregion,CUSCO,Victimización,2025,20.1,%\n"


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    monkeypatch.setattr(carga_asistida, "CARPETA", tmp_path / "raw")


def cargador(contenido, **cambios):
    datos = dict(fuente="Fuente de prueba", entidad="Entidad X", tipo="ong",
                 url_fuente="https://ejemplo.org/datos")
    datos.update(cambios)
    if isinstance(contenido, str):
        contenido = contenido.encode("utf-8")
    return CargaAsistidaCSV(contenido, **datos)


def test_es_un_conector():
    assert issubclass(CargaAsistidaCSV, ConectorDatos)


def test_carga_valida(base):
    resultado = cargador(CSV).sincronizar()
    assert isinstance(resultado, ResultadoSincronizacion)
    assert resultado.filas_guardadas == 2
    df = db.indicadores_df()
    assert len(df) == 2
    assert set(df["tipo"]) == {"ong"}
    assert df.loc[df["lugar"] == "AREQUIPA", "valor"].iloc[0] == 25.5


def test_csv_con_punto_y_coma(base):
    texto = "ambito;lugar;indicador;periodo;valor;unidad\nregion;AREQUIPA;X;2025;10.5;%\n"
    assert cargador(texto).sincronizar().filas_guardadas == 1


def test_filas_invalidas_se_reportan_y_no_se_guardan(base):
    texto = (
        CABECERA
        + "region,AREQUIPA,X,2025,10,%\n"
        + "planeta,MARTE,X,2025,10,%\n"
        + 'region,CUSCO,X,2025,"1,5",%\n'
        + "region,PUNO,X,2025,abc,%\n"
        + "region,,X,2025,5,%\n"
    )
    resultado = cargador(texto).sincronizar()
    assert resultado.filas_guardadas == 1
    assert len(resultado.advertencias) == 4


def test_faltan_columnas(base):
    with pytest.raises(ValueError):
        cargador("lugar,valor\nA,1\n").sincronizar()


def test_ninguna_fila_valida(base):
    with pytest.raises(ValueError):
        cargador(CABECERA + "xxx,A,B,2025,1,%\n").sincronizar()


def test_tipo_invalido():
    with pytest.raises(ValueError):
        cargador(CSV, tipo="ciudadana")


def test_url_invalida():
    with pytest.raises(ValueError):
        cargador(CSV, url_fuente="ftp://ejemplo.org")


def test_archivo_vacio():
    with pytest.raises(ValueError):
        cargador(b"")


def test_recargar_actualiza_y_no_duplica(base):
    cargador(CSV).sincronizar()
    nuevo = CABECERA + "region,AREQUIPA,Victimización,2025,30.0,%\nregion,CUSCO,Victimización,2025,20.1,%\n"
    cargador(nuevo).sincronizar()
    df = db.indicadores_df()
    assert len(df) == 2
    assert df.loc[df["lugar"] == "AREQUIPA", "valor"].iloc[0] == 30.0


def test_misma_fuente_con_otro_tipo_se_rechaza(base):
    cargador(CSV).sincronizar()
    with pytest.raises(ValueError):
        cargador(CSV, tipo="estatal").sincronizar()


def test_csv_en_latin1(base):
    texto = CABECERA + "region,JUNÍN,X,2025,5,%\n"
    cargador(texto.encode("latin-1")).sincronizar()
    assert db.indicadores_df()["lugar"].iloc[0] == "JUNÍN"
