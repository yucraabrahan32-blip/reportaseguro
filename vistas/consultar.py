"""Consultar el riesgo: reúne mapa, estadísticas, regiones e indicadores en pestañas.

Antes eran cuatro páginas sueltas en el menú. Son distintas maneras de mirar lo mismo
—qué tan peligrosa está una zona—, así que se agrupan aquí en un solo módulo.
"""
import streamlit as st

from vistas import paneles

st.title("🗺️ Consultar el riesgo")
st.caption("Explora la situación de seguridad desde distintos ángulos.")

tab_mapa, tab_stats, tab_regiones, tab_indicadores = st.tabs(
    ["🗺️ Mapa", "📊 Riesgo por distrito", "📍 Regiones", "🏛️ Indicadores externos"]
)

with tab_mapa:
    paneles.mapa()
with tab_stats:
    paneles.estadisticas()
with tab_regiones:
    paneles.regiones()
with tab_indicadores:
    paneles.indicadores()
