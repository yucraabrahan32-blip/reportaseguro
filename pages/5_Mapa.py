import plotly.express as px
import streamlit as st

from backend.ubigeo import ALIAS, normalizar
from database import db

st.set_page_config(page_title="Mapa", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa de incidentes")

capa = st.radio(
    "Capa",
    ["Denuncias oficiales (Lima y Callao)", "Reportes ciudadanos (todo el Perú)"],
    horizontal=True,
)

if capa.startswith("Denuncias"):
    oficial = db.denuncias_oficiales_df()
    catalogo = db.ubigeo_df()
    if oficial.empty or catalogo.empty:
        st.warning(
            "Faltan datos. Sincroniza los datos oficiales y carga el catálogo "
            "(python -m backend.ubigeo)."
        )
        st.stop()

    col1, col2 = st.columns(2)
    periodos = sorted(oficial["periodo"].unique())
    periodo = col1.selectbox(
        "Periodo", periodos, index=periodos.index("2025") if "2025" in periodos else 0
    )
    delito = col2.selectbox("Delito", sorted(oficial["delito"].unique()), format_func=str.capitalize)
    if periodo == "2026-01":
        st.caption("Ojo: 2026-01 es solo un mes; no es comparable con los años completos.")

    datos = oficial[(oficial["periodo"] == periodo) & (oficial["delito"] == delito)].copy()
    datos["clave"] = datos["distrito"].map(lambda d: ALIAS.get(normalizar(d), normalizar(d)))
    zona = catalogo[catalogo["provincia"].map(normalizar).isin({"LIMA", "CALLAO"})]
    mapa = datos.merge(zona, left_on="clave", right_on="nombre_norm", how="inner",
                       suffixes=("_pdf", ""))

    if mapa.empty:
        st.info("No hay datos para esa combinación.")
        st.stop()
    if len(mapa) < len(datos):
        st.caption(f"{len(datos) - len(mapa)} distrito(s) no se pudieron ubicar en el mapa.")

    fig = px.scatter_map(
        mapa, lat="latitud", lon="longitud", size="cantidad", color="cantidad",
        hover_name="distrito", hover_data={"cantidad": True, "latitud": False, "longitud": False},
        size_max=40, zoom=9, color_continuous_scale="YlOrRd", map_style="open-street-map",
        title=f"Denuncias de {delito.lower()} por distrito ({periodo})",
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Cifras absolutas del SIDPOL (Mininter), no por habitante. Cada burbuja se ubica en "
        "la coordenada del distrito. Desde noviembre de 2024 la fuente no incluye las "
        "denuncias virtuales por robo y hurto."
    )

else:
    puntos = db.incidentes_con_coordenadas()
    if puntos.empty:
        st.info("Aún no hay reportes ciudadanos con ubicación. Registra alguno en 'Reportar Incidente'.")
        st.stop()

    agrupado = (
        puntos.groupby(["departamento", "provincia", "distrito", "latitud", "longitud"])
        .size().reset_index(name="reportes")
    )
    fig = px.scatter_map(
        agrupado, lat="latitud", lon="longitud", size="reportes", color="reportes",
        hover_name="distrito",
        hover_data={"departamento": True, "provincia": True, "reportes": True,
                    "latitud": False, "longitud": False},
        size_max=35, zoom=4.5, color_continuous_scale="Reds", map_style="open-street-map",
        title="Reportes ciudadanos por distrito",
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Los reportes se agrupan por distrito y se dibujan en la coordenada del distrito, "
        "no en el lugar exacto del hecho. Con pocos reportes conviene leerlo como un conteo, "
        "no como un mapa de calor."
    )