from html import escape

import pandas as pd
import streamlit as st


def metric_card(label, value, icon=None, accent="blue", tooltip=None):
    metric_symbols = {
        "clipboard-check": "✓",
        "alert-triangle": "!",
        "bar-chart": "▮",
        "check-circle": "✓",
        "building": "▦",
        "plane": "✈",
    }
    icon_symbol = metric_symbols.get(icon, "")
    icon_html = (
        f'<div class="metric-icon"><span class="metric-symbol">{icon_symbol}</span></div>'
        if icon_symbol
        else ""
    )
    tooltip_text = escape(tooltip or "")
    info_html = (
        f'<span class="metric-info" title="{tooltip_text}" aria-label="{tooltip_text}">i</span>'
        if tooltip
        else ""
    )

    st.html(
        f"""
        <div class="metric-card c-{escape(accent)}">
            <div class="metric-header">
                {icon_html}
                <div class="metric-label">{escape(label)}</div>
                {info_html}
            </div>
            <div class="metric-value">{escape(str(value))}</div>
        </div>
        """,
        width="stretch",
    )


def render_chart(title, caption, chart):
    with st.container(border=True):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="chart-caption">{caption}</div>', unsafe_allow_html=True
        )
        if chart is None:
            st.info("Sem dados para os filtros selecionados.")
        else:
            st.altair_chart(chart, width="stretch")


def format_number(value):
    if pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def format_percent(value):
    return f"{value:.2f}%".replace(".", ",")


def format_decimal(value):
    return f"{value:.2f}".replace(".", ",")


def truncate_label(value, max_length=48):
    if not isinstance(value, str):
        return value
    value = value.strip()
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3].rstrip()}..."
