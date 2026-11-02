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
"""


def conectar() -> sqlite3.Connection:
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(RUTA_DB)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar() -> None:
    con = conectar()
    try:
        with con:
            con.executescript(ESQUEMA)
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