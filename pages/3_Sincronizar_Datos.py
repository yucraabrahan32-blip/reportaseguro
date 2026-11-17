import streamlit as st

from backend.acceso import barra_lateral, es_admin
from backend.fuentes import sincronizar_todos
from backend.fuentes.novedades import NOMBRES, ultimo_reporte
from database import db

st.set_page_config(page_title="Sincronizar datos", page_icon="🔄", layout="wide")
barra_lateral()
st.title("🔄 Sincronizar datos oficiales")
st.write(
    "Descarga reportes del Ministerio del Interior (SIDPOL), extrae las denuncias por "
    "distrito (Lima y Callao) y por región (todo el país) y las guarda en la base de datos."
)


def etiqueta(corte):
    if not corte:
        return "sin datos"
    anio, mes = corte.split("-")
    return f"{NOMBRES[int(mes) - 1]} de {anio}"


def como_tupla(corte):
    return tuple(int(x) for x in corte.split("-")) if corte else None


if es_admin():
    if st.button("Sincronizar ahora", type="primary"):
        with st.spinner("Descargando y procesando los reportes..."):
            resultados, errores = sincronizar_todos()
        for resultado in resultados:
            st.success(f"{resultado.fuente}: {resultado.filas_guardadas} registros guardados.")
            if resultado.advertencias:
                with st.expander(f"{len(resultado.advertencias)} advertencia(s): {resultado.fuente}"):
                    for aviso in resultado.advertencias:
                        st.text(aviso)
        for nombre, error in errores:
            st.error(f"{nombre}: no se pudo sincronizar ({error})")
else:
    st.info("Solo un administrador puede sincronizar. Inicia sesión en la página Administracion.")

cortes = db.cortes_cargados()
c1, c2 = st.columns(2)
c1.metric("Datos por distrito (Lima y Callao)", etiqueta(cortes["distrital"]))
c2.metric("Datos por región (todo el país)", etiqueta(cortes["regional"]))
st.caption(
    "Cada conjunto de datos tiene su propio mes de corte y las cifras son acumuladas de "
    "enero a ese mes. Las cifras de un mismo año pueden cambiar entre reportes porque el "
    "Mininter las revisa."
)

st.subheader("Reporte más reciente del Observatorio")
if st.button("Buscar reporte más reciente"):
    with st.spinner("Consultando gob.pe..."):
        st.session_state["reporte_reciente"] = ultimo_reporte()
        st.session_state["reporte_consultado"] = True

if st.session_state.get("reporte_consultado"):
    reciente = st.session_state.get("reporte_reciente")
    if reciente is None:
        st.warning("No se pudo consultar la página del Observatorio (¿sin internet?).")
    else:
        st.write(
            f"Reporte más reciente publicado: **{reciente.etiqueta}** "
            f"([abrir en gob.pe]({reciente.url}))"
        )
        ultimo = (reciente.anio, reciente.mes)
        regional, distrital = como_tupla(cortes["regional"]), como_tupla(cortes["distrital"])
        if regional == ultimo:
            st.success("Los datos por región usan el reporte más reciente.")
        elif regional is None or regional < ultimo:
            st.info("Hay un reporte más nuevo para las regiones: un administrador puede sincronizar.")
        if distrital is None or distrital < ultimo:
            st.info(
                f"Los datos por distrito siguen en {etiqueta(cortes['distrital'])}: las páginas "
                "por distrito del reporte nuevo cambiaron de formato y todavía no se cargan."
            )

ultima = db.ultima_sincronizacion()
if ultima:
    st.info(
        f"Última sincronización: {ultima['fecha']} | Fuente: {ultima['fuente']} | "
        f"Archivo: {ultima['archivo']} | Registros: {ultima['filas']}"
    )

st.subheader("Historial")
st.dataframe(db.historial_sincronizaciones(), width="stretch", hide_index=True)
