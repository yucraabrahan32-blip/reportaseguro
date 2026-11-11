import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from backend.ubigeo import ALIAS, normalizar
from database import db

st.set_page_config(page_title="Mapa", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapa de incidentes")
st.caption(
    "Combina dos fuentes: las **denuncias oficiales** del SIDPOL (Lima y Callao) "
    "y los **reportes ciudadanos** (todo el Perú)."
)

# ---------- Cargar datos ----------
oficial = db.denuncias_oficiales_df()
catalogo = db.ubigeo_df()
ciudadanos = db.incidentes_con_coordenadas()

sin_datos = oficial.empty or catalogo.empty
if sin_datos:
    st.warning(
        "Faltan datos oficiales. Ve a **Sincronizar Datos** y luego ejecuta "
        "`python -m backend.ubigeo` para cargar el catálogo."
    )

# ---------- Filtros ----------
col1, col2, col3 = st.columns(3)

periodos = sorted(oficial["periodo"].unique()) if not oficial.empty else ["2025"]
periodo = col1.selectbox(
    "Periodo", periodos,
    index=periodos.index("2025") if "2025" in periodos else 0
)
if periodo == "2026-01":
    col1.caption("⚠️ Solo un mes, no comparable con años completos.")

delitos = sorted(oficial["delito"].unique()) if not oficial.empty else []
delito = col2.selectbox("Delito", ["Todos"] + delitos, format_func=str.capitalize)

modo = col3.radio("Vista", ["🔵 Burbujas", "🔥 Mapa de calor"], horizontal=True)

# ---------- Preparar datos oficiales ----------
zona_ubigeo = catalogo[
    catalogo["provincia"].map(normalizar).isin({"LIMA", "CALLAO"})
] if not catalogo.empty else pd.DataFrame()

if not oficial.empty and not zona_ubigeo.empty:
    datos_of = oficial[oficial["periodo"] == periodo].copy()
    if delito != "Todos":
        datos_of = datos_of[datos_of["delito"] == delito]

    # Sumar por distrito si hay varios delitos
    datos_of = datos_of.groupby("distrito", as_index=False)["cantidad"].sum()
    datos_of["clave"] = datos_of["distrito"].map(
        lambda d: ALIAS.get(normalizar(d), normalizar(d))
    )
    mapa_of = datos_of.merge(
        zona_ubigeo, left_on="clave", right_on="nombre_norm", how="inner",
        suffixes=("_pdf", "")
    )
else:
    mapa_of = pd.DataFrame()

# ---------- Preparar datos ciudadanos ----------
if not ciudadanos.empty:
    ciud_agrup = (
        ciudadanos
        .groupby(["departamento", "provincia", "distrito", "latitud", "longitud"])
        .size().reset_index(name="reportes")
    )
else:
    ciud_agrup = pd.DataFrame()

# ---------- Construir mapa Folium ----------
mapa = folium.Map(location=[-12.05, -77.05], zoom_start=10, tiles="OpenStreetMap")

# -- Capa oficial --
capa_oficial = folium.FeatureGroup(name="🔴 Denuncias oficiales SIDPOL (Lima y Callao)", show=True)

if not mapa_of.empty:
    max_cant = mapa_of["cantidad"].max()

    if modo == "🔵 Burbujas":
        for _, fila in mapa_of.iterrows():
            radio = max(5, int((fila["cantidad"] / max_cant) * 35))
            # Color según intensidad
            if fila["cantidad"] / max_cant >= 0.66:
                color = "#d62728"   # rojo — alto
            elif fila["cantidad"] / max_cant >= 0.33:
                color = "#ff7f0e"   # naranja — medio
            else:
                color = "#2ca02c"   # verde — bajo

            folium.CircleMarker(
                location=[fila["latitud"], fila["longitud"]],
                radius=radio,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.65,
                popup=folium.Popup(
                    f"<b>{fila['distrito'].title()}</b><br>"
                    f"Delito: {delito if delito != 'Todos' else 'Todos'}<br>"
                    f"Denuncias: <b>{int(fila['cantidad']):,}</b><br>"
                    f"Periodo: {periodo}",
                    max_width=200,
                ),
                tooltip=f"{fila['distrito'].title()}: {int(fila['cantidad']):,} denuncias",
            ).add_to(capa_oficial)

    else:  # Heatmap
        heat_data = [
            [fila["latitud"], fila["longitud"], fila["cantidad"]]
            for _, fila in mapa_of.iterrows()
        ]
        HeatMap(
            heat_data,
            min_opacity=0.3,
            radius=25,
            blur=20,
            gradient={0.2: "blue", 0.5: "yellow", 0.8: "orange", 1.0: "red"},
        ).add_to(capa_oficial)

capa_oficial.add_to(mapa)

# -- Capa ciudadana --
capa_ciudadana = folium.FeatureGroup(name="🟡 Reportes ciudadanos (todo el Perú)", show=True)

if not ciud_agrup.empty:
    for _, fila in ciud_agrup.iterrows():
        folium.CircleMarker(
            location=[fila["latitud"], fila["longitud"]],
            radius=max(5, int(fila["reportes"] * 4)),
            color="#f5a623",
            fill=True,
            fill_color="#f5a623",
            fill_opacity=0.8,
            popup=folium.Popup(
                f"<b>{fila['distrito'].title()}</b><br>"
                f"{fila['provincia'].title()}, {fila['departamento'].title()}<br>"
                f"Reportes ciudadanos: <b>{int(fila['reportes'])}</b>",
                max_width=200,
            ),
            tooltip=f"{fila['distrito'].title()}: {int(fila['reportes'])} reporte(s) ciudadano(s)",
        ).add_to(capa_ciudadana)

capa_ciudadana.add_to(mapa)

# Control de capas (toggle arriba a la derecha)
folium.LayerControl(collapsed=False).add_to(mapa)

# Leyenda
leyenda_html = """
<div style="
    position: fixed; bottom: 30px; left: 30px; z-index: 1000;
    background-color: white; padding: 10px 14px; border-radius: 8px;
    border: 1px solid #ccc; font-size: 13px; line-height: 1.8;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
">
    <b>Leyenda</b><br>
    <span style="color:#d62728;">●</span> Alto riesgo (oficial)<br>
    <span style="color:#ff7f0e;">●</span> Riesgo medio (oficial)<br>
    <span style="color:#2ca02c;">●</span> Bajo riesgo (oficial)<br>
    <span style="color:#f5a623;">●</span> Reporte ciudadano
</div>
"""
mapa.get_root().html.add_child(folium.Element(leyenda_html))

# ---------- Mostrar ----------
st_folium(mapa, width="100%", height=560, returned_objects=[])

# ---------- Métricas ----------
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Distritos con datos oficiales", len(mapa_of) if not mapa_of.empty else 0)
m2.metric("Total denuncias oficiales", f"{int(mapa_of['cantidad'].sum()):,}" if not mapa_of.empty else "0")
m3.metric("Reportes ciudadanos", len(ciudadanos) if not ciudadanos.empty else 0)

# ---------- Notas ----------
st.caption(
    "🔴 Datos oficiales: SIDPOL (Mininter) — solo cubren Lima Metropolitana y Callao a nivel distrito. "
    "Cifras absolutas, no por habitante. Desde noviembre 2024 no incluyen denuncias virtuales de robo y hurto. "
    "🟡 Reportes ciudadanos: registrados en esta app, no verificados, ubicados en el centro del distrito."
)
