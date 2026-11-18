"""Paneles de consulta: mapa, estadísticas, regiones e indicadores externos.

Cada función dibuja un panel pensado para vivir dentro de una pestaña de la página
"Consultar el riesgo". Por eso usan `return` (no `st.stop()`, que cortaría toda la
página) y claves de widget propias para no chocar entre sí.
"""
import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from backend import services
from backend import servicio_regional as sr
from backend.acceso import es_admin
from backend.fuentes.carga_asistida import PLANTILLA, CargaAsistidaCSV
from backend.fuentes.novedades import NOMBRES
from backend.ubigeo import ALIAS, normalizar
from database import db


def _clave_distrito(nombre) -> str:
    """Normaliza un nombre de distrito y aplica alias conocidos."""
    return ALIAS.get(normalizar(nombre), normalizar(nombre))


# ========================= MAPA =========================
def mapa() -> None:
    st.caption(
        "Combina dos fuentes: las **denuncias oficiales** del SIDPOL (Lima y Callao) "
        "y los **reportes ciudadanos** (todo el Perú)."
    )

    oficial = db.denuncias_oficiales_df()
    catalogo = db.ubigeo_df()
    ciudadanos = db.incidentes_con_coordenadas()

    if oficial.empty or catalogo.empty:
        st.warning(
            "Faltan datos oficiales. Un administrador debe sincronizar y cargar el "
            "catálogo de ubigeo (`python -m backend.ubigeo`)."
        )

    # --- Filtros ---
    col1, col2, col3 = st.columns(3)
    periodos = sorted(oficial["periodo"].unique()) if not oficial.empty else ["2025"]
    periodo = col1.selectbox(
        "Periodo", periodos,
        index=periodos.index("2025") if "2025" in periodos else 0,
        key="mapa_periodo",
    )
    if periodo == "2026-01":
        col1.caption("⚠️ Solo un mes, no comparable con años completos.")

    delitos = sorted(oficial["delito"].unique()) if not oficial.empty else []
    delito = col2.selectbox(
        "Delito", ["Todos"] + delitos, format_func=str.capitalize, key="mapa_delito"
    )
    modo = col3.radio("Vista", ["🔵 Burbujas", "🔥 Mapa de calor"], horizontal=True, key="mapa_modo")

    # --- Datos oficiales (Lima y Callao) ---
    zona_ubigeo = (
        catalogo[catalogo["provincia"].map(normalizar).isin({"LIMA", "CALLAO"})]
        if not catalogo.empty else pd.DataFrame()
    )
    if not oficial.empty and not zona_ubigeo.empty:
        datos_of = oficial[oficial["periodo"] == periodo].copy()
        if delito != "Todos":
            datos_of = datos_of[datos_of["delito"] == delito]
        datos_of = datos_of.groupby("distrito", as_index=False)["cantidad"].sum()
        datos_of["clave"] = datos_of["distrito"].map(_clave_distrito)
        mapa_of = datos_of.merge(
            zona_ubigeo, left_on="clave", right_on="nombre_norm", how="inner",
            suffixes=("_pdf", ""),
        )
    else:
        mapa_of = pd.DataFrame()

    # --- Datos ciudadanos ---
    if not ciudadanos.empty:
        ciud_agrup = (
            ciudadanos
            .groupby(["departamento", "provincia", "distrito", "latitud", "longitud"])
            .size().reset_index(name="reportes")
        )
    else:
        ciud_agrup = pd.DataFrame()

    # --- Construir el mapa ---
    lienzo = folium.Map(location=[-12.05, -77.05], zoom_start=10, tiles="OpenStreetMap")
    capa_oficial = folium.FeatureGroup(name="🔴 Denuncias oficiales SIDPOL (Lima y Callao)", show=True)

    if not mapa_of.empty:
        max_cant = mapa_of["cantidad"].max()
        if modo == "🔵 Burbujas":
            for _, fila in mapa_of.iterrows():
                proporcion = fila["cantidad"] / max_cant
                radio = max(5, int(proporcion * 35))
                if proporcion >= 0.66:
                    color = "#d62728"
                elif proporcion >= 0.33:
                    color = "#ff7f0e"
                else:
                    color = "#2ca02c"
                folium.CircleMarker(
                    location=[fila["latitud"], fila["longitud"]],
                    radius=radio, color=color, fill=True,
                    fill_color=color, fill_opacity=0.65,
                    popup=folium.Popup(
                        f"<b>{fila['distrito'].title()}</b><br>"
                        f"Delito: {delito if delito != 'Todos' else 'Todos'}<br>"
                        f"Denuncias: <b>{int(fila['cantidad']):,}</b><br>"
                        f"Periodo: {periodo}",
                        max_width=200,
                    ),
                    tooltip=f"{fila['distrito'].title()}: {int(fila['cantidad']):,} denuncias",
                ).add_to(capa_oficial)
        else:
            heat = [[f["latitud"], f["longitud"], f["cantidad"]] for _, f in mapa_of.iterrows()]
            HeatMap(
                heat, min_opacity=0.3, radius=25, blur=20,
                gradient={0.2: "blue", 0.5: "yellow", 0.8: "orange", 1.0: "red"},
            ).add_to(capa_oficial)
    capa_oficial.add_to(lienzo)

    capa_ciudadana = folium.FeatureGroup(name="🟡 Reportes ciudadanos (todo el Perú)", show=True)
    for _, fila in ciud_agrup.iterrows():
        folium.CircleMarker(
            location=[fila["latitud"], fila["longitud"]],
            radius=max(5, int(fila["reportes"] * 4)),
            color="#f5a623", fill=True, fill_color="#f5a623", fill_opacity=0.8,
            popup=folium.Popup(
                f"<b>{fila['distrito'].title()}</b><br>"
                f"{fila['provincia'].title()}, {fila['departamento'].title()}<br>"
                f"Reportes ciudadanos: <b>{int(fila['reportes'])}</b>",
                max_width=200,
            ),
            tooltip=f"{fila['distrito'].title()}: {int(fila['reportes'])} reporte(s) ciudadano(s)",
        ).add_to(capa_ciudadana)
    capa_ciudadana.add_to(lienzo)

    folium.LayerControl(collapsed=False).add_to(lienzo)
    leyenda = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
        background-color: white; padding: 10px 14px; border-radius: 8px;
        border: 1px solid #ccc; font-size: 13px; line-height: 1.8;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.2);">
        <b>Leyenda</b><br>
        <span style="color:#d62728;">●</span> Alto riesgo (oficial)<br>
        <span style="color:#ff7f0e;">●</span> Riesgo medio (oficial)<br>
        <span style="color:#2ca02c;">●</span> Bajo riesgo (oficial)<br>
        <span style="color:#f5a623;">●</span> Reporte ciudadano
    </div>
    """
    lienzo.get_root().html.add_child(folium.Element(leyenda))
    st_folium(lienzo, width="100%", height=560, returned_objects=[], key="mapa_folium")

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Distritos con datos oficiales", len(mapa_of) if not mapa_of.empty else 0)
    m2.metric("Total denuncias oficiales", f"{int(mapa_of['cantidad'].sum()):,}" if not mapa_of.empty else "0")
    m3.metric("Reportes ciudadanos", len(ciudadanos) if not ciudadanos.empty else 0)
    st.caption(
        "🔴 Datos oficiales: SIDPOL (Mininter) — solo Lima Metropolitana y Callao a nivel distrito. "
        "Cifras absolutas, no por habitante. Desde noviembre 2024 no incluyen denuncias virtuales de robo y hurto. "
        "🟡 Reportes ciudadanos: registrados en esta app, no verificados, en las coordenadas señaladas por el usuario."
    )


# ===================== ESTADÍSTICAS =====================
def estadisticas() -> None:
    oficial = db.denuncias_oficiales_df()
    if oficial.empty:
        st.warning("No hay datos oficiales. Un administrador debe sincronizar en 'Sincronizar datos'.")
        return

    periodos = sorted(oficial["periodo"].unique())
    periodo = st.selectbox(
        "Periodo", periodos,
        index=periodos.index("2025") if "2025" in periodos else 0,
        key="stats_periodo",
    )
    if periodo == "2026-01":
        st.caption("Ojo: 2026-01 es solo un mes; no se compara con los años completos.")

    riesgo = services.indice_riesgo(oficial, periodo)
    if riesgo.empty:
        st.info("No hay datos para ese periodo.")
        return

    ciudadanos = db.incidentes_df()
    zona = ciudadanos[ciudadanos["provincia"].map(normalizar).isin({"LIMA", "CALLAO"})].copy()
    zona["clave"] = zona["distrito"].map(_clave_distrito)
    conteo = zona.groupby("clave").size().rename("reportes_ciudadanos")
    riesgo["clave"] = riesgo["distrito"].map(_clave_distrito)
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


# ======================= REGIONES =======================
def regiones() -> None:
    df = db.denuncias_regionales_df()
    if df.empty:
        st.warning("No hay datos regionales. Un administrador debe sincronizar en 'Sincronizar datos'.")
        return

    corte = df["corte"].dropna().max()
    anio_corte, mes_corte = corte.split("-")
    mes = NOMBRES[int(mes_corte) - 1]
    st.caption(
        f"Cifras acumuladas de enero a {mes} de cada año (reporte con corte en {mes} de {anio_corte})."
    )

    col1, col2 = st.columns(2)
    periodo = col1.selectbox(
        "Año", sorted(df["periodo"].unique(), reverse=True),
        format_func=lambda p: f"Enero a {mes} de {p}", key="reg_anio",
    )
    categoria = col2.selectbox(
        "Categoría", ["Todas"] + sorted(df["categoria"].unique()), key="reg_categoria"
    )

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
    mapa_reg = totales.merge(coords, on="region")
    if mapa_reg.empty:
        st.info("No se pudo ubicar las regiones. Carga el catálogo: python -m backend.ubigeo")
    else:
        fig_mapa = px.scatter_map(
            mapa_reg, lat="latitud", lon="longitud", size="cantidad", color="cantidad",
            hover_name="region", hover_data={"cantidad": True, "latitud": False, "longitud": False},
            size_max=45, zoom=4, color_continuous_scale="YlOrRd", map_style="open-street-map",
            title="Mapa por región",
        )
        st.plotly_chart(fig_mapa, width="stretch")

    pivote = df.groupby(["region", "periodo"])["cantidad"].sum().unstack()
    if {"2025", "2026"}.issubset(pivote.columns):
        pivote["variacion_%"] = ((pivote["2026"] / pivote["2025"] - 1) * 100).round(1)
        st.subheader(f"Variación entre enero-{mes} de 2025 y de 2026")
        st.dataframe(pivote.sort_values("variacion_%").reset_index(), width="stretch", hide_index=True)

    st.caption(
        "Cifras absolutas, no por habitante. Lima aparece dividida en Lima Metropolitana y "
        "Región Lima, como la publica la fuente. Los porcentajes se calculan aquí, no se copian "
        "del PDF. Cada burbuja se coloca en el promedio de las coordenadas de los distritos de "
        "la región, así que es una ubicación aproximada."
    )


# ================= INDICADORES EXTERNOS =================
def indicadores() -> None:
    st.write(
        "Cifras que otras instituciones ya publicaron (INEI, ONG). Cada dato se muestra con su "
        "fuente y su enlace. Estas fuentes no ofrecen descarga automática, así que un "
        "administrador las carga desde un archivo CSV."
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
                archivo = st.file_uploader("Archivo CSV", type=["csv"], key="ind_archivo")
                fuente = st.text_input("Nombre de la fuente (ej.: ENAPRES 2025)", key="ind_fuente")
                entidad = st.text_input("Entidad que la publica (ej.: INEI)", key="ind_entidad")
                tipo = st.selectbox(
                    "Tipo de fuente", ["estatal", "ong"],
                    format_func=lambda t: "Estatal" if t == "estatal" else "ONG",
                    key="ind_tipo",
                )
                url = st.text_input("Enlace donde se publica el dato (https://...)", key="ind_url")
                enviar = st.form_submit_button("Cargar")
            if enviar:
                if archivo is None:
                    st.error("Selecciona un archivo CSV.")
                else:
                    try:
                        resultado = CargaAsistidaCSV(
                            archivo.getvalue(), fuente, entidad, tipo, url
                        ).sincronizar()
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
        return

    indicador = st.selectbox("Indicador", sorted(datos["indicador"].unique()), key="ind_indicador")
    sub = datos[datos["indicador"] == indicador]
    periodo = st.selectbox("Periodo", sorted(sub["periodo"].unique(), reverse=True), key="ind_periodo")
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
