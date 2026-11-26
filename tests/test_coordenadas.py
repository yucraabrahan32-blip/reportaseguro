"""Pruebas de la ubicacion por coordenadas marcadas en el mapa.

Cuando el ciudadano marca el punto en el mapa, la latitud/longitud exactas se
guardan en el incidente. El mapa de riesgo usa esa coordenada real y, solo si
no existe, cae en el centroide del distrito (catalogo ubigeo).
"""
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from database.modelos import Base, IncidenteCiudadano, Ubigeo


def _bd_en_memoria():
    """Base SQLite temporal (solo vive durante la prueba)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_incidente_guarda_su_coordenada_real():
    # El incidente almacena la latitud/longitud exactas del punto marcado.
    engine = _bd_en_memoria()
    with Session(engine) as s:
        s.add(IncidenteCiudadano(
            distrito="MIRAFLORES", delito="ROBO",
            fecha_hecho="2025-01-01", hora_hecho="10:00",
            descripcion="Robo cerca del parque", creado_en="2025-01-01T10:00:00",
            latitud=-12.1234, longitud=-77.0456,
        ))
        s.commit()
        guardado = s.query(IncidenteCiudadano).first()
        assert guardado.latitud == -12.1234
        assert guardado.longitud == -77.0456


def test_el_mapa_prefiere_la_coordenada_real_sobre_el_centroide():
    # Reporte con coordenada propia -> usa esa. Sin coordenada -> centroide del distrito.
    engine = _bd_en_memoria()
    with Session(engine) as s:
        s.add(Ubigeo(departamento="LIMA", provincia="LIMA", distrito="MIRAFLORES",
                     nombre_norm="MIRAFLORES", latitud=-12.11, longitud=-77.02))
        s.add(IncidenteCiudadano(departamento="LIMA", provincia="LIMA", distrito="MIRAFLORES",
              delito="ROBO", fecha_hecho="2025-01-01", hora_hecho="10:00",
              descripcion="Con coordenada propia", creado_en="2025-01-01T10:00:00",
              latitud=-12.1234, longitud=-77.0456))
        s.add(IncidenteCiudadano(departamento="LIMA", provincia="LIMA", distrito="MIRAFLORES",
              delito="HURTO", fecha_hecho="2025-01-02", hora_hecho="11:00",
              descripcion="Sin coordenada propia", creado_en="2025-01-02T11:00:00"))
        s.commit()

        i, u = IncidenteCiudadano, Ubigeo
        lat = func.coalesce(i.latitud, u.latitud)
        lon = func.coalesce(i.longitud, u.longitud)
        consulta = (
            select(i.delito, lat, lon)
            .join(u, (u.departamento == i.departamento) & (u.provincia == i.provincia)
                  & (u.distrito == i.distrito), isouter=True)
        )
        resultado = {f[0]: (round(f[1], 4), round(f[2], 4)) for f in s.execute(consulta)}

    assert resultado["ROBO"] == (-12.1234, -77.0456)   # usa su coordenada real
    assert resultado["HURTO"] == (-12.11, -77.02)       # cae al centroide del distrito
