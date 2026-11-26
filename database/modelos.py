"""Conexión (engine) y modelos ORM de ReportaSeguro. Cada clase es una tabla."""
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Ruta absoluta: ya no depende de desde dónde ejecutes la app.
RUTA_DB = Path(__file__).resolve().parent / "reportaseguro.db"

engine = create_engine(
    f"sqlite:///{RUTA_DB.as_posix()}",
    echo=False,
    connect_args={"check_same_thread": False},  # Streamlit usa varios hilos
)


@event.listens_for(engine, "connect")
def _activar_claves_foraneas(conexion, _):
    conexion.execute("PRAGMA foreign_keys = ON")


Session = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Fuente(Base):
    __tablename__ = "fuentes"
    __table_args__ = (CheckConstraint("tipo IN ('estatal', 'ong', 'ciudadana')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True)
    entidad: Mapped[str]
    tipo: Mapped[str]


class Sincronizacion(Base):
    __tablename__ = "sincronizaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    fuente_id: Mapped[int] = mapped_column(ForeignKey("fuentes.id"))
    url: Mapped[str]
    archivo: Mapped[str]
    fecha_descarga: Mapped[str]
    filas_cargadas: Mapped[int]


class DenunciaOficial(Base):
    __tablename__ = "denuncias_oficiales"
    __table_args__ = (
        CheckConstraint("cantidad >= 0"),
        UniqueConstraint("fuente_id", "distrito", "delito", "periodo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fuente_id: Mapped[int] = mapped_column(ForeignKey("fuentes.id"))
    sincronizacion_id: Mapped[int] = mapped_column(ForeignKey("sincronizaciones.id"))
    distrito: Mapped[str]
    delito: Mapped[str]
    periodo: Mapped[str]
    cantidad: Mapped[int]
    correccion_manual: Mapped[int] = mapped_column(default=0)


class DenunciaRegional(Base):
    __tablename__ = "denuncias_regionales"
    __table_args__ = (
        CheckConstraint("cantidad >= 0"),
        UniqueConstraint("fuente_id", "region", "categoria", "periodo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fuente_id: Mapped[int] = mapped_column(ForeignKey("fuentes.id"))
    sincronizacion_id: Mapped[int] = mapped_column(ForeignKey("sincronizaciones.id"))
    region: Mapped[str]
    categoria: Mapped[str]
    periodo: Mapped[str]
    cantidad: Mapped[int]
    corte: Mapped[str | None]


class IncidenteCiudadano(Base):
    __tablename__ = "incidentes_ciudadanos"

    id: Mapped[int] = mapped_column(primary_key=True)
    departamento: Mapped[str | None]
    provincia: Mapped[str | None]
    distrito: Mapped[str]
    delito: Mapped[str]
    fecha_hecho: Mapped[str]
    hora_hecho: Mapped[str]
    descripcion: Mapped[str]
    creado_en: Mapped[str]
    latitud: Mapped[float | None]
    longitud: Mapped[float | None]


class Ubigeo(Base):
    __tablename__ = "ubigeo"

    id: Mapped[int] = mapped_column(primary_key=True)
    ubigeo_inei: Mapped[str | None]
    ubigeo_reniec: Mapped[str | None]
    departamento: Mapped[str]
    provincia: Mapped[str]
    distrito: Mapped[str]
    nombre_norm: Mapped[str]
    superficie_km2: Mapped[float | None]
    densidad_2020: Mapped[float | None]
    altitud: Mapped[float | None]
    latitud: Mapped[float | None]
    longitud: Mapped[float | None]


class IndicadorExterno(Base):
    __tablename__ = "indicadores_externos"
    __table_args__ = (
        CheckConstraint("ambito IN ('nacional', 'region', 'distrito')"),
        UniqueConstraint("fuente_id", "ambito", "lugar", "indicador", "periodo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fuente_id: Mapped[int] = mapped_column(ForeignKey("fuentes.id"))
    sincronizacion_id: Mapped[int] = mapped_column(ForeignKey("sincronizaciones.id"))
    ambito: Mapped[str]
    lugar: Mapped[str]
    indicador: Mapped[str]
    periodo: Mapped[str]
    valor: Mapped[float]
    unidad: Mapped[str]


class Administrador(Base):
    __tablename__ = "administradores"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String, unique=True)
    clave_hash: Mapped[str]
    creado_en: Mapped[str]


class IntentoLogin(Base):
    __tablename__ = "intentos_login"

    usuario: Mapped[str] = mapped_column(String, primary_key=True)
    fallos: Mapped[int]
    bloqueado_hasta: Mapped[float] = mapped_column(default=0)
    ultimo_intento: Mapped[float]