"""Lógica de negocio. Por ahora: sincronización de datos oficiales."""
from backend.conectores import (
    CORRECCIONES, URL_SIDPOL, aplicar_correcciones, descargar_pdf, extraer_distritos,
)
from database import db


def sincronizar_sidpol() -> dict:
    archivo = descargar_pdf(URL_SIDPOL)
    df, dudosas = extraer_distritos(archivo, 30, ["HOMICIDIO", "HURTO", "ROBO"])
    df = aplicar_correcciones(df, CORRECCIONES)
    filas = db.guardar_denuncias_oficiales(df, "SIDPOL - Mininter", URL_SIDPOL, archivo.name)
    return {"filas_guardadas": filas, "lineas_dudosas": len(dudosas)}


if __name__ == "__main__":
    print(sincronizar_sidpol())
    con = db.conectar()
    try:
        consulta = (
            "SELECT distrito, cantidad FROM denuncias_oficiales "
            "WHERE delito = 'ROBO' AND periodo = '2025' ORDER BY cantidad DESC LIMIT 5"
        )
        for fila in con.execute(consulta):
            print(fila)
    finally:
        con.close() 