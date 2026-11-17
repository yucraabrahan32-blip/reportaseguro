"""Extracción de denuncias por región del PDF SIDPOL (tablas II.3 y II.4)."""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

from backend.paginas import localizar_pagina

# Orden inferido de los encabezados del PDF; verificar contra el original.
CATEGORIAS = [
    "Delitos patrimoniales",
    "Delitos contra la seguridad pública",
    "Delitos contra la vida, el cuerpo y la salud",
    "Delitos contra la libertad",
    "Delitos contra la administración pública",
    "Otros delitos",
]
# Lima Metropolitana, Región Lima y el Callao cuentan por separado, como en la fuente.
REGIONES_ESPERADAS = 26
NUM = re.compile(r"^\d{1,3}(,\d{3})*$")
PCT = re.compile(r"^-?\d+%$")
REGION = re.compile(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\. ]+")
ABREVIATURAS = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}
PATRON_CORTE = re.compile(r"\(\s*ene\.(?:\s*-\s*([a-z]{3})\.)?\s*\)\s*(\d{4})", re.IGNORECASE)


def leer_corte(texto: str) -> str:
    """Mes de corte (AAAA-MM) leído del título de la tabla: '(ene.-jul.) 2026' -> '2026-07'."""
    m = PATRON_CORTE.search(texto)
    if not m:
        raise ValueError("No se pudo leer el periodo (mes de corte) del reporte.")
    mes = ABREVIATURAS.get((m.group(1) or "ene").lower())
    if mes is None:
        raise ValueError(f"Mes de corte no reconocido: {m.group(1)!r}.")
    return f"{m.group(2)}-{mes:02d}"


def _fila(linea: str):
    """Devuelve (región, cifras, porcentajes) o None si la línea no es una fila de datos."""
    tokens = linea.split()
    i = next((k for k, t in enumerate(tokens) if NUM.match(t)), None)
    if not i:  # no hay cifras, o la línea empieza con una cifra
        return None
    region = re.sub(r"\s*\d/$", "", " ".join(tokens[:i])).strip()
    if not REGION.fullmatch(region):
        return None
    resto = tokens[i:]
    if any(not NUM.match(t) and not PCT.match(t) for t in resto):
        return None
    cifras = [int(t.replace(",", "")) for t in resto if NUM.match(t)]
    porcentajes = [t for t in resto if PCT.match(t)]
    return region, cifras, porcentajes


def _filas(texto: str) -> list:
    return [f for f in map(_fila, texto.splitlines()) if f]


def extraer_regiones(ruta: Path):
    """Cruza las tablas II.3 y II.4; solo acepta filas coherentes. Devuelve (DataFrame, rechazadas).

    Los periodos son '2025' y '2026': cifras acumuladas de enero al mes de corte de cada año.
    """
    n13 = localizar_pagina(ruta, ["II.3", "AMAZONAS"])
    n14 = localizar_pagina(ruta, ["II.4", "AMAZONAS"])
    with pdfplumber.open(ruta) as pdf:
        texto13 = pdf.pages[n13 - 1].extract_text() or ""
        texto14 = pdf.pages[n14 - 1].extract_text() or ""
    corte = leer_corte(texto13)
    p13 = {r: c for r, c, _ in _filas(texto13)}
    p14 = {r: c for r, c, _ in _filas(texto14)}

    filas, rechazadas = [], []
    for region in sorted(set(p13) | set(p14)):
        a, b = p13.get(region), p14.get(region)
        if a is None or b is None:
            rechazadas.append((region, "falta en la tabla II.3 o en la II.4"))
        elif len(a) != 7 or len(b) != 12:
            rechazadas.append((region, f"cifras inesperadas ({len(a)} y {len(b)})"))
        elif sum(a[:6]) != a[6]:
            rechazadas.append((region, "las 6 categorías no suman el total (II.3)"))
        elif b[1::2] != a[:6]:
            rechazadas.append((region, "las cifras de 2026 de la II.4 no coinciden con la II.3"))
        else:
            for k, categoria in enumerate(CATEGORIAS):
                filas.append({"region": region, "categoria": categoria,
                              "periodo": "2025", "cantidad": b[2 * k], "corte": corte})
                filas.append({"region": region, "categoria": categoria,
                              "periodo": "2026", "cantidad": a[k], "corte": corte})
    return pd.DataFrame(filas), rechazadas
