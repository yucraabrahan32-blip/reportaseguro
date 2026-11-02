"""Conector SIDPOL (Mininter): descarga el PDF y extrae denuncias por distrito."""
import re
from pathlib import Path
from statistics import median

import pandas as pd
import pdfplumber
import requests

URL_SIDPOL = (
    "https://cdn.www.gob.pe/uploads/document/file/9435842/"
    "7729200-reporte-de-denuncias-registradas-en-el-sidpol-a-enero-del-2026.pdf"
)
CARPETA = Path("data/raw")
COLUMNAS = ["anio_2024", "anio_2025", "ene_2026"]
NUMERO = re.compile(r"^\d{1,3}(,\d{3})*$")
SOLO_LETRAS = re.compile(r"^[A-ZÁÉÍÓÚÑ\.\-]+$")
METRICAS = {
    "izq": lambda w: w["x0"],
    "centro": lambda w: (w["x0"] + w["x1"]) / 2,
    "der": lambda w: w["x1"],
}


def descargar_pdf(url: str) -> Path:
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / url.split("/")[-1]
    respuesta = requests.get(url, timeout=60)
    respuesta.raise_for_status()
    destino.write_bytes(respuesta.content)
    return destino


def _lineas(palabras, tol=3):
    """Agrupa palabras que están en la misma línea visual."""
    lineas = []
    for w in sorted(palabras, key=lambda w: w["top"]):
        if lineas and abs(w["top"] - lineas[-1][0]["top"]) <= tol:
            lineas[-1].append(w)
        else:
            lineas.append([w])
    return [sorted(linea, key=lambda w: w["x0"]) for linea in lineas]


def _centros_de_columna(filas_con_tres):
    """Elige si las cifras están alineadas a izq., centro o der. y calcula los 3 centros."""
    mejor = None
    for f in METRICAS.values():
        columnas = list(zip(*[[f(w) for w in fila] for fila in filas_con_tres]))
        dispersion = sum(max(c) - min(c) for c in columnas)
        if mejor is None or dispersion < mejor[0]:
            mejor = (dispersion, f, [median(c) for c in columnas])
    return mejor[1], mejor[2]


def extraer_distritos(ruta: Path, n_pagina: int, delitos: list[str]):
    """Devuelve (DataFrame, líneas dudosas). Asigna cada cifra a su columna por posición."""
    with pdfplumber.open(ruta) as pdf:
        pagina = pdf.pages[n_pagina - 1]
        palabras = pagina.extract_words(x_tolerance=1.5, y_tolerance=2)
        ancho, alto = pagina.width, pagina.height

    cabeceras = sorted((w for w in palabras if w["text"] == "Región"), key=lambda w: w["x0"])
    if len(cabeceras) != len(delitos):
        raise ValueError(f"Se esperaban {len(delitos)} bloques y se hallaron {len(cabeceras)}")
    fuente_top = min((w["top"] for w in palabras if w["text"].startswith("Fuente")), default=alto)

    filas, dudosas = [], []
    for i, (delito, cab) in enumerate(zip(delitos, cabeceras)):
        x_ini = cab["x0"] - 2
        x_fin = cabeceras[i + 1]["x0"] - 2 if i + 1 < len(cabeceras) else ancho
        cab_distrito = next(
            (w for w in palabras
             if w["text"] == "Distrito" and x_ini <= w["x0"] < x_fin
             and abs(w["top"] - cab["top"]) < 3),
            None,
        )
        if cab_distrito is None:
            raise ValueError(f"No se encontró la columna 'Distrito' en el bloque {delito}")
        x_distrito = cab_distrito["x0"] - 6

        zona = [w for w in palabras
                if x_ini <= w["x0"] < x_fin and w["x0"] >= x_distrito
                and cab["top"] + 3 < w["top"] < fuente_top]

        parseadas = []
        for linea in _lineas(zona):
            nums = [w for w in linea if NUMERO.match(w["text"])]
            resto = [w for w in linea if not NUMERO.match(w["text"])]
            raras = [w for w in resto if not SOLO_LETRAS.match(w["text"])]
            nombre = " ".join(w["text"] for w in resto if SOLO_LETRAS.match(w["text"]))
            parseadas.append((linea, nombre, nums, raras))

        con_tres = [nums for _, _, nums, raras in parseadas if len(nums) == 3 and not raras]
        if len(con_tres) < 5:
            raise ValueError(f"Muy pocas filas completas en {delito}; revisar el PDF")
        medir, centros = _centros_de_columna(con_tres)

        for linea, nombre, nums, raras in parseadas:
            texto = " ".join(w["text"] for w in linea)
            if raras or not nombre or not nums:
                dudosas.append((delito, texto, "texto raro, sin nombre o sin cifras"))
                continue
            valores, conflicto = [None, None, None], False
            for w in nums:
                j = min(range(3), key=lambda k: abs(medir(w) - centros[k]))
                conflicto = conflicto or valores[j] is not None
                valores[j] = int(w["text"].replace(",", ""))
            if conflicto:
                dudosas.append((delito, texto, "dos cifras en la misma columna"))
                continue
            filas.append({"delito": delito, "distrito": nombre, **dict(zip(COLUMNAS, valores))})

    df = pd.DataFrame(filas).astype({c: "Int64" for c in COLUMNAS})
    return df, dudosas
    df = pd.DataFrame(filas).astype({c: "Int64" for c in COLUMNAS})
    return df, dudosas


# Correcciones manuales de filas ilegibles en el PDF.
# CONFIRMAR cada valor mirando la página 30 antes de usarlo.
CORRECCIONES = {
    ("HURTO", "LIMA"): (11222, 9438, 717),  # 2024, 2025, ene. 2026
}


def aplicar_correcciones(df: pd.DataFrame, correcciones: dict) -> pd.DataFrame:
    """Reemplaza filas corruptas y las marca como corrección manual."""
    df = df.copy()
    df["correccion_manual"] = False
    for (delito, distrito), valores in correcciones.items():
        fila = {"delito": delito, "distrito": distrito,
                "correccion_manual": True, **dict(zip(COLUMNAS, valores))}
        mascara = (df["delito"] == delito) & (df["distrito"] == distrito)
        df = pd.concat([df[~mascara], pd.DataFrame([fila])], ignore_index=True)
    return df.astype({c: "Int64" for c in COLUMNAS})


if __name__ == "__main__":
    archivo = descargar_pdf(URL_SIDPOL)
    ...

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

if __name__ == "__main__":
    archivo = descargar_pdf(URL_SIDPOL)
    df, dudosas = extraer_distritos(archivo, 30, ["HOMICIDIO", "HURTO", "ROBO"])
    print("Filas por delito:")
    print(df.groupby("delito").size())
    muestra = ["SAN JUAN DE LURIGANCHO", "RIMAC", "JESUS MARIA", "SAN BARTOLO", "PUNTA NEGRA", "CALLAO"]
    print("\nFilas de control:")
    print(df[df["distrito"].isin(muestra)].to_string(index=False))
    print("\nLíneas dudosas (revisar a mano):")
    for delito, texto, motivo in dudosas:
        print(f"  [{delito}] {texto}  -> {motivo}")
    df.to_csv(CARPETA / "sidpol_distritos_p30.csv", index=False)
    print("\nGuardado en data/raw/sidpol_distritos_p30.csv")