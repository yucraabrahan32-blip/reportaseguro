"""Persistencia SQLite de ReportaSeguro."""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

RUTA_DB = Path("database/reportaseguro.db")
PERIODOS = {"anio_2024": "2024", "anio_2025": "2025", "ene_2026": "2026-01"}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS fuentes (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE,
    entidad TEXT NOT NULL,
    tipo    TEXT NOT NULL CHECK (tipo IN ('estatal', 'ong', 'ciudadana'))
);

CREATE TABLE IF NOT EXISTS sincronizaciones (
    id             INTEGER PRIMARY KEY,
    fuente_id      INTEGER NOT NULL REFERENCES fuentes(id),
    url            TEXT NOT NULL,
    archivo        TEXT NOT NULL,
    fecha_descarga TEXT NOT NULL,
    filas_cargadas INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS denuncias_oficiales (
    id                INTEGER PRIMARY KEY,
    fuente_id         INTEGER NOT NULL REFERENCES fuentes(id),
    sincronizacion_id INTEGER NOT NULL REFERENCES sincronizaciones(id),
    distrito          TEXT NOT NULL,
    delito            TEXT NOT NULL,
    periodo           TEXT NOT NULL,
    cantidad          INTEGER NOT NULL CHECK (cantidad >= 0),
    correccion_manual INTEGER NOT NULL DEFAULT 0,
    UNIQUE (fuente_id, distrito, delito, periodo)
);

CREATE TABLE IF NOT EXISTS incidentes_ciudadanos (
    id           INTEGER PRIMARY KEY,
    departamento TEXT,
    provincia    TEXT,
    distrito     TEXT NOT NULL,
    delito       TEXT NOT NULL,
    fecha_hecho  TEXT NOT NULL,
    hora_hecho   TEXT NOT NULL,
    descripcion  TEXT NOT NULL,
    creado_en    TEXT NOT NULL
);
"""


def conectar() -> sqlite3.Connection:
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(RUTA_DB)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _migrar(con: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a bases creadas con versiones anteriores."""
    columnas = {f[1] for f in con.execute("PRAGMA table_info(incidentes_ciudadanos)")}
    for nombre in ("departamento", "provincia"):
        if nombre not in columnas:
            con.execute(f"ALTER TABLE incidentes_ciudadanos ADD COLUMN {nombre} TEXT")


def inicializar() -> None:
    con = conectar()
    try:
        with con:
            con.executescript(ESQUEMA)
            _migrar(con)
            con.execute(
                "INSERT OR IGNORE INTO fuentes (nombre, entidad, tipo) VALUES (?, ?, ?)",
                ("SIDPOL - Mininter", "Ministerio del Interior", "estatal"),
            )
    finally:
        con.close()


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
    con = conectar()
    try:
        with con:
            fuente_id = con.execute(
                "SELECT id FROM fuentes WHERE nombre = ?", (fuente,)
            ).fetchone()[0]
            sync_id = con.execute(
                "INSERT INTO sincronizaciones (fuente_id, url, archivo, fecha_descarga, filas_cargadas) "
                "VALUES (?, ?, ?, ?, ?)",
                (fuente_id, url, archivo, datetime.now().isoformat(timespec="seconds"), len(largo)),
            ).lastrowid
            con.executemany(
                """
                INSERT INTO denuncias_oficiales
                    (fuente_id, sincronizacion_id, distrito, delito, periodo, cantidad, correccion_manual)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (fuente_id, distrito, delito, periodo) DO UPDATE SET
                    cantidad = excluded.cantidad,
                    correccion_manual = excluded.correccion_manual,
                    sincronizacion_id = excluded.sincronizacion_id
                """,
                [
                    (fuente_id, sync_id, r.distrito, r.delito, r.periodo,
                     int(r.cantidad), int(r.correccion_manual))
                    for r in largo.itertuples()
                ],
            )
        return len(largo)
    finally:
        con.close()


# ---------- Catálogo de ubigeo (se carga con: python -m backend.ubigeo) ----------

def _consulta_ubigeo(sql: str, params: tuple = ()) -> list:
    inicializar()
    con = conectar()
    try:
        return [f[0] for f in con.execute(sql, params).fetchall()]
    except sqlite3.OperationalError:
        return []  # la tabla ubigeo aún no existe
    finally:
        con.close()


def listar_departamentos() -> list[str]:
    return _consulta_ubigeo("SELECT DISTINCT departamento FROM ubigeo ORDER BY departamento")


def listar_provincias(departamento: str) -> list[str]:
    return _consulta_ubigeo(
        "SELECT DISTINCT provincia FROM ubigeo WHERE departamento = ? ORDER BY provincia",
        (departamento,),
    )


def listar_distritos_de(departamento: str, provincia: str) -> list[str]:
    return _consulta_ubigeo(
        "SELECT distrito FROM ubigeo WHERE departamento = ? AND provincia = ? ORDER BY distrito",
        (departamento, provincia),
    )


# ---------- Incidentes ciudadanos ----------

def guardar_incidente(departamento: str, provincia: str, distrito: str, delito: str,
                      fecha_hecho: str, hora_hecho: str, descripcion: str) -> int:
    inicializar()
    con = conectar()
    try:
        with con:
            return con.execute(
                "INSERT INTO incidentes_ciudadanos "
                "(departamento, provincia, distrito, delito, fecha_hecho, hora_hecho, "
                " descripcion, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (departamento, provincia, distrito, delito, fecha_hecho, hora_hecho,
                 descripcion.strip(), datetime.now().isoformat(timespec="seconds")),
            ).lastrowid
    finally:
        con.close()


def listar_incidentes(limite: int = 10) -> pd.DataFrame:
    inicializar()
    con = conectar()
    try:
        return pd.read_sql_query(
            "SELECT id, departamento, provincia, distrito, delito, fecha_hecho, "
            "hora_hecho, descripcion FROM incidentes_ciudadanos ORDER BY id DESC LIMIT ?",
            con, params=(limite,),
        )
    finally:
        con.close()


def actualizar_incidente(id_incidente: int, delito: str, descripcion: str) -> bool:
    """Solo se editan el tipo y la descripción; la ubicación no cambia."""
    inicializar()
    con = conectar()
    try:
        with con:
            cur = con.execute(
                "UPDATE incidentes_ciudadanos SET delito = ?, descripcion = ? WHERE id = ?",
                (delito, descripcion.strip(), id_incidente),
            )
            return cur.rowcount > 0
    finally:
        con.close()


def eliminar_incidente(id_incidente: int) -> bool:
    inicializar()
    con = conectar()
    try:
        with con:
            cur = con.execute("DELETE FROM incidentes_ciudadanos WHERE id = ?", (id_incidente,))
            return cur.rowcount > 0
    finally:
        con.close()


# ---------- Sincronizaciones ----------

def ultima_sincronizacion():
    """Devuelve la última sincronización como diccionario, o None si no hay."""
    inicializar()
    con = conectar()
    try:
        fila = con.execute(
            "SELECT f.nombre, s.archivo, s.fecha_descarga, s.filas_cargadas "
            "FROM sincronizaciones s JOIN fuentes f ON f.id = s.fuente_id "
            "ORDER BY s.id DESC LIMIT 1"
        ).fetchone()
        if fila is None:
            return None
        return {"fuente": fila[0], "archivo": fila[1], "fecha": fila[2], "filas": fila[3]}
    finally:
        con.close()


def historial_sincronizaciones(limite: int = 10) -> pd.DataFrame:
    inicializar()
    con = conectar()
    try:
        return pd.read_sql_query(
            "SELECT s.id, f.nombre AS fuente, s.fecha_descarga, s.archivo, s.filas_cargadas "
            "FROM sincronizaciones s JOIN fuentes f ON f.id = s.fuente_id "
            "ORDER BY s.id DESC LIMIT ?",
            con, params=(limite,),
        )
    finally:
        con.close()


# ---------- DataFrames para estadísticas ----------

def denuncias_oficiales_df() -> pd.DataFrame:
    inicializar()
    con = conectar()
    try:
        return pd.read_sql_query(
            "SELECT distrito, delito, periodo, cantidad, correccion_manual "
            "FROM denuncias_oficiales",
            con,
        )
    finally:
        con.close()


def incidentes_df() -> pd.DataFrame:
    inicializar()
    con = conectar()
    try:
        return pd.read_sql_query(
            "SELECT id, departamento, provincia, distrito, delito, fecha_hecho, hora_hecho "
            "FROM incidentes_ciudadanos",
            con,
        )
    finally:
        con.close()

def ubigeo_df() -> pd.DataFrame:
    inicializar()
    con = conectar()
    try:
        return pd.read_sql_query(
            "SELECT departamento, provincia, distrito, nombre_norm, latitud, longitud "
            "FROM ubigeo",
            con,
        )
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return pd.DataFrame()  # la tabla ubigeo aún no existe
    finally:
        con.close()


def incidentes_con_coordenadas() -> pd.DataFrame:
    """Reportes ciudadanos unidos al catálogo para obtener las coordenadas del distrito."""
    inicializar()
    con = conectar()
    try:
        return pd.read_sql_query(
            "SELECT i.id, i.departamento, i.provincia, i.distrito, i.delito, "
            "       u.latitud, u.longitud "
            "FROM incidentes_ciudadanos i "
            "JOIN ubigeo u ON u.departamento = i.departamento "
            "             AND u.provincia = i.provincia "
            "             AND u.distrito = i.distrito "
            "WHERE u.latitud IS NOT NULL AND u.longitud IS NOT NULL",
            con,
        )
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return pd.DataFrame()
    finally:
        con.close()