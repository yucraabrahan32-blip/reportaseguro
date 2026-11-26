"""Reportar un incidente marcando el punto exacto en el mapa.

El ciudadano hace clic en el mapa; el sistema guarda esa coordenada real y deduce
el distrito por el centroide mas cercano del catalogo ubigeo. La moderacion
(editar/eliminar) es solo para administradores.
"""
from datetime import date
from math import atan2, cos, radians, sin, sqrt

import folium
import streamlit as st
from streamlit_folium import st_folium

from backend.acceso import es_admin
from backend.models import DELITOS, Incidente, RepositorioIncidentes, Ubicacion
from database import db

repo = RepositorioIncidentes()
OPCIONES = list(DELITOS)

st.title("📝 Reportar incidente")
st.caption(
    "El reporte es anónimo: no se pide cuenta. No escribas nombres, DNI ni teléfonos; "
    "describe el hecho, no a las personas."
)

if "aviso" in st.session_state:
    st.success(st.session_state.pop("aviso"))

# ---------- Catálogo para deducir el distrito ----------
catalogo = db.ubigeo_df()
if catalogo.empty:
    st.warning("Falta cargar el catálogo de ubigeo. Ejecuta: python -m backend.ubigeo")
    st.stop()

# Estado en sesión:
#  - loc_*      : la ubicación elegida (coordenada + distrito deducido)
#  - map_centro/map_zoom : la vista del mapa, para que NO se reinicie al hacer clic
#  - ultimo_clic: el último punto ya procesado (evita reprocesar el mismo clic)
st.session_state.setdefault("loc_lat", None)
st.session_state.setdefault("loc_lon", None)
st.session_state.setdefault("loc_distrito", None)
st.session_state.setdefault("loc_provincia", None)
st.session_state.setdefault("loc_departamento", None)
st.session_state.setdefault("map_centro", [-12.05, -77.05])
st.session_state.setdefault("map_zoom", 11)
st.session_state.setdefault("ultimo_clic", None)


def _distancia_km(lat1, lon1, lat2, lon2):
    """Distancia aproximada entre dos puntos (fórmula de haversine)."""
    radio = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radio * 2 * atan2(sqrt(a), sqrt(1 - a))


# ---------- Mapa para marcar el punto ----------
st.markdown("**📍 Señala en el mapa dónde ocurrió el incidente**")
st.caption("Haz clic en el mapa para marcar el punto exacto. El sistema detecta el distrito solo.")

# El mapa se dibuja en la vista guardada (centro y zoom), no en una fija: asi,
# cuando el usuario hace clic, el mapa NO vuelve a su posicion/zoom inicial.
mapa_sel = folium.Map(
    location=st.session_state["map_centro"],
    zoom_start=st.session_state["map_zoom"],
    tiles="OpenStreetMap",
)
mapa_sel.add_child(folium.ClickForMarker())
if st.session_state["loc_lat"]:
    folium.Marker(
        [st.session_state["loc_lat"], st.session_state["loc_lon"]],
        icon=folium.Icon(color="red", icon="exclamation-sign"),
    ).add_to(mapa_sel)

resultado = st_folium(
    mapa_sel, width="100%", height=420,
    returned_objects=["last_clicked", "center", "zoom"], key="mapa_reporte",
)

# Guardar la vista actual (lo que el usuario movió/acercó) para el próximo dibujado.
if resultado:
    if resultado.get("center"):
        st.session_state["map_centro"] = [resultado["center"]["lat"], resultado["center"]["lng"]]
    if resultado.get("zoom"):
        st.session_state["map_zoom"] = resultado["zoom"]

# Procesar solo un clic NUEVO (si es el mismo de antes, no se vuelve a procesar).
clic = resultado.get("last_clicked") if resultado else None
if clic:
    punto = (clic["lat"], clic["lng"])
    if punto != st.session_state["ultimo_clic"]:
        st.session_state["ultimo_clic"] = punto
        coords = catalogo.dropna(subset=["latitud", "longitud"])
        if not coords.empty:
            distancias = coords.apply(
                lambda r: _distancia_km(punto[0], punto[1], r["latitud"], r["longitud"]), axis=1
            )
            fila = coords.loc[distancias.idxmin()]
            st.session_state.update(
                loc_lat=punto[0], loc_lon=punto[1],
                loc_distrito=fila["distrito"],
                loc_provincia=fila["provincia"],
                loc_departamento=fila["departamento"],
            )
            st.rerun()

if st.session_state["loc_lat"]:
    st.success(
        f"📍 Ubicación detectada: {st.session_state['loc_distrito'].title()}, "
        f"{st.session_state['loc_provincia'].title()}, {st.session_state['loc_departamento'].title()} "
        f"({st.session_state['loc_lat']:.5f}, {st.session_state['loc_lon']:.5f})"
    )
else:
    st.info("👆 Haz clic en el mapa para seleccionar la ubicación del incidente.")

st.divider()

# ---------- Formulario del reporte ----------
with st.form("form_incidente", clear_on_submit=True):
    delito = st.selectbox("Tipo de incidente", OPCIONES, format_func=str.capitalize)
    fecha = st.date_input("Fecha del hecho", value=date.today(), max_value=date.today())
    hora = st.time_input("Hora aproximada")
    descripcion = st.text_area("Descripción", max_chars=500)
    enviado = st.form_submit_button("Enviar reporte", disabled=not st.session_state["loc_lat"])

if enviado:
    if not st.session_state["loc_lat"]:
        st.error("Primero selecciona una ubicación en el mapa.")
    else:
        try:
            nuevo_id = repo.agregar(
                Incidente(
                    ubicacion=Ubicacion(
                        departamento=st.session_state["loc_departamento"],
                        provincia=st.session_state["loc_provincia"],
                        distrito=st.session_state["loc_distrito"],
                        latitud=st.session_state["loc_lat"],
                        longitud=st.session_state["loc_lon"],
                    ),
                    delito=delito,
                    fecha_hecho=fecha,
                    hora_hecho=hora.strftime("%H:%M"),
                    descripcion=descripcion,
                )
            )
        except ValueError as error:
            st.error(str(error))
        else:
            # Limpiar la ubicación elegida para el siguiente reporte.
            st.session_state.update(
                loc_lat=None, loc_lon=None, loc_distrito=None,
                loc_provincia=None, loc_departamento=None,
            )
            st.session_state["aviso"] = f"Reporte #{nuevo_id} registrado. Gracias por contribuir."
            st.rerun()

st.divider()
st.subheader("Reportes recientes")

incidentes = repo.listar(limite=200)
if incidentes.empty:
    st.info("Todavía no hay reportes registrados.")
    st.stop()

if not es_admin():
    st.dataframe(
        incidentes.drop(columns=["descripcion"]).head(10), width="stretch", hide_index=True
    )
    st.caption("Las descripciones y la moderación (editar o eliminar) son solo para administradores.")
    st.stop()

st.dataframe(incidentes.head(10), width="stretch", hide_index=True)

seleccion = st.selectbox(
    "Selecciona un reporte para editar o eliminar",
    incidentes["id"].tolist(),
    format_func=lambda i: f"Reporte #{i}",
)
fila = incidentes[incidentes["id"] == seleccion].iloc[0]

st.markdown("**Editar** (la ubicación no se modifica; si es incorrecta, elimina el reporte)")
with st.form(f"form_editar_{seleccion}"):
    ed_delito = st.selectbox(
        "Tipo de incidente", OPCIONES,
        index=OPCIONES.index(fila["delito"]) if fila["delito"] in OPCIONES else 0,
        format_func=str.capitalize,
    )
    ed_descripcion = st.text_area("Descripción", value=fila["descripcion"], max_chars=500)
    guardar = st.form_submit_button("Guardar cambios")

if guardar:
    try:
        actualizado = repo.actualizar(int(seleccion), ed_delito, ed_descripcion)
    except ValueError as error:
        st.error(str(error))
    else:
        if actualizado:
            st.session_state["aviso"] = f"Reporte #{seleccion} actualizado."
            st.rerun()
        else:
            st.error("No se pudo actualizar el reporte.")

st.markdown("**Eliminar**")
with st.form(f"form_eliminar_{seleccion}"):
    confirmar = st.checkbox("Confirmo que quiero eliminar este reporte")
    eliminar = st.form_submit_button("Eliminar reporte")

if eliminar:
    if not confirmar:
        st.error("Marca la casilla de confirmación para eliminar.")
    elif repo.eliminar(int(seleccion)):
        st.session_state["aviso"] = f"Reporte #{seleccion} eliminado."
        st.rerun()
    else:
        st.error("No se pudo eliminar el reporte.")
