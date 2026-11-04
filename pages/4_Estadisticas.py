import plotly.express as px
import streamlit as st

from backend import services
from database import db
from backend.ubigeo import ALIAS, normalizar

st.set_page_config(page_title="Estadísticas", page_icon="📊", layout="wide")
st.title("📊 Riesgo por distrito")

oficial = db.denuncias_oficiales_df()
if oficial.empty:
    st.warning("No hay datos oficiales. Ve a la página 'Sincronizar Datos'.")
    st.stop()

periodos = sorted(oficial["periodo"].unique())
periodo = st.selectbox(
    "Periodo", periodos, index=periodos.index("2025") if "2025" in periodos else 0
)
if periodo == "2026-01":
    st.caption("Ojo: 2026-01 es solo un mes; no se compara con los años completos.")

riesgo = services.indice_riesgo(oficial, periodo)
if riesgo.empty:
    st.info("No hay datos para ese periodo.")
    st.stop()

ciudadanos = db.incidentes_df()


def clave(nombre) -> str:
    return ALIAS.get(normalizar(nombre), normalizar(nombre))


zona = ciudadanos[ciudadanos["provincia"].map(normalizar).isin({"LIMA", "CALLAO"})].copy()
zona["clave"] = zona["distrito"].map(clave)
conteo = zona.groupby("clave").size().rename("reportes_ciudadanos")
riesgo["clave"] = riesgo["distrito"].map(clave)
riesgo = riesgo.merge(conteo, on="clave", how="left").fillna({"reportes_ciudadanos": 0})
riesgo["reportes_ciudadanos"] = riesgo["reportes_ciudadanos"].astype(int)

col1, col2, col3 = st.columns(3)
col1.metric("Distritos analizados", len(riesgo))
col2.metric("En nivel Alto", int((riesgo["nivel"] == "Alto").sum()))
col3.metric("Reportes ciudadanos", len(ciudadanos))

top = riesgo.head(10)
fig = px.bar(
    top, x="puntaje", y="distrito", orientation="h", color="nivel",
    color_discrete_map={"Alto": "#d62728", "Medio": "#ff7f0e", "Bajo": "#2ca02c"},
    title=f"Top 10 distritos por puntaje de riesgo ({periodo})",
)
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, width="stretch")

st.subheader("Oficial vs. ciudadano")
st.dataframe(
    riesgo[["distrito", "HOMICIDIO", "ROBO", "HURTO", "indice", "nivel", "reportes_ciudadanos"]],
    width="stretch", hide_index=True,
)

st.subheader("🚨 Alertas: enero 2026 por encima del promedio mensual de 2025")
alertas = services.alertas_aumento(oficial)
if alertas.empty:
    st.success("No hay distritos que superen el umbral.")
else:
    st.dataframe(alertas, width="stretch", hide_index=True)

st.caption(
    "Puntaje = homicidio×10 + robo×3 + hurto×1. Son cifras absolutas, no por habitante, "
    "así que los distritos más poblados tienden a quedar arriba. Desde noviembre de 2024 la "
    "fuente no incluye las denuncias virtuales por robo y hurto."
)   