"""Detecta cuál es el reporte SIDPOL más reciente publicado por el Observatorio (solo lectura)."""
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.gob.pe"
COLECCION = (
    BASE + "/institucion/mininter/colecciones/"
    "13872-reportes-del-observatorio-nacional-de-seguridad-ciudadana"
)
CABECERAS = {"User-Agent": "Mozilla/5.0"}
NOMBRES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "setiembre", "octubre", "noviembre", "diciembre"]
MESES = {nombre: i for i, nombre in enumerate(NOMBRES, start=1)}
MESES["septiembre"] = 9
PATRON_ENLACE = re.compile(
    r"/informes-publicaciones/\d+-reporte-de-denuncias-registradas-en-el-sidpol-"
    r"a-([a-z]+)-(?:del-)?(\d{4})"
)
PATRON_ARCHIVO = re.compile(r"sidpol-a-([a-z]+)-(?:del-)?(\d{4})")


@dataclass(frozen=True)
class ReporteSidpol:
    anio: int
    mes: int
    url: str

    @property
    def etiqueta(self) -> str:
        return f"{NOMBRES[self.mes - 1]} de {self.anio}"


def extraer_reportes(html: str) -> list[ReporteSidpol]:
    """Reportes SIDPOL de una página del listado, del más nuevo al más antiguo."""
    soup = BeautifulSoup(html, "html.parser")
    por_mes = {}
    for enlace in soup.find_all("a", href=True):
        coincidencia = PATRON_ENLACE.search(enlace["href"])
        if coincidencia and coincidencia.group(1) in MESES:
            clave = (int(coincidencia.group(2)), MESES[coincidencia.group(1)])
            por_mes.setdefault(clave, BASE + enlace["href"] if enlace["href"].startswith("/") else enlace["href"])
    ordenados = sorted(por_mes.items(), reverse=True)
    return [ReporteSidpol(anio, mes, url) for (anio, mes), url in ordenados]


def ultimo_reporte(hojas: int = 3):
    """El reporte más reciente entre las primeras hojas del listado, o None si no se pudo consultar."""
    reportes = []
    for hoja in range(1, hojas + 1):
        url = COLECCION if hoja == 1 else f"{COLECCION}?sheet={hoja}"
        try:
            respuesta = requests.get(url, timeout=30, headers=CABECERAS)
            respuesta.raise_for_status()
        except requests.RequestException:
            continue
        reportes += extraer_reportes(respuesta.text)
    if not reportes:
        return None
    return max(reportes, key=lambda r: (r.anio, r.mes))


def periodo_en_uso(nombre_archivo: str):
    """(año, mes) del reporte que usa el sistema, leído del nombre del archivo descargado."""
    coincidencia = PATRON_ARCHIVO.search(nombre_archivo)
    if coincidencia and coincidencia.group(1) in MESES:
        return int(coincidencia.group(2)), MESES[coincidencia.group(1)]
    return None


def url_pdf(reporte: ReporteSidpol) -> str:
    """Dirección del PDF de un reporte, leída de su ficha en gob.pe (solo si es el del SIDPOL)."""
    respuesta = requests.get(reporte.url, timeout=30, headers=CABECERAS)
    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")
    pdfs = [
        urljoin(BASE, a["href"]) for a in soup.find_all("a", href=True)
        if ".pdf" in a["href"].lower() and "sidpol" in a["href"].lower()
    ]
    if not pdfs:
        raise ValueError(f"La ficha del reporte de {reporte.etiqueta} no trae un PDF del SIDPOL.")
    return pdfs[0]
