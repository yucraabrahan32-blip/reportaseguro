from datetime import date

import streamlit as st

from backend.models import DELITOS, Incidente, RepositorioIncidentes, Ubicacion
from database import db

repo = RepositorioIncidentes()
OPCIONES = list(DELITOS)

st.set_page_config(page_title="Reportar incidente", page_icon="📝", layout="wide")
st.title("📝 Reportar incidente")
st.caption("No escribas nombres, DNI ni teléfonos. Describe el hecho, no a las personas.")

if "aviso" in st.session_state:
    st.success(st.session_state.pop("aviso"))

departamentos = db.listar_departamentos()
if not departamentos:
    st.warning("Falta cargar el catálogo de ubigeo. Ejecuta: python -m backend.ubigeo")
    st.stop()

st.markdown("**Ubicación**")
col1, col2, col3 = st.columns(3)
departamento = col1.selectbox(
    "Departamento", departamentos, format_func=str.title,
    index=departamentos.index("LIMA") if "LIMA" in departamentos else 0,
)
provincias = db.listar_provincias(departamento)
provincia = col2.selectbox("Provincia", provincias, format_func=str.title)
distritos = db.listar_distritos_de(departamento, provincia)
distrito = col3.selectbox("Distrito", distritos, format_func=str.title)

with st.form("form_incidente", clear_on_submit=True):
    delito = st.selectbox("Tipo de incidente", OPCIONES, format_func=str.capitalize)
    fecha = st.date_input("Fecha del hecho", value=date.today(), max_value=date.today())
    hora = st.time_input("Hora aproximada")
    descripcion = st.text_area("Descripción", max_chars=500)
    enviado = st.form_submit_button("Enviar reporte")

if enviado:
    try:
        nuevo_id = repo.agregar(
            Incidente(
                ubicacion=Ubicacion(departamento, provincia, distrito or ""),
                delito=delito,
                fecha_hecho=fecha,
                hora_hecho=hora.strftime("%H:%M"),
                descripcion=descripcion,
            )
        )
    except ValueError as error:
        st.error(str(error))
    else:
        st.session_state["aviso"] = f"Reporte #{nuevo_id} registrado. Gracias por contribuir."
        st.rerun()

st.divider()
st.subheader("Gestionar reportes")

incidentes = repo.listar(limite=200)
if incidentes.empty:
    st.info("Todavía no hay reportes registrados.")
    st.stop()

st.dataframe(incidentes.head(10), width="stretch", hide_index=True)

seleccion = st.selectbox(
    "Selecciona un reporte para editar o eliminar",
    incidentes["id"].tolist(),
    format_func=lambda i: f"Reporte #{i}",
)
fila = incidentes[incidentes["id"] == seleccion].iloc[0]

st.markdown("**Editar** (la ubicación no se modifica; si te equivocaste de lugar, elimina y reporta de nuevo)")
with st.form(f"form_editar_{seleccion}"):
    ed_delito = st.selectbox(
        "Tipo de incidente", OPCIONES,
        index=OPCIONES.index(fila["delito"]) if fila["delito"] in OPCIONES else 0,
        format_func=str.capitalize,
    )
    ed_descripcion = st.text_area("Descripción", value=fila["descripcion"], max_chars=500)
    guardar = st.form_submit_button("Guardar cambios")

if guardar:
    try:
        actualizado = repo.actualizar(int(seleccion), ed_delito, ed_descripcion)
    except ValueError as error:
        st.error(str(error))
    else:
        if actualizado:
            st.session_state["aviso"] = f"Reporte #{seleccion} actualizado."
            st.rerun()
        else:
            st.error("No se pudo actualizar el reporte.")

st.markdown("**Eliminar**")
with st.form(f"form_eliminar_{seleccion}"):
    confirmar = st.checkbox("Confirmo que quiero eliminar este reporte")
    eliminar = st.form_submit_button("Eliminar reporte")

if eliminar:
    if not confirmar:
        st.error("Marca la casilla de confirmación para eliminar.")
    elif repo.eliminar(int(seleccion)):
        st.session_state["aviso"] = f"Reporte #{seleccion} eliminado."
        st.rerun()
    else:
        st.error("No se pudo eliminar el reporte.")