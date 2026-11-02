from datetime import date

import streamlit as st

from database import db

st.set_page_config(page_title="Reportar incidente", page_icon="📝", layout="wide")
st.title("📝 Reportar incidente")
st.caption("No escribas nombres, DNI ni teléfonos. Describe el hecho, no a las personas.")

distritos = db.listar_distritos()
if not distritos:
    st.warning("Aún no hay datos oficiales cargados. Ejecuta primero: python -m backend.services")
    st.stop()

DELITOS = ["ROBO", "HURTO", "HOMICIDIO", "OTRO"]

with st.form("form_incidente", clear_on_submit=True):
    distrito = st.selectbox("Distrito", distritos)
    delito = st.selectbox("Tipo de incidente", DELITOS, format_func=str.capitalize)
    fecha = st.date_input("Fecha del hecho", value=date.today(), max_value=date.today())
    hora = st.time_input("Hora aproximada")
    descripcion = st.text_area("Descripción", max_chars=500)
    enviado = st.form_submit_button("Enviar reporte")

if enviado:
    if len(descripcion.strip()) < 10:
        st.error("La descripción debe tener al menos 10 caracteres.")
    else:
        nuevo_id = db.guardar_incidente(
            distrito, delito, fecha.isoformat(), hora.strftime("%H:%M"), descripcion
        )
        st.success(f"Reporte #{nuevo_id} registrado. Gracias por contribuir.")

st.subheader("Últimos reportes")
st.dataframe(db.listar_incidentes(), use_container_width=True, hide_index=True)