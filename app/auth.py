import base64
import hashlib
import hmac
import json
import time
from html import escape

import streamlit as st

from app.config import AUTH_CACHE_TTL_SECONDS, DASHBOARD_PASSWORD, DASHBOARD_USERNAME

AUTH_SESSION_KEY = "authenticated"
AUTH_QUERY_PARAM = "auth"


def check_dashboard_credentials(username, password):
    expected_username = str(DASHBOARD_USERNAME or "")
    expected_password = str(DASHBOARD_PASSWORD or "")
    return hmac.compare_digest(username or "", expected_username) and hmac.compare_digest(
        password or "", expected_password
    )


def _auth_secret():
    return hashlib.sha256(
        f"{DASHBOARD_USERNAME or ''}\0{DASHBOARD_PASSWORD or ''}".encode("utf-8")
    ).digest()


def _credentials_fingerprint():
    return hashlib.sha256(
        f"{DASHBOARD_USERNAME or ''}\0{DASHBOARD_PASSWORD or ''}".encode("utf-8")
    ).hexdigest()


def _encode_payload(payload):
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_bytes = payload_json.encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii")
    signature = hmac.new(_auth_secret(), payload_bytes, hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def create_auth_token(username=None, issued_at=None):
    payload = {
        "username": str(username if username is not None else DASHBOARD_USERNAME or ""),
        "issued_at": int(issued_at if issued_at is not None else time.time()),
        "fingerprint": _credentials_fingerprint(),
    }
    return _encode_payload(payload)


def validate_auth_token(token, now=None):
    if not token or "." not in token:
        return False

    encoded_payload, signature = token.rsplit(".", 1)
    try:
        payload_bytes = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return False

    expected_encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii")
    if not hmac.compare_digest(encoded_payload, expected_encoded_payload):
        return False

    expected_signature = hmac.new(
        _auth_secret(), payload_bytes, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return False

    expected_username = str(DASHBOARD_USERNAME or "")
    if not hmac.compare_digest(str(payload.get("username") or ""), expected_username):
        return False

    if not hmac.compare_digest(
        str(payload.get("fingerprint") or ""), _credentials_fingerprint()
    ):
        return False

    issued_at = payload.get("issued_at")
    if not isinstance(issued_at, int):
        return False

    current_time = int(now if now is not None else time.time())
    return 0 <= current_time - issued_at <= AUTH_CACHE_TTL_SECONDS


def _get_cached_auth_token():
    value = st.query_params.get(AUTH_QUERY_PARAM)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _cache_authenticated_session(username=None):
    st.session_state[AUTH_SESSION_KEY] = True
    st.query_params[AUTH_QUERY_PARAM] = create_auth_token(username=username)


def _restore_cached_session():
    if st.session_state.get(AUTH_SESSION_KEY):
        return True

    if validate_auth_token(_get_cached_auth_token()):
        st.session_state[AUTH_SESSION_KEY] = True
        return True

    return False


def _clear_cached_session():
    st.session_state[AUTH_SESSION_KEY] = False
    if AUTH_QUERY_PARAM in st.query_params:
        del st.query_params[AUTH_QUERY_PARAM]


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
                _cache_authenticated_session(username=username)
                st.rerun()
            else:
                st.error("Usuario ou senha invalidos.")


def require_login():
    if _restore_cached_session():
        return True

    render_login()
    return False


def render_logout_control():
    username = escape(str(DASHBOARD_USERNAME or ""))
    st.sidebar.caption(f"Logado como {username}")
    if st.sidebar.button("Sair", width="stretch"):
        _clear_cached_session()
        st.rerun()
