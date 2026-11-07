"""Exploración temporal de las páginas regionales del PDF SIDPOL."""
import pdfplumber

from backend.conectores import URL_SIDPOL, descargar_pdf

PAGINAS = [8, 13, 14, 20, 21]


def es_cuadricula(tabla) -> bool:
    """Descarta la cuadrícula numerada de la plantilla del PDF."""
    if len(tabla) < 2:
        return False
    celdas = [c for c in tabla[1] if c not in (None, "")]
    return len(celdas) >= 10 and all(c.isdigit() and int(c) <= 32 for c in celdas)


if __name__ == "__main__":
    ruta = descargar_pdf(URL_SIDPOL)
    with pdfplumber.open(ruta) as pdf:
        for n in PAGINAS:
            pagina = pdf.pages[n - 1]
            print(f"\n===== Página {n} =====")
            tablas = [t for t in pagina.extract_tables() if not es_cuadricula(t)]
            print(f"Tablas de datos: {len(tablas)}")
            for tabla in tablas:
                for fila in tabla[:6]:
                    print("   ", fila)
            texto = pagina.extract_text() or ""
            print("--- texto ---")
            print("\n".join(texto.splitlines()[:25]))
