import streamlit as st

from backend import servicio_regional, services
from database import db

st.set_page_config(page_title="Sincronizar datos", page_icon="🔄", layout="wide")
st.title("🔄 Sincronizar datos oficiales")
st.write(
    "Descarga el reporte del Ministerio del Interior (SIDPOL), extrae las denuncias "
    "por distrito (Lima y Callao) y por región (todo el país) y las guarda en la base "
    "de datos con su fuente y fecha."
)

if st.button("Sincronizar ahora", type="primary"):
    with st.spinner("Descargando y procesando el reporte..."):
        try:
            distrital = services.sincronizar_sidpol()
            regional = servicio_regional.sincronizar_regional()
        except Exception as error:
            st.error(f"No se pudo sincronizar: {error}")
        else:
            st.success(
                f"Sincronización completa: {distrital['filas_guardadas']} registros distritales "
                f"y {regional['filas_guardadas']} regionales ({regional['regiones']} regiones)."
            )
            if regional["rechazadas"]:
                st.warning(
                    "Regiones descartadas por no pasar las validaciones: "
                    + ", ".join(r for r, _ in regional["rechazadas"])
                )

ultima = db.ultima_sincronizacion()
if ultima:
    st.info(
        f"Última sincronización: {ultima['fecha']} | Fuente: {ultima['fuente']} | "
        f"Archivo: {ultima['archivo']} | Registros: {ultima['filas']}"
    )
else:
    st.warning("Aún no se ha sincronizado ninguna fuente.")

st.subheader("Historial")
st.dataframe(db.historial_sincronizaciones(), width="stretch", hide_index=True)
