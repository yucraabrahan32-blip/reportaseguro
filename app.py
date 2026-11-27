"""Punto de entrada y enrutador de ReportaSeguro.

Define el menú con st.navigation. El ciudadano ve tres opciones (Inicio, Reportar
y Consultar el riesgo); las páginas de administración aparecen solo con sesión
iniciada. Al usar st.navigation, Streamlit ignora el descubrimiento automático de
la carpeta pages/, así que todo el menú se arma aquí.
"""
import streamlit as st

from backend.acceso import es_admin, sesion_en_barra
from vistas.estilo import aplicar_estilo

st.set_page_config(page_title="ReportaSeguro", page_icon="🛡️", layout="wide", initial_sidebar_state="")
aplicar_estilo()

# ---------- Páginas públicas (todo ciudadano) ----------
INICIO = st.Page("vistas/inicio.py", title="Inicio", icon="🏠", default=True)
REPORTAR = st.Page("vistas/reportar.py", title="Reportar un incidente", icon="📝")
CONSULTAR = st.Page("vistas/consultar.py", title="Consultar el riesgo", icon="🗺️")

# ---------- Páginas de administración ----------
ADMINISTRACION = st.Page("vistas/administracion.py", title="Administración", icon="🔐")
SINCRONIZAR = st.Page("vistas/sincronizar.py", title="Sincronizar datos", icon="🔄")
REPORTES = st.Page("vistas/reportes.py", title="Reportes", icon="📑")


def construir_navegacion() -> dict:
    """Arma el menú según haya o no sesión de administrador."""
    publicas = [INICIO, REPORTAR, CONSULTAR]
    if es_admin():
        return {
            "Menú": publicas,
            "Administración": [SINCRONIZAR, REPORTES, ADMINISTRACION],
        }
    return {
        "Menú": publicas,
        "Acceso": [ADMINISTRACION],
    }


# ---------- Barra lateral: marca y sesión ----------
with st.sidebar:
    st.markdown("### 🛡️ ReportaSeguro")
    st.caption("Grupo 07 · Lenguajes de Programación · UTP")

pagina = st.navigation(construir_navegacion())
sesion_en_barra()
pagina.run()
