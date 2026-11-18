"""Acceso del administrador en Streamlit. La sesión vive en el navegador (st.session_state)."""
import streamlit as st

from database.limite_login import verificar_con_limite

CLAVE_SESION = "admin_usuario"


def es_admin() -> bool:
    """True si hay una sesión de administrador activa."""
    return bool(st.session_state.get(CLAVE_SESION))


def intentar_login(usuario: str, clave: str) -> None:
    """Valida las credenciales con límite de intentos y muestra el resultado en pantalla."""
    resultado = verificar_con_limite(usuario, clave)
    if resultado.estado == "ok":
        st.session_state[CLAVE_SESION] = usuario.strip().lower()
        st.rerun()
    elif resultado.estado == "bloqueado":
        st.error(f"Demasiados intentos fallidos. Espera {resultado.segundos} segundos para volver a intentar.")
    else:
        st.error(f"Usuario o clave incorrectos. Intentos restantes: {resultado.restantes}.")


def cerrar_sesion() -> None:
    """Cierra la sesión de administrador."""
    st.session_state.pop(CLAVE_SESION, None)


def sesion_en_barra() -> None:
    """Muestra el estado de la sesión en la barra lateral. Solo aparece si hay admin."""
    if not es_admin():
        return
    with st.sidebar:
        st.divider()
        st.caption(f"Administrador: {st.session_state[CLAVE_SESION]}")
        if st.button("Cerrar sesión", key="salir_admin"):
            cerrar_sesion()
            st.rerun()
