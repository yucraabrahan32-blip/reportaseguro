"""Página de inicio: explica la finalidad de la app y lleva a las dos acciones principales."""
import pandas as pd
import streamlit as st

from backend.acceso import es_admin
from database import db

URL_OBSERVATORIO = (
    "https://www.gob.pe/institucion/mininter/colecciones/"
    "13872-reportes-del-observatorio-nacional-de-seguridad-ciudadana"
)
URL_INEI = "https://m.inei.gob.pe/estadisticas/indice-tematico/seguridad-ciudadana"
URL_REPOSITORIO = "https://github.com/yucraabrahan32-blip/reportaseguro"
REDES = {"GitHub": URL_REPOSITORIO}


def _tabla(funcion) -> pd.DataFrame:
    try:
        return funcion()
    except Exception:
        return pd.DataFrame()


def _ultima_sync():
    try:
        return db.ultima_sincronizacion()
    except Exception:
        return None


ciudadanos = _tabla(db.incidentes_df)
oficial = _tabla(db.denuncias_oficiales_df)
regional = _tabla(db.denuncias_regionales_df)
ultima = _ultima_sync()

# ---------- Encabezado ----------
st.title("🛡️ ReportaSeguro")
st.subheader("Mapa y registro de incidentes de seguridad ciudadana")
st.write(
    "Une dos fuentes: las **denuncias oficiales** del Ministerio del Interior, que el "
    "sistema descarga y procesa por su cuenta, y los **reportes de los vecinos**. Con "
    "ambas calcula un índice de riesgo, genera alertas y muestra mapas por distrito y región."
)

# ---------- Acciones principales ----------
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("#### 📝 ¿Viste algo?")
        st.write("Registra un incidente de forma anónima. No hace falta crear una cuenta.")
        st.page_link("vistas/reportar.py", label="Reportar un incidente", icon="📝")
with col2:
    with st.container(border=True):
        st.markdown("#### 🗺️ ¿Qué tan segura está tu zona?")
        st.write("Mira el mapa, el riesgo por distrito y las cifras por región.")
        st.page_link("vistas/consultar.py", label="Consultar el riesgo", icon="🗺️")

st.info(
    "Si es una emergencia, llama a la Policía Nacional al 105. Esta herramienta no reemplaza "
    "la denuncia policial: sirve para registrar y visualizar información."
)

# ---------- Cifras del sistema ----------
st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Reportes ciudadanos", len(ciudadanos))
m2.metric("Distritos con cifras oficiales", oficial["distrito"].nunique() if not oficial.empty else 0)
m3.metric("Regiones con cifras oficiales", regional["region"].nunique() if not regional.empty else 0)
m4.metric("Última sincronización", ultima["fecha"][:10] if ultima else "Sin datos")
if not ultima and es_admin():
    st.page_link("vistas/sincronizar.py", label="Sincronizar datos oficiales", icon="🔄")

# ---------- Cómo funciona ----------
st.divider()
st.subheader("Cómo funciona")
c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("**1. Se leen los datos oficiales**")
        st.write("El sistema descarga el reporte SIDPOL del Mininter y extrae las denuncias por distrito y región.")
with c2:
    with st.container(border=True):
        st.markdown("**2. Los vecinos reportan**")
        st.write("Cualquier persona registra un incidente indicando dónde ocurrió.")
with c3:
    with st.container(border=True):
        st.markdown("**3. Se cruzan y se visualizan**")
        st.write("Se calcula un índice de riesgo, se detectan aumentos y se dibujan mapas.")

with st.expander("Límites de los datos"):
    st.write(
        "- Las cifras oficiales son absolutas, no por habitante.\n"
        "- El detalle por distrito existe solo para Lima Metropolitana y el Callao; "
        "para el resto del país hay cifras por región.\n"
        "- Desde noviembre de 2024 la fuente no incluye las denuncias virtuales de robo y hurto.\n"
        "- Los reportes ciudadanos no están verificados."
    )

# ---------- Pie de página ----------
st.divider()
cA, cB = st.columns(2)
with cA:
    st.markdown("**Equipo (Grupo 07)**")

with cB:
    st.markdown("**Fuentes y enlaces**")
    st.markdown(f"[Observatorio Nacional de Seguridad Ciudadana]({URL_OBSERVATORIO})")
    st.markdown(f"[INEI: seguridad ciudadana]({URL_INEI})")
    for nombre, enlace in REDES.items():
        st.markdown(f"[{nombre}]({enlace})")
st.caption("Proyecto final de Lenguajes de Programación · Universidad Tecnológica del Perú · 2026")
