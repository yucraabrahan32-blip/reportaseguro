import streamlit as st

from backend.acceso import CLAVE_SESION, es_admin
from database import usuarios

st.set_page_config(page_title="Administración", page_icon="🔐", layout="wide")
st.title("🔐 Administración")

if es_admin():
    st.success(f"Sesión iniciada como {st.session_state[CLAVE_SESION]}.")
    st.write("Como administrador puedes:")
    st.page_link("pages/2_Reportar_Incidente.py", label="Ver, editar y eliminar reportes", icon="📝")
    st.page_link("pages/3_Sincronizar_Datos.py", label="Sincronizar los datos oficiales", icon="🔄")
    st.page_link("pages/7_Reportes.py", label="Descargar los reportes en CSV", icon="📑")
    if st.button("Cerrar sesión"):
        st.session_state.pop(CLAVE_SESION, None)
        st.rerun()
    st.stop()

st.write("Solo el personal autorizado necesita iniciar sesión. Para reportar un incidente no hace falta.")
if not usuarios.hay_admins():
    st.warning("No hay administradores. Crea uno con: python -m backend.crear_admin")
    st.stop()

with st.form("login_admin_pagina"):
    usuario = st.text_input("Usuario")
    clave = st.text_input("Clave", type="password")
    entrar = st.form_submit_button("Entrar")

if entrar:
    if usuarios.verificar(usuario, clave):
        st.session_state[CLAVE_SESION] = usuario.strip().lower()
        st.rerun()
    else:
        st.error("Usuario o clave incorrectos.")
