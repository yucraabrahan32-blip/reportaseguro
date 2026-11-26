"""Prueba de INTEGRACION: modelos ORM + base de datos SQLite.

A diferencia de las pruebas unitarias (que prueban una funcion aislada), esta
prueba comprueba que varias piezas funcionen JUNTAS: los modelos de SQLAlchemy,
la creacion de tablas y el guardar/leer en una base de datos real.

Para no tocar la base de datos del proyecto, se usa una base SQLite EN MEMORIA
(sqlite:///:memory:), que existe solo mientras dura la prueba.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.modelos import Base, IncidenteCiudadano


def test_guardar_y_leer_un_incidente_en_la_base():
    # 1. Crear una base de datos temporal en memoria y sus tablas.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # 2. Guardar un incidente.
    with Session(engine) as sesion:
        sesion.add(IncidenteCiudadano(
            distrito="MIRAFLORES",
            delito="ROBO",
            fecha_hecho="2025-01-01",
            hora_hecho="14:30",
            descripcion="Robo de celular cerca del parque",
            creado_en="2025-01-01T14:30:00",
        ))
        sesion.commit()

        # 3. Leerlo de vuelta y comprobar que se guardo bien.
        guardado = sesion.query(IncidenteCiudadano).first()
        assert guardado is not None
        assert guardado.id is not None          # la base le asigno un id
        assert guardado.distrito == "MIRAFLORES"
        assert guardado.delito == "ROBO"
