"""Administración: inicio de sesión y panel del administrador.

Único punto de acceso para el personal autorizado. El ciudadano no necesita entrar aquí.
"""
import streamlit as st

from backend.acceso import CLAVE_SESION, cerrar_sesion, es_admin, intentar_login
from database import usuarios

st.title("🔐 Administración")

if es_admin():
    st.success(f"Sesión iniciada como {st.session_state[CLAVE_SESION]}.")
    st.write("Como administrador puedes:")
    st.page_link("vistas/reportar.py", label="Ver, editar y eliminar reportes", icon="📝")
    st.page_link("vistas/sincronizar.py", label="Sincronizar los datos oficiales", icon="🔄")
    st.page_link("vistas/reportes.py", label="Descargar los reportes en CSV", icon="📑")
    st.page_link("vistas/consultar.py", label="Cargar indicadores de otras fuentes", icon="🏛️")
    if st.button("Cerrar sesión"):
        cerrar_sesion()
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
    intentar_login(usuario, clave)
