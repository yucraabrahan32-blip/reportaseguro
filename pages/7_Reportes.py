import plotly.express as px
import streamlit as st

from backend.acceso import barra_lateral, es_admin
from backend.models import AnalizadorIncidentes
from database import db

st.set_page_config(page_title="Reportes", page_icon="📑", layout="wide")
barra_lateral()
st.title("📑 Reportes de incidentes ciudadanos")

datos = db.incidentes_df()
if datos.empty:
    st.info("Aún no hay reportes. Registra alguno en 'Reportar Incidente'.")
    st.stop()

col1, col2 = st.columns(2)
departamentos = sorted(datos["departamento"].dropna().unique())
departamento = col1.selectbox(
    "Departamento", ["Todos"] + departamentos,
    format_func=lambda x: x if x == "Todos" else x.title(),
)
tipo = col2.selectbox(
    "Tipo de incidente", ["Todos"] + sorted(datos["delito"].unique()),
    format_func=lambda x: x if x == "Todos" else x.capitalize(),
)

analisis = AnalizadorIncidentes(datos).filtrar(
    None if departamento == "Todos" else departamento,
    None if tipo == "Todos" else tipo,
)
if analisis.df.empty:
    st.info("No hay reportes con esos filtros.")
    st.stop()

franjas = analisis.por_franja()
m1, m2, m3 = st.columns(3)
m1.metric("Reportes", len(analisis.df))
m2.metric("Tipo más frecuente", analisis.por_tipo().iloc[0]["delito"].capitalize())
m3.metric("Franja más frecuente", franjas.sort_values("reportes", ascending=False).iloc[0]["franja"])

g1, g2 = st.columns(2)
g1.plotly_chart(
    px.bar(analisis.por_tipo(), x="delito", y="reportes", title="Reportes por tipo"),
    width="stretch",
)
g2.plotly_chart(
    px.bar(franjas, x="franja", y="reportes", title="Reportes por franja horaria"),
    width="stretch",
)
st.plotly_chart(
    px.bar(analisis.por_hora(), x="hora", y="reportes", title="Reportes por hora del día"),
    width="stretch",
)

st.subheader("Distritos con más reportes")
st.dataframe(analisis.por_distrito(), width="stretch", hide_index=True)

if es_admin():
    st.download_button(
        "Descargar reportes (CSV)",
        data=analisis.df.drop(columns=["hora"]).to_csv(index=False).encode("utf-8-sig"),
        file_name="reportes_ciudadanos.csv",
        mime="text/csv",
    )
else:
    st.caption("La descarga del CSV es solo para administradores.")
st.caption(
    "Los gráficos son agregados y no incluyen descripciones. Con pocos reportes sirven para "
    "ver que el sistema funciona, no para sacar conclusiones."
)
