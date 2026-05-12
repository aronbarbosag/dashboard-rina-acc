from datetime import datetime

import pandas as pd
import streamlit as st

from app.config import DEFAULT_FETCH_START_DATE, LOCAL_TIMEZONE, RAW_DIR, pipeline
from app.data import build_sidebar_logo_html


def run_update_from_sidebar(audits):
    logo_html = build_sidebar_logo_html()
    if logo_html:
        st.sidebar.markdown(logo_html, unsafe_allow_html=True)
    st.sidebar.markdown("### Atualizacao")
    st.sidebar.caption(
        "Selecione o intervalo de datas para atualizar os dados e reconstruir o dashboard"
    )
    read_pipeline_lock = getattr(pipeline, "read_pipeline_lock", lambda raw_dir: None)
    is_pipeline_locked = getattr(pipeline, "is_pipeline_locked", lambda raw_dir: False)
    lock_error = getattr(pipeline, "PipelineAlreadyRunningError", RuntimeError)
    lock_info = read_pipeline_lock(RAW_DIR)
    update_running = is_pipeline_locked(RAW_DIR)

    if update_running:
        started_at = lock_info.get("started_at") if lock_info else None
        if started_at:
            parsed_started_at = pd.to_datetime(started_at, errors="coerce", utc=True)
            if pd.notna(parsed_started_at):
                started_at = parsed_started_at.tz_convert(LOCAL_TIMEZONE).strftime(
                    "%d/%m/%Y %H:%M UTC-3"
                )

        st.sidebar.warning(
            "Atualizacao em andamento. Os dados atuais continuam disponiveis."
            + (f"\n\nInicio: {started_at}" if started_at else "")
        )

    if audits.empty:
        default_start = DEFAULT_FETCH_START_DATE
        default_end = datetime.now().date()
    else:
        default_start = min(audits["date"].min().date(), DEFAULT_FETCH_START_DATE)
        default_end = max(audits["date"].max().date(), datetime.now().date())

    update_start = st.sidebar.date_input(
        "Inicio da coleta",
        value=default_start,
        format="DD/MM/YYYY",
        key="update_start",
    )
    update_end = st.sidebar.date_input(
        "Fim da coleta",
        value=default_end,
        format="DD/MM/YYYY",
        key="update_end",
    )

    if st.sidebar.button(
        "Atualizar dados",
        type="primary",
        width="stretch",
        disabled=update_running,
    ):
        try:
            with st.spinner("Atualizando dados da API e reconstruindo datasets..."):
                pipeline.run_pipeline(
                    initial_date=update_start, final_date=update_end, fetch=True
                )
                st.cache_data.clear()
            st.success("Dados atualizados com sucesso.")
            st.rerun()
        except lock_error:
            st.warning(
                "Outra atualizacao ja esta em andamento. Tente novamente em alguns minutos."
            )
        except Exception as error:
            st.error(f"Nao foi possivel atualizar os dados: {error}")
