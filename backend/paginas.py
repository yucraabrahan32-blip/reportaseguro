"""Localiza páginas de un PDF por su contenido, para tolerar cambios de paginación."""
import pdfplumber


def localizar_pagina(ruta, marcas: list[str]) -> int:
    """Número (desde 1) de la primera página cuyo texto contiene todas las marcas."""
    with pdfplumber.open(ruta) as pdf:
        for n, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            if all(marca in texto for marca in marcas):
                return n
    raise ValueError(
        f"No se encontró una página con {marcas}. El formato del reporte pudo haber cambiado."
    )
