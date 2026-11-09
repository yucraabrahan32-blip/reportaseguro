"""Extracción de denuncias por región del PDF SIDPOL (páginas 13 y 14)."""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

from backend.conectores import URL_SIDPOL, descargar_pdf
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
NUM = re.compile(r"^\d{1,3}(,\d{3})*$")
PCT = re.compile(r"^-?\d+%$")
REGION = re.compile(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\. ]+")


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


def _leer_pagina(ruta: Path, n_pagina: int) -> list:
    with pdfplumber.open(ruta) as pdf:
        texto = pdf.pages[n_pagina - 1].extract_text() or ""
    return [f for f in map(_fila, texto.splitlines()) if f]


def extraer_regiones(ruta: Path):
    """Cruza las páginas 13 (ene. 2026) y 14 (ene. 2025 y 2026); solo acepta filas coherentes."""
    p13 = {r: c for r, c, _ in _leer_pagina(ruta, localizar_pagina(ruta, ['II.3', 'AMAZONAS']))}
    p14 = {r: c for r, c, _ in _leer_pagina(ruta, localizar_pagina(ruta, ['II.4', 'AMAZONAS']))}
    filas, rechazadas = [], []
    for region in sorted(set(p13) | set(p14)):
        a, b = p13.get(region), p14.get(region)
        if a is None or b is None:
            rechazadas.append((region, "falta en la página 13 o en la 14"))
        elif len(a) != 7 or len(b) != 12:
            rechazadas.append((region, f"cifras inesperadas ({len(a)} y {len(b)})"))
        elif sum(a[:6]) != a[6]:
            rechazadas.append((region, "las 6 categorías no suman el total (p. 13)"))
        elif b[1::2] != a[:6]:
            rechazadas.append((region, "ene. 2026 de la p. 14 no coincide con la p. 13"))
        else:
            for k, categoria in enumerate(CATEGORIAS):
                filas.append({"region": region, "categoria": categoria,
                              "periodo": "2025-01", "cantidad": b[2 * k]})
                filas.append({"region": region, "categoria": categoria,
                              "periodo": "2026-01", "cantidad": a[k]})
    return pd.DataFrame(filas), rechazadas


if __name__ == "__main__":
    df, rechazadas = extraer_regiones(descargar_pdf(URL_SIDPOL))
    print("Regiones aceptadas:", df["region"].nunique() if not df.empty else 0)
    print(sorted(df["region"].unique()) if not df.empty else [])
    control = df[df["region"].isin(["AREQUIPA", "LIMA METROPOLITANA"])]
    print("\nFilas de control:")
    print(control.to_string(index=False))
    print("\nRechazadas:")
    for region, motivo in rechazadas:
        print("  ", region, "->", motivo)
