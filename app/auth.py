import hmac
from html import escape

import streamlit as st

from app.config import DASHBOARD_PASSWORD, DASHBOARD_USERNAME


def check_dashboard_credentials(username, password):
    expected_username = str(DASHBOARD_USERNAME or "")
    expected_password = str(DASHBOARD_PASSWORD or "")
    return hmac.compare_digest(username or "", expected_username) and hmac.compare_digest(
        password or "", expected_password
    )


def render_login():
    st.markdown(
        """
        <div class="login-header">
            <p class="login-kicker">Acesso restrito</p>
            <h1 class="login-title">Dashboard Operacional RINA ACC</h1>
            <p class="login-subtitle">
                Entre com suas credenciais para visualizar os dados de auditoria.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, login_column, _ = st.columns([1, 1.1, 1])
    with login_column:
        with st.form("dashboard_login"):
            st.markdown("### Login")
            username = st.text_input("Usuario")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button(
                "Entrar",
                type="primary",
                width="stretch",
            )

        if submitted:
            if check_dashboard_credentials(username, password):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Usuario ou senha invalidos.")


def require_login():
    if st.session_state.get("authenticated"):
        return True

    render_login()
    return False


def render_logout_control():
    username = escape(str(DASHBOARD_USERNAME or ""))
    st.sidebar.caption(f"Logado como {username}")
    if st.sidebar.button("Sair", width="stretch"):
        st.session_state["authenticated"] = False
        st.rerun()
