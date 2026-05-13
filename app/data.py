import base64
import json
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from app.config import (
    FETCH_METADATA_FILE,
    KPIS_FILE,
    LOCAL_TIMEZONE,
    LOGO_PATH,
    MONTH_LABELS,
    PROCESSED_DIR,
)


@st.cache_data(show_spinner=False)
def load_csv(path):
    path = PROCESSED_DIR / path if isinstance(path, str) else path
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_json(path):
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open("r") as file:
        return json.load(file)


def _logo_data_uri():
    if not LOGO_PATH.exists():
        return ""
    suffix = LOGO_PATH.suffix.lower()
    if suffix == ".svg":
        mime_type = "image/svg+xml"
    elif suffix == ".png":
        mime_type = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        mime_type = "image/jpeg"
    else:
        mime_type = "application/octet-stream"
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_sidebar_logo_html():
    uri = _logo_data_uri()
    if not uri:
        return '<div class="sidebar-logo"><span class="sidebar-logo-fallback">RINA</span></div>'
    return f'<div class="sidebar-logo"><img src="{uri}" alt="RINA Logo"></div>'


def build_login_logo_html():
    uri = _logo_data_uri()
    if not uri:
        return '<div class="login-logo-fallback">RINA</div>'
    return f'<img class="login-logo" src="{uri}" alt="RINA Logo">'


def parse_datetime_columns(dataframe, columns):
    dataframe = dataframe.copy()
    for column in columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
    return dataframe


def get_last_update_label():
    metadata = load_json(FETCH_METADATA_FILE)
    fetched_at = metadata.get("fetched_at")

    if fetched_at:
        parsed = pd.to_datetime(fetched_at, errors="coerce", utc=True)
        if pd.notna(parsed):
            return parsed.tz_convert(LOCAL_TIMEZONE).strftime("%d/%m/%Y %H:%M UTC-3")

    kpis_path = PROCESSED_DIR / KPIS_FILE
    if kpis_path.exists():
        modified_at = datetime.fromtimestamp(kpis_path.stat().st_mtime, tz=timezone.utc)
        modified_at = modified_at.astimezone(LOCAL_TIMEZONE)
        return modified_at.strftime("%d/%m/%Y %H:%M UTC-3")

    return "dados ainda nao gerados"


def format_month_label(value):
    if not isinstance(value, str) or "-" not in value:
        return value
    year, month = value.split("-", 1)
    return f"{MONTH_LABELS.get(month, month)}/{year[-2:]}"


def add_month_label(dataframe):
    dataframe = dataframe.copy()
    if dataframe.empty or "audit_month" not in dataframe.columns:
        dataframe["month_label"] = pd.Series(dtype="string")
        return dataframe

    dataframe["month_label"] = dataframe["audit_month"].apply(format_month_label)
    return dataframe
