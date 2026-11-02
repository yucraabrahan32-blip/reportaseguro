import streamlit as st

from backend import services
from database import db

st.set_page_config(page_title="Sincronizar datos", page_icon="🔄", layout="wide")
st.title("🔄 Sincronizar datos oficiales")
st.write(
    "Descarga el reporte del Ministerio del Interior (SIDPOL), extrae las denuncias "
    "por distrito y las guarda en la base de datos con su fuente y fecha."
)

if st.button("Sincronizar ahora", type="primary"):
    with st.spinner("Descargando y procesando el reporte..."):
        try:
            resultado = services.sincronizar_sidpol()
        except Exception as error:
            st.error(f"No se pudo sincronizar: {error}")
        else:
            st.success(f"Sincronización completa: {resultado['filas_guardadas']} registros guardados.")
            st.caption(
                f"Líneas del PDF descartadas por no poder leerse: {resultado['lineas_dudosas']}. "
                "Algunas son notas al pie; otras requieren revisión manual."
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