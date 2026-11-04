"""Catálogo de ubigeo (departamento, provincia, distrito) y validación contra SIDPOL."""
import re
import unicodedata
from pathlib import Path

import pandas as pd

from database import db

RUTA_CSV = Path("data/ubigeo/ubigeo_distrito.csv")
COLUMNAS = {
    "inei": "ubigeo_inei",
    "reniec": "ubigeo_reniec",
    "departamento": "departamento",
    "provincia": "provincia",
    "distrito": "distrito",
    "superficie": "superficie_km2",
    "pob_densidad_2020": "densidad_2020",
    "altitude": "altitud",
    "latitude": "latitud",
    "longitude": "longitud",
}
NUMERICAS = ["superficie_km2", "densidad_2020", "altitud", "latitud", "longitud"]
# Nombres del PDF que no coinciden con el catálogo (ambos normalizados).
# Se completa después de ver el resultado de la verificación.
ALIAS = {"LURIGANCHO CHOSICA": "LURIGANCHO"}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ubigeo (
    id             INTEGER PRIMARY KEY,
    ubigeo_inei    TEXT,    
    ubigeo_reniec  TEXT,
    departamento   TEXT NOT NULL,
    provincia      TEXT NOT NULL,
    distrito       TEXT NOT NULL,
    nombre_norm    TEXT NOT NULL,
    superficie_km2 REAL,
    densidad_2020  REAL,
    altitud        REAL,
    latitud        REAL,
    longitud       REAL
);
"""


def normalizar(texto) -> str:
    """Mayúsculas, sin tildes ni signos, con espacios simples."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", " ", texto.upper()).strip()


def leer_csv() -> pd.DataFrame:
    try:
        df = pd.read_csv(RUTA_CSV, dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(RUTA_CSV, dtype=str, encoding="latin-1")
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas {faltan}. Columnas reales: {list(df.columns)}")
    df = df[list(COLUMNAS)].rename(columns=COLUMNAS)
    for col in NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["nombre_norm"] = df["distrito"].map(normalizar)
    return df


def cargar_catalogo() -> int:
    df = leer_csv()
    columnas = [
        "ubigeo_inei", "ubigeo_reniec", "departamento", "provincia", "distrito",
        "nombre_norm", "superficie_km2", "densidad_2020", "altitud", "latitud", "longitud",
    ]
    filas = df.astype(object).where(df.notna(), None)[columnas].values.tolist()
    db.inicializar()
    con = db.conectar()
    try:
        con.executescript("DROP TABLE IF EXISTS ubigeo;" + ESQUEMA)
        with con:
            con.execute("DELETE FROM ubigeo")
            con.executemany(
                f"INSERT INTO ubigeo ({', '.join(columnas)}) "
                f"VALUES ({', '.join('?' * len(columnas))})",
                filas,
            )
        return len(filas)
    finally:
        con.close()


def verificar_contra_sidpol() -> None:
    """Compara los distritos del PDF (Lima y Callao) con el catálogo."""
    con = db.conectar()
    try:
        catalogo = pd.read_sql_query("SELECT distrito, provincia, nombre_norm FROM ubigeo", con)
        oficial = pd.read_sql_query("SELECT DISTINCT distrito FROM denuncias_oficiales", con)
    finally:
        con.close()

    zona = catalogo[catalogo["provincia"].map(normalizar).isin({"LIMA", "CALLAO"})]
    del_pdf = {ALIAS.get(normalizar(d), normalizar(d)): d for d in oficial["distrito"]}

    print(f"Distritos del PDF: {len(del_pdf)}")
    print(f"Distritos del catálogo en las provincias Lima y Callao: {len(zona)}")
    print("\nEn el PDF pero sin coincidencia en el catálogo:")
    for norm, original in sorted(del_pdf.items()):
        if norm not in set(zona["nombre_norm"]):
            print("  ", original)
    print("\nEn el catálogo (Lima y Callao) pero no en el PDF:")
    for _, fila in zona.iterrows():
        if fila["nombre_norm"] not in del_pdf:
            print("  ", fila["distrito"], "|", fila["provincia"])


if __name__ == "__main__":
    print("Distritos cargados:", cargar_catalogo())
    verificar_contra_sidpol()