import streamlit as st

from backend.fuentes import sincronizar_todos
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
        resultados, errores = sincronizar_todos()
    for resultado in resultados:
        st.success(f"{resultado.fuente}: {resultado.filas_guardadas} registros guardados.")
        if resultado.advertencias:
            with st.expander(f"{len(resultado.advertencias)} advertencia(s): {resultado.fuente}"):
                for aviso in resultado.advertencias:
                    st.text(aviso)
    for nombre, error in errores:
        st.error(f"{nombre}: no se pudo sincronizar ({error})")

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
