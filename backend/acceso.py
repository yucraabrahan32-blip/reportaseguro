"""Acceso del administrador en Streamlit. La sesión vive en el navegador (st.session_state)."""
import streamlit as st

from database import usuarios

CLAVE_SESION = "admin_usuario"


def es_admin() -> bool:
    return bool(st.session_state.get(CLAVE_SESION))


def barra_lateral() -> None:
    """Muestra el acceso de administrador en la barra lateral. Llamar una sola vez por página."""
    with st.sidebar:
        st.divider()
        if es_admin():
            st.caption(f"Administrador: {st.session_state[CLAVE_SESION]}")
            if st.button("Cerrar sesión", key="salir_admin"):
                st.session_state.pop(CLAVE_SESION, None)
                st.rerun()
            return
        with st.expander("Administración"):
            if not usuarios.hay_admins():
                st.caption("No hay administradores. Crea uno con: python -m backend.crear_admin")
                return
            with st.form("login_admin"):
                usuario = st.text_input("Usuario")
                clave = st.text_input("Clave", type="password")
                entrar = st.form_submit_button("Entrar")
            if entrar:
                if usuarios.verificar(usuario, clave):
                    st.session_state[CLAVE_SESION] = usuario.strip().lower()
                    st.rerun()
                else:
                    st.error("Usuario o clave incorrectos.")
