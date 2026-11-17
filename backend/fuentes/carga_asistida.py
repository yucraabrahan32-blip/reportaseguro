"""Carga asistida: un administrador sube un CSV con indicadores que una fuente externa ya publicó."""
import io
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.conectores import CARPETA
from backend.fuentes.base import ConectorDatos
from database import db

COLUMNAS = ["ambito", "lugar", "indicador", "periodo", "valor", "unidad"]
AMBITOS = {"nacional", "region", "distrito"}
CLAVES = ["ambito", "lugar", "indicador", "periodo"]
MAX_BYTES = 2_000_000
MAX_FILAS = 5000
PLANTILLA = ",".join(COLUMNAS) + "\n"


def _leer_texto(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("latin-1")


def _validar_fila(r):
    """Devuelve (fila limpia, "") si es válida, o (None, motivo)."""
    ambito = r.ambito.strip().lower()
    if ambito not in AMBITOS:
        return None, "ámbito no válido (usa nacional, region o distrito)"
    for nombre in ("lugar", "indicador", "periodo", "unidad"):
        if not getattr(r, nombre).strip():
            return None, f"falta {nombre}"
    valor = r.valor.strip()
    if "," in valor:
        return None, "usa punto decimal y sin separador de miles"
    try:
        numero = float(valor)
    except ValueError:
        return None, "el valor no es un número"
    if not math.isfinite(numero):
        return None, "el valor no es un número finito"
    return {
        "ambito": ambito, "lugar": r.lugar.strip(), "indicador": r.indicador.strip(),
        "periodo": r.periodo.strip(), "valor": numero, "unidad": r.unidad.strip(),
    }, ""


class CargaAsistidaCSV(ConectorDatos):
    def __init__(self, contenido: bytes, fuente: str, entidad: str, tipo: str, url_fuente: str):
        fuente, entidad, url_fuente = fuente.strip(), entidad.strip(), url_fuente.strip()
        if not fuente or not entidad:
            raise ValueError("Indica el nombre de la fuente y la entidad que la publica.")
        if tipo not in db.TIPOS_FUENTE_EXTERNA:
            raise ValueError("El tipo de fuente debe ser 'estatal' u 'ong'.")
        if not url_fuente.lower().startswith(("http://", "https://")):
            raise ValueError("Indica el enlace (http o https) donde se publica el dato.")
        if not contenido:
            raise ValueError("El archivo está vacío.")
        if len(contenido) > MAX_BYTES:
            raise ValueError("El archivo supera los 2 MB.")
        self.contenido = contenido
        self.fuente = fuente
        self.entidad = entidad
        self.tipo = tipo
        self.url = url_fuente
        self.nombre = f"Carga asistida: {fuente}"

    def descargar(self) -> Path:
        """No descarga nada: guarda el archivo subido con un nombre propio (nunca el del usuario)."""
        CARPETA.mkdir(parents=True, exist_ok=True)
        ruta = CARPETA / f"carga_{datetime.now():%Y%m%d_%H%M%S_%f}.csv"
        ruta.write_bytes(self.contenido)
        return ruta

    def extraer(self, archivo: Path) -> tuple[pd.DataFrame, list[str]]:
        texto = _leer_texto(archivo.read_bytes())
        lineas = texto.splitlines()
        if not lineas:
            raise ValueError("El archivo está vacío.")
        sep = ";" if lineas[0].count(";") > lineas[0].count(",") else ","  # Excel en español usa ;
        try:
            df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=False)
        except pd.errors.ParserError as error:
            raise ValueError(f"No se pudo leer el CSV: {error}") from None
        df.columns = [c.strip().lower() for c in df.columns]
        faltan = [c for c in COLUMNAS if c not in df.columns]
        if faltan:
            raise ValueError(f"Faltan columnas: {', '.join(faltan)}. Descarga la plantilla.")
        if len(df) > MAX_FILAS:
            raise ValueError(f"El archivo tiene más de {MAX_FILAS} filas.")

        filas, advertencias = [], []
        for numero, fila in enumerate(df[COLUMNAS].itertuples(index=False), start=2):
            limpia, motivo = _validar_fila(fila)
            if limpia is None:
                advertencias.append(f"Fila {numero}: {motivo}")
            else:
                filas.append(limpia)
        if not filas:
            raise ValueError("Ninguna fila es válida. " + "; ".join(advertencias[:3]))

        resultado = pd.DataFrame(filas, columns=COLUMNAS)
        repetidas = int(resultado.duplicated(subset=CLAVES, keep="last").sum())
        if repetidas:
            resultado = resultado.drop_duplicates(subset=CLAVES, keep="last")
            advertencias.append(f"{repetidas} fila(s) repetida(s): se conservó la última.")
        return resultado, advertencias

    def guardar(self, datos: pd.DataFrame, archivo: Path) -> int:
        return db.guardar_indicadores(
            datos, self.fuente, self.entidad, self.tipo, self.url, archivo.name
        )
