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