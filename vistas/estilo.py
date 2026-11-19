"""Identidad visual de ReportaSeguro: tipografía, color y pulido de la interfaz.

El tema base (colores) vive en .streamlit/config.toml. Aquí va el CSS que Streamlit
no cubre: fuentes propias, titulares, botones, fichas de métrica, pestañas y barra
lateral. Se aplica una sola vez desde el router (app.py) y rige todas las páginas.

Paleta:
  tinta  #0f1f2e  texto principal (navy profundo)
  marca  #0e6b7a  verde petróleo institucional (acento)
  marca- #0a4d58  variante oscura para hover
  canvas #f3f7f8  fondos tenues
  línea  #d4dee0  bordes finos
Los colores de riesgo (rojo/naranja/verde) se reservan para los datos, no para el cromo.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

/* ---------- Base tipográfica ---------- */
html, body, [class*="st-"], .stApp, button, input, textarea, select {
    font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
}
.stApp { color: #0f1f2e; }

/* ---------- Titulares ---------- */
h1, h2, h3, h4 {
    font-family: 'Schibsted Grotesk', 'Inter', sans-serif !important;
    color: #0f1f2e;
    letter-spacing: -0.015em;
}
h1 { font-weight: 700; }
h2, h3 { font-weight: 600; }

/* ---------- Franja de marca en la barra superior ---------- */
[data-testid="stHeader"] {
    background: #f3f7f8;
    border-bottom: 3px solid #0e6b7a;
}

/* ---------- Botones ---------- */
.stButton > button,
.stDownloadButton > button,
.stLinkButton > a {
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid #d4dee0;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stLinkButton > a:hover {
    border-color: #0e6b7a;
    color: #0e6b7a;
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background: #0e6b7a;
    color: #ffffff;
    border: 1px solid #0e6b7a;
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover {
    background: #0a4d58;
    border-color: #0a4d58;
    color: #ffffff;
}

/* ---------- Enlaces ---------- */
a, a:visited { color: #0e6b7a; }

/* ---------- Métricas como fichas ---------- */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #d4dee0;
    border-left: 4px solid #0e6b7a;
    border-radius: 10px;
    padding: 14px 16px;
}
[data-testid="stMetricValue"] {
    font-family: 'Schibsted Grotesk', sans-serif !important;
    color: #0f1f2e;
}
[data-testid="stMetricLabel"] { color: #5a6b76; }

/* ---------- Pestañas ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #d4dee0;
}
.stTabs [data-baseweb="tab"] { font-weight: 600; }
.stTabs [aria-selected="true"] { color: #0e6b7a; }

/* ---------- Barra lateral ---------- */
[data-testid="stSidebar"] { border-right: 1px solid #d4dee0; }
[data-testid="stSidebar"] h3 { color: #0a4d58; }

/* ---------- Tarjetas (st.container con borde) ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; }

/* ---------- La barra lateral y su control siempre visibles ---------- */
[data-testid="stSidebar"] { visibility: visible !important; }
[data-testid="stSidebarCollapsedControl"] {
    visibility: visible !important;
    z-index: 1000;
}

/* ---------- Ocultar cromo de Streamlit (sin tocar la barra lateral) ---------- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] [data-testid="stActionButton"] { display: none; }

/* ---------- Restaurar la fuente de iconos (Material Symbols) ----------
   El override de Inter con !important rompía las ligaduras de los iconos y
   mostraba su nombre como texto (p. ej. "keyboard_double_arrow_left"). */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
}
</style>
"""


def aplicar_estilo() -> None:
    """Inyecta la identidad visual. Llamar una sola vez, en el router (app.py)."""
    st.markdown(_CSS, unsafe_allow_html=True)
