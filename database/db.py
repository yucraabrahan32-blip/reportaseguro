"""Persistencia de ReportaSeguro con SQLAlchemy (ORM) sobre SQLite."""
from datetime import datetime

import pandas as pd
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database.modelos import (
    Base, DenunciaOficial, DenunciaRegional, IncidenteCiudadano, IndicadorExterno,
    Fuente, Session, Sincronizacion, Ubigeo, engine,
)

PERIODOS = {"anio_2024": "2024", "anio_2025": "2025", "ene_2026": "2026-01"}
TIPOS_FUENTE_EXTERNA = ("estatal", "ong")
_LISTO = False


def _migrar_columnas() -> None:
    """Agrega columnas nuevas a bases creadas con versiones anteriores (SQLite ADD COLUMN)."""
    with engine.begin() as con:
        existentes = {fila[1] for fila in con.exec_driver_sql("PRAGMA table_info(incidentes_ciudadanos)")}
        for columna in ("latitud", "longitud"):
            if columna not in existentes:
                con.exec_driver_sql(f"ALTER TABLE incidentes_ciudadanos ADD COLUMN {columna} REAL")


def inicializar() -> None:
    """Crea las tablas que falten y registra la fuente SIDPOL (una sola vez por ejecución)."""
    global _LISTO
    if _LISTO:
        return
    Base.metadata.create_all(engine)
    _migrar_columnas()
    with Session.begin() as s:
        if s.scalar(select(Fuente.id).where(Fuente.nombre == "SIDPOL - Mininter")) is None:
            s.add(Fuente(nombre="SIDPOL - Mininter", entidad="Ministerio del Interior", tipo="estatal"))
    _LISTO = True


def consulta_df(stmt) -> pd.DataFrame:
    """Ejecuta un select de SQLAlchemy y devuelve un DataFrame."""
    inicializar()
    with engine.connect() as con:
        return pd.read_sql_query(stmt, con)


def _columna(stmt) -> list:
    inicializar()
    with Session() as s:
        return list(s.scalars(stmt))


def _nueva_sync(s, fuente_id: int, url: str, archivo: str, filas: int) -> int:
    sync = Sincronizacion(
        fuente_id=fuente_id, url=url, archivo=archivo,
        fecha_descarga=datetime.now().isoformat(timespec="seconds"), filas_cargadas=filas,
    )
    s.add(sync)
    s.flush()
    return sync.id


# ---------- Denuncias oficiales (distritos) ----------

def guardar_denuncias_oficiales(df: pd.DataFrame, fuente: str, url: str, archivo: str) -> int:
    """Guarda el DataFrame en formato largo. Si ya existe la fila, la actualiza."""
    largo = df.melt(
        id_vars=["delito", "distrito", "correccion_manual"],
        value_vars=list(PERIODOS),
        var_name="col",
        value_name="cantidad",
    ).dropna(subset=["cantidad"])
    largo["periodo"] = largo["col"].map(PERIODOS)

    inicializar()
    with Session.begin() as s:
        fuente_id = s.scalar(select(Fuente.id).where(Fuente.nombre == fuente))
        sync_id = _nueva_sync(s, fuente_id, url, archivo, len(largo))
        filas = [
            {"fuente_id": fuente_id, "sincronizacion_id": sync_id, "distrito": r.distrito,
             "delito": r.delito, "periodo": r.periodo, "cantidad": int(r.cantidad),
             "correccion_manual": int(r.correccion_manual)}
            for r in largo.itertuples()
        ]
        stmt = sqlite_insert(DenunciaOficial)
        stmt = stmt.on_conflict_do_update(
            index_elements=["fuente_id", "distrito", "delito", "periodo"],
            set_={
                "cantidad": stmt.excluded.cantidad,
                "correccion_manual": stmt.excluded.correccion_manual,
                "sincronizacion_id": stmt.excluded.sincronizacion_id,
            },
        )
        s.execute(stmt, filas)
    return len(largo)


def denuncias_oficiales_df() -> pd.DataFrame:
    return consulta_df(select(
        DenunciaOficial.distrito, DenunciaOficial.delito, DenunciaOficial.periodo,
        DenunciaOficial.cantidad, DenunciaOficial.correccion_manual,
    ))


# ---------- Catálogo de ubigeo (se carga con: python -m backend.ubigeo) ----------

def listar_departamentos() -> list[str]:
    return _columna(select(Ubigeo.departamento).distinct().order_by(Ubigeo.departamento))


def listar_provincias(departamento: str) -> list[str]:
    return _columna(
        select(Ubigeo.provincia).where(Ubigeo.departamento == departamento)
        .distinct().order_by(Ubigeo.provincia)
    )


def listar_distritos_de(departamento: str, provincia: str) -> list[str]:
    return _columna(
        select(Ubigeo.distrito)
        .where(Ubigeo.departamento == departamento, Ubigeo.provincia == provincia)
        .order_by(Ubigeo.distrito)
    )


def ubigeo_df() -> pd.DataFrame:
    return consulta_df(select(
        Ubigeo.departamento, Ubigeo.provincia, Ubigeo.distrito,
        Ubigeo.nombre_norm, Ubigeo.latitud, Ubigeo.longitud,
    ))


# ---------- Incidentes ciudadanos ----------

def guardar_incidente(departamento: str, provincia: str, distrito: str, delito: str,
                      fecha_hecho: str, hora_hecho: str, descripcion: str,
                      latitud: float | None = None, longitud: float | None = None) -> int:
    inicializar()
    with Session.begin() as s:
        incidente = IncidenteCiudadano(
            departamento=departamento, provincia=provincia, distrito=distrito, delito=delito,
            fecha_hecho=fecha_hecho, hora_hecho=hora_hecho, descripcion=descripcion.strip(),
            creado_en=datetime.now().isoformat(timespec="seconds"),
            latitud=latitud, longitud=longitud,
        )
        s.add(incidente)
        s.flush()
        return incidente.id


def listar_incidentes(limite: int = 10) -> pd.DataFrame:
    return consulta_df(
        select(
            IncidenteCiudadano.id, IncidenteCiudadano.departamento, IncidenteCiudadano.provincia,
            IncidenteCiudadano.distrito, IncidenteCiudadano.delito, IncidenteCiudadano.fecha_hecho,
            IncidenteCiudadano.hora_hecho, IncidenteCiudadano.descripcion,
        ).order_by(IncidenteCiudadano.id.desc()).limit(limite)
    )


def actualizar_incidente(id_incidente: int, delito: str, descripcion: str) -> bool:
    """Solo se editan el tipo y la descripción; la ubicación no cambia."""
    inicializar()
    with Session.begin() as s:
        resultado = s.execute(
            update(IncidenteCiudadano).where(IncidenteCiudadano.id == id_incidente)
            .values(delito=delito, descripcion=descripcion.strip())
        )
        return resultado.rowcount > 0


def eliminar_incidente(id_incidente: int) -> bool:
    inicializar()
    with Session.begin() as s:
        resultado = s.execute(delete(IncidenteCiudadano).where(IncidenteCiudadano.id == id_incidente))
        return resultado.rowcount > 0


def incidentes_df() -> pd.DataFrame:
    return consulta_df(select(
        IncidenteCiudadano.id, IncidenteCiudadano.departamento, IncidenteCiudadano.provincia,
        IncidenteCiudadano.distrito, IncidenteCiudadano.delito,
        IncidenteCiudadano.fecha_hecho, IncidenteCiudadano.hora_hecho,
    ))


def incidentes_con_coordenadas() -> pd.DataFrame:
    """Reportes ciudadanos con coordenadas: usa el punto real marcado al reportar y,
    si no existe, cae en el centroide del distrito del catálogo ubigeo."""
    i, u = IncidenteCiudadano, Ubigeo
    lat = func.coalesce(i.latitud, u.latitud)
    lon = func.coalesce(i.longitud, u.longitud)
    return consulta_df(
        select(i.id, i.departamento, i.provincia, i.distrito, i.delito,
               lat.label("latitud"), lon.label("longitud"))
        .join(u, (u.departamento == i.departamento) & (u.provincia == i.provincia)
              & (u.distrito == i.distrito), isouter=True)
        .where(lat.is_not(None))
    )


# ---------- Sincronizaciones ----------

def ultima_sincronizacion():
    """Devuelve la última sincronización como diccionario, o None si no hay."""
    inicializar()
    with Session() as s:
        fila = s.execute(
            select(Fuente.nombre, Sincronizacion.archivo,
                   Sincronizacion.fecha_descarga, Sincronizacion.filas_cargadas)
            .join(Fuente, Fuente.id == Sincronizacion.fuente_id)
            .order_by(Sincronizacion.id.desc()).limit(1)
        ).first()
    if fila is None:
        return None
    return {"fuente": fila[0], "archivo": fila[1], "fecha": fila[2], "filas": fila[3]}


def historial_sincronizaciones(limite: int = 10) -> pd.DataFrame:
    return consulta_df(
        select(Sincronizacion.id, Fuente.nombre.label("fuente"), Sincronizacion.fecha_descarga,
               Sincronizacion.archivo, Sincronizacion.filas_cargadas)
        .join(Fuente, Fuente.id == Sincronizacion.fuente_id)
        .order_by(Sincronizacion.id.desc()).limit(limite)
    )


# ---------- Denuncias regionales ----------

def guardar_denuncias_regionales(df: pd.DataFrame, fuente: str, url: str, archivo: str) -> int:
    """Reemplaza las cifras regionales por las del reporte cargado; cada fila lleva su mes de corte."""
    inicializar()
    with Session.begin() as s:
        fuente_id = s.scalar(select(Fuente.id).where(Fuente.nombre == fuente))
        sync_id = _nueva_sync(s, fuente_id, url, archivo, len(df))
        s.execute(delete(DenunciaRegional))
        s.execute(
            sqlite_insert(DenunciaRegional),
            [{"fuente_id": fuente_id, "sincronizacion_id": sync_id, "region": r.region,
              "categoria": r.categoria, "periodo": r.periodo, "cantidad": int(r.cantidad),
              "corte": r.corte} for r in df.itertuples()],
        )
    return len(df)


def denuncias_regionales_df() -> pd.DataFrame:
    return consulta_df(select(
        DenunciaRegional.region, DenunciaRegional.categoria, DenunciaRegional.periodo,
        DenunciaRegional.cantidad, DenunciaRegional.corte,
    ))


def cortes_cargados() -> dict:
    """Mes de corte de los datos cargados: por distrito y por región (AAAA-MM o None)."""
    inicializar()
    with Session() as s:
        distrital = s.scalar(
            select(func.max(DenunciaOficial.periodo)).where(DenunciaOficial.periodo.like("____-__"))
        )
        regional = s.scalar(select(func.max(DenunciaRegional.corte)))
    return {"distrital": distrital, "regional": regional}


# ---------- Indicadores externos ----------

def guardar_indicadores(df: pd.DataFrame, fuente: str, entidad: str, tipo: str,
                        url: str, archivo: str) -> int:
    """Guarda indicadores de una fuente externa. Si la fila ya existe, la actualiza."""
    if tipo not in TIPOS_FUENTE_EXTERNA:
        raise ValueError("El tipo de fuente debe ser 'estatal' u 'ong'.")
    inicializar()
    with Session.begin() as s:
        existente = s.scalar(select(Fuente).where(Fuente.nombre == fuente))
        if existente and existente.tipo != tipo:
            raise ValueError(f"Ya existe una fuente llamada '{fuente}' de tipo '{existente.tipo}'.")
        if existente is None:
            existente = Fuente(nombre=fuente, entidad=entidad, tipo=tipo)
            s.add(existente)
            s.flush()
        sync_id = _nueva_sync(s, existente.id, url, archivo, len(df))
        filas = [
            {"fuente_id": existente.id, "sincronizacion_id": sync_id, "ambito": r.ambito,
             "lugar": r.lugar, "indicador": r.indicador, "periodo": r.periodo,
             "valor": float(r.valor), "unidad": r.unidad}
            for r in df.itertuples()
        ]
        stmt = sqlite_insert(IndicadorExterno)
        stmt = stmt.on_conflict_do_update(
            index_elements=["fuente_id", "ambito", "lugar", "indicador", "periodo"],
            set_={"valor": stmt.excluded.valor, "unidad": stmt.excluded.unidad,
                  "sincronizacion_id": stmt.excluded.sincronizacion_id},
        )
        s.execute(stmt, filas)
    return len(df)


def indicadores_df() -> pd.DataFrame:
    i = IndicadorExterno
    return consulta_df(
        select(i.ambito, i.lugar, i.indicador, i.periodo, i.valor, i.unidad,
               Fuente.nombre.label("fuente"), Fuente.entidad, Fuente.tipo,
               Sincronizacion.url, Sincronizacion.fecha_descarga)
        .join(Fuente, Fuente.id == i.fuente_id)
        .join(Sincronizacion, Sincronizacion.id == i.sincronizacion_id)
    )