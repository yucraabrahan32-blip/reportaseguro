import plotly.express as px
import streamlit as st

from backend import servicio_regional as sr
from backend.acceso import barra_lateral
from backend.fuentes.novedades import NOMBRES
from database import db

st.set_page_config(page_title="Regiones", page_icon="📍", layout="wide")
barra_lateral()
st.title("📍 Denuncias por región")

df = db.denuncias_regionales_df()
if df.empty:
    st.warning("No hay datos regionales. Un administrador debe sincronizar en 'Sincronizar Datos'.")
    st.stop()

corte = df["corte"].dropna().max()
anio_corte, mes_corte = corte.split("-")
mes = NOMBRES[int(mes_corte) - 1]
st.caption(
    f"Cifras acumuladas de enero a {mes} de cada año (reporte con corte en {mes} de {anio_corte})."
)

col1, col2 = st.columns(2)
periodo = col1.selectbox(
    "Año", sorted(df["periodo"].unique(), reverse=True),
    format_func=lambda p: f"Enero a {mes} de {p}",
)
categoria = col2.selectbox("Categoría", ["Todas"] + sorted(df["categoria"].unique()))

datos = df[df["periodo"] == periodo]
if categoria != "Todas":
    datos = datos[datos["categoria"] == categoria]
totales = (
    datos.groupby("region", as_index=False)["cantidad"].sum()
    .sort_values("cantidad", ascending=False)
)

fig = px.bar(
    totales, x="cantidad", y="region", orientation="h",
    title=f"Denuncias por región (enero a {mes} de {periodo}, {categoria.lower()})",
)
fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=700)
st.plotly_chart(fig, width="stretch")

coords = sr.coordenadas_regiones(db.ubigeo_df(), totales["region"].tolist())
mapa = totales.merge(coords, on="region")
if mapa.empty:
    st.info("No se pudo ubicar las regiones. Carga el catálogo: python -m backend.ubigeo")
else:
    fig_mapa = px.scatter_map(
        mapa, lat="latitud", lon="longitud", size="cantidad", color="cantidad",
        hover_name="region", hover_data={"cantidad": True, "latitud": False, "longitud": False},
        size_max=45, zoom=4, color_continuous_scale="YlOrRd", map_style="open-street-map",
        title="Mapa por región",
    )
    st.plotly_chart(fig_mapa, width="stretch")

pivote = df.groupby(["region", "periodo"])["cantidad"].sum().unstack()
if {"2025", "2026"}.issubset(pivote.columns):
    pivote["variacion_%"] = ((pivote["2026"] / pivote["2025"] - 1) * 100).round(1)
    st.subheader(f"Variación entre enero-{mes} de 2025 y de 2026")
    st.dataframe(
        pivote.sort_values("variacion_%").reset_index(), width="stretch", hide_index=True
    )
st.caption(
    "Cifras absolutas, no por habitante. Lima aparece dividida en Lima Metropolitana y "
    "Región Lima, como la publica la fuente. Los porcentajes se calculan aquí, no se copian "
    "del PDF. Cada burbuja se coloca en el promedio de las coordenadas de los distritos de "
    "la región, así que es una ubicación aproximada."
)
