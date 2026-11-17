import plotly.express as px
import streamlit as st

from backend.acceso import barra_lateral, es_admin
from backend.fuentes.carga_asistida import PLANTILLA, CargaAsistidaCSV
from database import db

st.set_page_config(page_title="Indicadores externos", page_icon="🏛️", layout="wide")
barra_lateral()
st.title("🏛️ Indicadores de otras fuentes (INEI, ONG)")
st.write(
    "Cifras que otras instituciones ya publicaron. Cada dato se muestra con su fuente y su "
    "enlace. Estas fuentes no ofrecen descarga automática, así que un administrador las "
    "carga desde un archivo CSV."
)

if es_admin():
    with st.expander("Cargar un archivo CSV (solo administradores)"):
        st.download_button(
            "Descargar plantilla CSV", PLANTILLA,
            file_name="plantilla_indicadores.csv", mime="text/csv",
        )
        st.caption(
            "Columnas: ambito (nacional, region o distrito), lugar, indicador, periodo, valor y "
            "unidad. Usa punto decimal y no pongas separador de miles. Carga solo cifras que la "
            "fuente haya publicado y cita el enlace."
        )
        with st.form("carga_asistida"):
            archivo = st.file_uploader("Archivo CSV", type=["csv"])
            fuente = st.text_input("Nombre de la fuente (ej.: ENAPRES 2025)")
            entidad = st.text_input("Entidad que la publica (ej.: INEI)")
            tipo = st.selectbox(
                "Tipo de fuente", ["estatal", "ong"],
                format_func=lambda t: "Estatal" if t == "estatal" else "ONG",
            )
            url = st.text_input("Enlace donde se publica el dato (https://...)")
            enviar = st.form_submit_button("Cargar")
        if enviar:
            if archivo is None:
                st.error("Selecciona un archivo CSV.")
            else:
                try:
                    resultado = CargaAsistidaCSV(archivo.getvalue(), fuente, entidad, tipo, url).sincronizar()
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success(f"{resultado.filas_guardadas} indicadores guardados de {fuente}.")
                    if resultado.advertencias:
                        with st.expander(f"{len(resultado.advertencias)} advertencia(s)"):
                            for aviso in resultado.advertencias:
                                st.text(aviso)

datos = db.indicadores_df()
if datos.empty:
    st.info("Aún no hay indicadores cargados.")
    st.stop()

indicador = st.selectbox("Indicador", sorted(datos["indicador"].unique()))
sub = datos[datos["indicador"] == indicador]
periodo = st.selectbox("Periodo", sorted(sub["periodo"].unique(), reverse=True))
sub = sub[sub["periodo"] == periodo].sort_values("valor", ascending=False)

if sub["unidad"].nunique() > 1:
    st.warning("Este indicador tiene más de una unidad de medida: no compares las barras entre sí.")
unidad = sub["unidad"].iloc[0]

fig = px.bar(
    sub, x="valor", y="lugar", orientation="h", color="fuente",
    title=f"{indicador} ({periodo}, {unidad})",
)
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, width="stretch")

st.dataframe(
    sub[["ambito", "lugar", "valor", "unidad", "fuente", "entidad", "tipo"]],
    width="stretch", hide_index=True,
)
for _, f in sub.drop_duplicates("fuente").iterrows():
    st.caption(
        f"Fuente: {f['fuente']} ({f['entidad']}, {'ONG' if f['tipo'] == 'ong' else 'estatal'}). "
        f"Enlace: {f['url']}. Cargado el {f['fecha_descarga'][:10]}."
    )
st.caption(
    "Estos datos se cargan manualmente y no están verificados por el sistema. Los indicadores "
    "pueden tener metodologías distintas a las del SIDPOL: no se suman ni se comparan con "
    "las denuncias."
)
