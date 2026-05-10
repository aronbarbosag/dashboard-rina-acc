import base64
import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import run_pipeline as pipeline
from transforms.transform_audits import (
    AUDITS_PROCESSED_FILE,
    KPIS_FILE,
    NONCONFORMITIES_PROCESSED_FILE,
    PROCESSED_DIR,
    build_analysis_tables,
    build_kpis,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RAW_DIR = Path("data/raw")
FETCH_METADATA_FILE = RAW_DIR / "fetch_metadata.json"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo-rina.png"
FAVICON_PATH = PROJECT_ROOT / "assets" / "favicon.png"
LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
MONTH_LABELS = {
    "01": "Jan",
    "02": "Fev",
    "03": "Mar",
    "04": "Abr",
    "05": "Mai",
    "06": "Jun",
    "07": "Jul",
    "08": "Ago",
    "09": "Set",
    "10": "Out",
    "11": "Nov",
    "12": "Dez",
}

# RINA brand palette (used for layout/UI elements)
GREEN_PTB = "#008543"
LIGHT_GREEN_PTB = "#C4D600"
YELLOW_PTB = "#FDC82F"
BLUE_PTB = "#006298"
CYAN_PTB = "#00B2A9"
ORANGE_PTB = "#ED8B00"
GREY_PTB = "#75787B"
BLUE_DASHBOARD = "#3B82F6"
PURPLE_DASHBOARD = "#6366F1"
RED_DASHBOARD = "#EF4444"
GREEN_DASHBOARD = "#14B8A6"
ORANGE_DASHBOARD = "#F59E0B"
SMOOTH_GREY = "#F8FAFC"

CHART_BLUE = "#2f6fed"  # Auditorias por mes
CHART_TEAL = "#139a8f"
CHART_GOLD = "#d89c22"
CHART_RED = "#d65f5f"  # NC por mes
CHART_PURPLE = "#7c5cc4"  # ATAs / Taxa
CHART_HEIGHT = 320


# ---------------------------------------------------------------------------
# Chart palette: vibrant, coordinated with KPI card icons
# Each entry is (start, end) — start = darker top/left, end = lighter bottom/right
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Inline SVG icons (Lucide-style)
# ---------------------------------------------------------------------------
ICONS = {
    "clipboard-check": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>'
        '<path d="m9 14 2 2 4-4"/></svg>'
    ),
    "alert-triangle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/></svg>'
    ),
    "bar-chart": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="12" x2="12" y1="20" y2="10"/>'
        '<line x1="18" x2="18" y1="20" y2="4"/>'
        '<line x1="6" x2="6" y1="20" y2="16"/></svg>'
    ),
    "check-circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/></svg>'
    ),
    "building": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<rect width="16" height="20" x="4" y="2" rx="2"/>'
        '<path d="M9 22v-4h6v4"/>'
        '<path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/>'
        '<path d="M12 10h.01"/><path d="M12 14h.01"/>'
        '<path d="M16 10h.01"/><path d="M16 14h.01"/>'
        '<path d="M8 10h.01"/><path d="M8 14h.01"/></svg>'
    ),
    "plane": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2'
        "c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 "
        '3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>'
    ),
    "doc-check": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<path d="m9 15 2 2 4-4"/></svg>'
    ),
    "trend-up": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline points="16 7 22 7 22 13"/></svg>'
    ),
    "trend-down": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/>'
        '<polyline points="16 17 22 17 22 11"/></svg>'
    ),
    "helicopter": (
        """
            <svg viewBox="0 0 1024 1024" class="icon" version="1.1" xmlns="http://www.w3.org/2000/svg" fill="#000000"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"><path d="M659.2 439.1H423.6c-13.9 0-25.2-11.3-25.2-25.2v-39.3c0-13.9 11.3-25.2 25.2-25.2h235.5c13.9 0 25.2 11.3 25.2 25.2v39.3c0.1 13.9-11.2 25.2-25.1 25.2z" fill="#B6CDEF"></path><path d="M659.2 454.1H423.6c-22.2 0-40.2-18-40.2-40.2v-39.3c0-22.2 18-40.2 40.2-40.2h235.5c22.2 0 40.2 18 40.2 40.2v39.3c0.1 22.2-18 40.2-40.1 40.2z m-235.6-89.7c-5.6 0-10.2 4.6-10.2 10.2v39.3c0 5.6 4.6 10.2 10.2 10.2h235.5c5.6 0 10.2-4.6 10.2-10.2v-39.3c0-5.6-4.6-10.2-10.2-10.2H423.6z" fill="#0F53A8"></path><path d="M183.6 417.8h548.7s154.5 32 205.6 208.6c13.6 47.1-14.9 105.7-63.9 105.7H615.1s-143.8 0.1-271.7-218.4L109 487 29.1 295.3h42.6l111.9 122.5z" fill="#B6CDEF"></path><path d="M615.1 747.1c-1.7 0-40.3-0.3-94.9-29-31.4-16.5-62-39.2-90.9-67.4-34.2-33.4-66.2-74.8-95-123l-227-25.8c-5.4-0.6-10.1-4.1-12.2-9.1L15.3 301c-1.9-4.6-1.4-9.9 1.4-14.1 2.8-4.2 7.5-6.7 12.5-6.7h42.6c4.2 0 8.2 1.8 11.1 4.9l107.4 117.6h542.1c1 0 2 0.1 3 0.3 1.7 0.4 42 8.9 88.9 40.3 27.5 18.4 51.6 40.8 71.8 66.7 25.1 32.3 44.1 70 56.3 112.2 8.9 30.9 2.3 67.3-16.8 92.8-15.6 20.7-37.4 32.1-61.5 32.1h-259z m-495.6-274l225.6 25.6c4.7 0.5 8.9 3.2 11.3 7.3 28.1 48.1 59.3 89.1 92.7 121.9 26.5 26.1 54.5 47.1 83.1 62.4 48.5 26 82.7 26.6 83 26.6H874c18.5 0 30.6-10.9 37.5-20.1 13.7-18.2 18.4-44.3 12-66.4-11-38.2-28.1-72.3-50.6-101.4-18-23.3-39.6-43.5-64.2-60.1-37.6-25.4-71.1-34.5-78.1-36.3h-547c-4.2 0-8.2-1.8-11.1-4.9L65.1 310.3H51.6l67.9 162.8z" fill="#0F53A8"></path><path d="M160.8 454.2m-68.4 0a68.4 68.4 0 1 0 136.8 0 68.4 68.4 0 1 0-136.8 0Z" fill="#89B7F5"></path><path d="M160.8 537.6c-46 0-83.4-37.4-83.4-83.4 0-46 37.4-83.4 83.4-83.4s83.4 37.4 83.4 83.4c0 45.9-37.4 83.4-83.4 83.4z m0-136.8c-29.4 0-53.4 23.9-53.4 53.4s23.9 53.4 53.4 53.4 53.4-23.9 53.4-53.4-24-53.4-53.4-53.4z" fill="#0F53A8"></path><path d="M487.3 549.2m-35.5 0a35.5 35.5 0 1 0 71 0 35.5 35.5 0 1 0-71 0Z" fill="#89B7F5"></path><path d="M487.3 599.7c-27.9 0-50.5-22.7-50.5-50.5s22.7-50.5 50.5-50.5c27.9 0 50.5 22.7 50.5 50.5s-22.7 50.5-50.5 50.5z m0-71c-11.3 0-20.5 9.2-20.5 20.5s9.2 20.5 20.5 20.5 20.5-9.2 20.5-20.5-9.2-20.5-20.5-20.5z" fill="#0F53A8"></path><path d="M595.6 549.2m-35.5 0a35.5 35.5 0 1 0 71 0 35.5 35.5 0 1 0-71 0Z" fill="#89B7F5"></path><path d="M595.6 599.7c-27.9 0-50.5-22.7-50.5-50.5s22.7-50.5 50.5-50.5 50.5 22.7 50.5 50.5-22.7 50.5-50.5 50.5z m0-71c-11.3 0-20.5 9.2-20.5 20.5s9.2 20.5 20.5 20.5 20.5-9.2 20.5-20.5-9.2-20.5-20.5-20.5z" fill="#0F53A8"></path><path d="M813.3 454.2s34.8 0 109.5 130.5c24.3 42.5-99.3 28.7-148.3 28.7L719 481.7l94.3-27.5z" fill="#89B7F5"></path><path d="M853.7 630.5c-14.5 0-30.6-0.5-47.8-1.2-11.8-0.5-22.9-0.9-31.3-0.9-6 0-11.5-3.6-13.8-9.2l-55.5-131.7c-1.7-3.9-1.6-8.4 0.3-12.3s5.2-6.8 9.3-8l94.2-27.5c1.4-0.4 2.8-0.6 4.2-0.6 5.4 0 17.4 2.6 36.8 20.2 25.1 22.7 54 62.4 85.7 117.9 8.5 14.9 4.5 26 1.3 31.2-10.6 17.7-40.7 22.1-83.4 22.1z m-69.1-32c6.9 0.2 14.5 0.5 22.5 0.8 21.9 0.9 46.7 1.8 67.8 0.7 24.2-1.3 32.9-4.9 35.6-6.5-0.2-0.4-0.4-0.8-0.7-1.3-56.7-99.1-88.6-118.8-96.4-122.4l-74 21.6 45.2 107.1z" fill="#0F53A8"></path><path d="M568 213.1h48.9v136.4H568z" fill="#B6CDEF"></path><path d="M616.9 364.4H568c-8.3 0-15-6.7-15-15V213.1c0-8.3 6.7-15 15-15h48.9c8.3 0 15 6.7 15 15v136.4c0 8.2-6.7 14.9-15 14.9z m-33.9-30h18.9V228.1H583v106.3z" fill="#0F53A8"></path><path d="M178.3 213.1H1004" fill="#B6CDEF"></path><path d="M1004 228.1H178.3c-8.3 0-15-6.7-15-15s6.7-15 15-15H1004c8.3 0 15 6.7 15 15s-6.7 15-15 15z" fill="#0F53A8"></path><path d="M513.9 790.7h427.4" fill="#B6CDEF"></path><path d="M941.3 805.7H513.9c-8.3 0-15-6.7-15-15s6.7-15 15-15h427.4c8.3 0 15 6.7 15 15s-6.7 15-15 15z" fill="#0F53A8"></path><path d="M631.1 732.1v58.6" fill="#B6CDEF"></path><path d="M631.1 805.7c-8.3 0-15-6.7-15-15v-58.6c0-8.3 6.7-15 15-15s15 6.7 15 15v58.6c0 8.3-6.7 15-15 15z" fill="#0F53A8"></path><path d="M833.5 732.1v58.6" fill="#B6CDEF"></path><path d="M833.5 805.7c-8.3 0-15-6.7-15-15v-58.6c0-8.3 6.7-15 15-15s15 6.7 15 15v58.6c0 8.3-6.7 15-15 15z" fill="#0F53A8"></path></g></svg>

        """
    ),
}

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RINA ACC Dashboard",
    page_icon=str(FAVICON_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            /* RINA brand */
            --rina-dark-blue: #13294B;
            --rina-blue: #0076A5;
            --rina-light-blue: #3EB1C8;
            --rina-light-grey: #D9D9D6;
            --rina-grey: #97999B;
            --btn-green: #4ADE80;
            --bg-rina: linear-gradient(224.15deg, #0076A5 -15.92%, #13294B 70%);

            /* Surface tokens */
            --background: #F4F6FA;
            --surface: #FFFFFF;
            --surface-soft: #F8FAFC;
            --border: #E5EBF3;
            --border-strong: #D1DAE6;
            --muted: #6B7280;
            --text: var(--rina-dark-blue);
            --accent: var(--rina-blue);
            --accent-soft: #E6F2F8;
            --sidebar: #FAFCFE;

            /* Effects */
            --shadow-sm: 0 1px 2px rgba(19, 41, 75, 0.04);
            --shadow-md: 0 4px 12px rgba(19, 41, 75, 0.06);
            --shadow-lg: 0 12px 28px rgba(19, 41, 75, 0.10);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .stApp { background: var(--background); color: var(--text); }

        /* ========================================================== */
        /*  SIDEBAR                                                   */
        /* ========================================================== */
        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * { color: var(--text) !important; }

        [data-testid="stSidebar"] h3 {
            color: var(--rina-dark-blue) !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 1.4rem;
            margin-bottom: 0.5rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid var(--border);
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] [data-baseweb="popover"] {
            background-color: #ffffff !important;
            border-color: var(--border) !important;
            border-radius: var(--radius-sm) !important;
        }

        [data-testid="stSidebar"] [data-baseweb="tag"] {
            background-color: var(--accent-soft) !important;
            color: var(--rina-blue) !important;
            border: 1px solid rgba(0, 118, 165, 0.2) !important;
        }

        [data-testid="stSidebar"] svg { fill: var(--text) !important; }

        [data-testid="stSidebar"] button[kind="primary"] {
            background: var(--rina-blue) !important;
            border: 1px solid var(--rina-blue) !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: var(--radius-sm) !important;
            transition: all 0.2s ease !important;
            padding: 0.6rem 1rem !important;
        }

        [data-testid="stSidebar"] button[kind="primary"]:hover {
            background: var(--rina-dark-blue) !important;
            border-color: var(--rina-dark-blue) !important;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        [data-testid="stSidebar"] button[kind="primary"] * { color: #ffffff !important; }

        .sidebar-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.35rem;
        }

        .sidebar-logo img {
            max-height: 200px;

            width: auto;
            object-fit: contain;
        }

        .sidebar-logo-fallback {
            color: #ffffff !important;
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: 0.18em;
        }

        /* ========================================================== */
        /*  LAYOUT                                                    */
        /* ========================================================== */
        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 1400px;
            margin: 0 auto;

        }

        h1, h2, h3 {
            letter-spacing: -0.01em;
            color: var(--rina-dark-blue);
        }

        /* ========================================================== */
        /*  PAGE HEADER  (light layout matching reference design)     */
        /* ========================================================== */
        .page-header {
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            margin: 0.2rem 0 1.4rem 0;
        }

        .page-header-icon {
            background: rgba(30, 136, 229, 0.12);
            color: #1E88E5;
            padding: 0.7rem;
            border-radius: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .page-header-icon svg { width: 30px; height: 30px; }

        .page-header-content { flex: 1; min-width: 0; }

        .page-header-title {
            font-size: 2rem;
            font-weight: 750;
            color: var(--rina-dark-blue);
            margin: 0 0 0.25rem 0;
            line-height: 1.1;
            letter-spacing: -0.02em;
        }

        .page-header-subtitle {
            color: var(--muted);
            font-size: 0.95rem;
            margin: 0 0 0.2rem 0;
        }

        .page-header-meta {
            color: #94A3B8;
            font-size: 0.82rem;
            margin: 0;
        }

        /* ========================================================== */
        /*  KPI CARDS                                                 */
        /* ========================================================== */
        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-sm);
            padding: 1.05rem 1.15rem 1rem;
            min-height: 140px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: var(--border-strong);
        }

        .metric-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 0.55rem;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
            line-height: 1.3;
            flex: 1;
        }

        .metric-info {
            width: 18px;
            height: 18px;
            border-radius: 999px;
            border: 1px solid var(--border-strong);
            color: var(--muted);
            background: var(--surface-soft);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 800;
            line-height: 1;
            cursor: help;
            flex-shrink: 0;
        }

        .metric-icon {
            width: 36px;
            height: 36px;
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .metric-symbol {
            font-size: 1.05rem;
            font-weight: 800;
            line-height: 1;
        }

        .metric-card.c-blue   .metric-icon { background: rgba(30, 136, 229, 0.12);  color: #1E88E5; }
        .metric-card.c-orange .metric-icon { background: rgba(234, 88, 12, 0.12);   color: #EA580C; }
        .metric-card.c-purple .metric-icon { background: rgba(124, 58, 237, 0.12);  color: #7C3AED; }
        .metric-card.c-green  .metric-icon { background: rgba(5, 150, 105, 0.12);   color: #059669; }
        .metric-card.c-teal   .metric-icon { background: rgba(13, 148, 136, 0.12);  color: #0D9488; }
        .metric-card.c-sky    .metric-icon { background: rgba(2, 132, 199, 0.12);   color: #0284C7; }

        .metric-value {
            font-size: 1.95rem;
            line-height: 1.05;
            font-weight: 700;
            color: var(--rina-dark-blue);
            letter-spacing: -0.025em;
        }

        /* ========================================================== */
        /*  CHART CARDS  (bordered container wraps title+caption+chart)
        /* ========================================================== */
        div.stColumn {
            background: #ffffff !important;
            border-radius: var(--radius-md) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            box-shadow: var(--shadow-sm);
            transition: box-shadow 0.2s ease;
            padding: 1.1rem 1.2rem 0.9rem !important;
            min-height: 430px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background: #ffffff !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: var(--shadow-md);
        }

        .chart-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--rina-dark-blue);
            margin: 0 0 0.2rem 0;
            letter-spacing: -0.01em;
        }

        .chart-caption {
            color: var(--muted);
            font-size: 0.84rem;
            margin: 0 0 0.6rem 0;
        }

        /* Strip the default chart wrapper styling since it's now inside our card */
        [data-testid="stVegaLiteChart"], .stAltairChart {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        /* ========================================================== */
        /*  SECTION TITLES (for tables outside chart cards)           */
        /* ========================================================== */
        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0.6rem 0 0.2rem 0;
            color: var(--rina-dark-blue);
            letter-spacing: -0.01em;
        }

        .section-caption {
            color: var(--muted);
            font-size: 0.86rem;
            margin: 0 0 0.6rem 0;
        }

        /* ========================================================== */
        /*  DATAFRAME                                                 */
        /* ========================================================== */
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }

        /* ========================================================== */
        /*  TABS                                                      */
        /* ========================================================== */
        .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid var(--border); }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            color: var(--muted);
            padding: 0.5rem 0.95rem;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            background: var(--accent-soft) !important;
            color: var(--rina-blue) !important;
            font-weight: 600;
        }

        /* ========================================================== */
        /*  DIVIDERS / ALERTS                                         */
        /* ========================================================== */
        hr, [data-testid="stDivider"] {
            border: none !important;
            border-top: 1px solid var(--border) !important;
            margin: 1.4rem 0 !important;
        }

        [data-testid="stAlert"] {
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }

        /* ========================================================== */
        /*  PRINT                                                     */
        /* ========================================================== */
        @media print {
            [data-testid="stSidebar"], header, footer { display: none !important; }
            .block-container { padding: 0.6rem !important; }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                box-shadow: none !important;
                page-break-inside: avoid;
            }
        }

        @media (max-width: 900px) {
            .block-container {
                padding: 1.2rem 1rem 2rem;
            }

            .page-header {
                flex-direction: column;
                align-items: flex-start;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_json(path):
    path = Path(path)
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


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def metric_card(label, value, icon=None, accent="blue", trend=None, tooltip=None):
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


def format_number(value):
    if pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def format_percent(value):
    return f"{value:.2f}%".replace(".", ",")


def format_decimal(value):
    return f"{value:.2f}".replace(".", ",")


def add_month_label(dataframe):
    dataframe = dataframe.copy()
    if dataframe.empty or "audit_month" not in dataframe.columns:
        dataframe["month_label"] = pd.Series(dtype="string")
        return dataframe

    dataframe["month_label"] = dataframe["audit_month"].apply(format_month_label)
    return dataframe


def format_month_label(value):
    if not isinstance(value, str) or "-" not in value:
        return value
    year, month = value.split("-", 1)
    return f"{MONTH_LABELS.get(month, month)}/{year[-2:]}"


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
def chart_config(chart):
    return (
        chart.configure_view(strokeWidth=0, fill="#ffffff")
        .configure(
            background="#ffffff",
            font="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        )
        .configure_axis(
            gridColor="#EEF2F7",
            gridDash=[2, 3],
            labelColor="#94A3B8",
            titleColor=CHART_TEAL,
            domainColor="#E5EBF3",
            tickColor="#E5EBF3",
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight=600,
            titlePadding=10,
        )
        .configure_legend(
            labelColor=CHART_TEAL,
            titleColor=CHART_TEAL,
            labelFontSize=11,
            titleFontSize=11,
        )
    )


def make_bar_chart(
    dataframe, x, y, tooltip, height=CHART_HEIGHT, sort="-x", color=CHART_TEAL
):
    """Vertical bars with a solid fill color."""
    if dataframe.empty:
        return None

    base = alt.Chart(dataframe).encode(
        x=alt.X(x, sort=sort, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title=None),
        tooltip=tooltip,
    )
    bars = base.mark_bar(
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        color=color,
    )
    labels = base.mark_text(
        dy=-6,
        color="#1f2a44",
        fontSize=11,
        fontWeight=600,
    ).encode(
        text=alt.Text(y, format=",.0f"),
    )
    chart = (bars + labels).properties(height=height)
    return chart_config(chart)


def make_horizontal_bar(
    dataframe, y, x, tooltip, height=CHART_HEIGHT, color=CHART_TEAL
):
    """Horizontal bars with a solid fill color."""
    if dataframe.empty:
        return None

    base = alt.Chart(dataframe).encode(
        y=alt.Y(y, sort="-x", title=None),
        x=alt.X(x, title=None),
        tooltip=tooltip,
    )
    bars = base.mark_bar(
        cornerRadiusTopRight=5,
        cornerRadiusBottomRight=5,
        color=color,
    )
    labels = base.mark_text(
        align="left",
        dx=6,
        color="#1f2a44",
        fontSize=11,
        fontWeight=600,
    ).encode(
        text=alt.Text(x, format=",.0f"),
    )
    chart = (bars + labels).properties(height=height)
    return chart_config(chart)


def make_area_line_chart(
    dataframe, x, y, tooltip, sort, color=CHART_TEAL, height=CHART_HEIGHT
):
    """Soft area under a line for trend visualization."""
    if dataframe.empty:
        return None

    start = color
    base = alt.Chart(dataframe).encode(
        x=alt.X(x, sort=sort, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title=None),
        tooltip=tooltip,
    )

    area = base.mark_area(
        color=start,
        opacity=0.12,
    )
    line = base.mark_line(strokeWidth=3, color=start)
    points = base.mark_point(size=80, fill=start, stroke="#ffffff", strokeWidth=2)
    labels = base.mark_text(
        dy=-10,
        color="#1f2a44",
        fontSize=11,
        fontWeight=600,
    ).encode(
        text=alt.Text(y, format=".2f"),
    )

    return chart_config((area + line + points + labels).properties(height=height))


def render_chart(title, caption, chart):
    """Each chart is wrapped in a bordered container with title + caption inside."""
    with st.container(border=True):
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="chart-caption">{caption}</div>', unsafe_allow_html=True
        )
        if chart is None:
            st.info("Sem dados para os filtros selecionados.")
        else:
            st.altair_chart(chart, width="stretch")


# ---------------------------------------------------------------------------
# Sidebar – filters and update
# ---------------------------------------------------------------------------
def filter_dataframe(audits, nonconformities):
    st.sidebar.markdown("### Filtros")

    if audits.empty:
        return audits, nonconformities

    min_date = audits["date"].min().date()
    max_date = audits["date"].max().date()
    selected_range = st.sidebar.date_input(
        "Periodo",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = min_date
        end_date = max_date

    filtered = audits[
        (audits["date"].dt.date >= start_date) & (audits["date"].dt.date <= end_date)
    ].copy()

    filter_columns = [
        ("operator_abbreviation", "Operadora"),
        ("base_abbreviation", "Base"),
        ("auditing_type", "Tipo de auditoria"),
        ("aircraft_prefix", "Aeronave"),
        ("aircraft_backup_label", "Titular/backup"),
        ("aircraft_configuration", "Configuracao"),
    ]

    for column, label in filter_columns:
        if column not in filtered.columns:
            continue

        values = sorted(value for value in filtered[column].dropna().unique())
        selected = st.sidebar.multiselect(label, values, default=[])
        if selected:
            filtered = filtered[filtered[column].isin(selected)]

    audit_ids = set(filtered["audit_id"])
    filtered_nonconformities = nonconformities[
        nonconformities["audit_id"].isin(audit_ids)
    ].copy()

    return filtered, filtered_nonconformities


def count_dashboard_rows(dataframe, columns, value_name):
    if dataframe.empty or not set(columns).issubset(dataframe.columns):
        return pd.DataFrame(columns=[*columns, value_name])

    return (
        dataframe.groupby(columns, dropna=False)
        .size()
        .reset_index(name=value_name)
        .sort_values(
            [value_name, *columns], ascending=[False, *([True] * len(columns))]
        )
        .reset_index(drop=True)
    )


def build_dashboard_recurrence_table(dataframe, group_columns):
    output_columns = [
        *group_columns,
        "audits_count",
        "current_nonconformities_count",
        "previous_nonconformities_count",
        "audits_with_current_nonconformity",
        "audits_with_previous_nonconformity",
        "recurrent_audits",
        "recurrence_rate",
    ]
    required_columns = {
        *group_columns,
        "audit_id",
        "nonconformity_total",
        "previous_nonconformity_total",
    }
    if dataframe.empty or not required_columns.issubset(dataframe.columns):
        return pd.DataFrame(columns=output_columns)

    source = dataframe.copy()
    source["has_current_nonconformity"] = source["nonconformity_total"] > 0
    source["has_previous_nonconformity"] = source["previous_nonconformity_total"] > 0
    source["has_recurrence"] = (
        source["has_current_nonconformity"] & source["has_previous_nonconformity"]
    )

    table = (
        source.groupby(group_columns, dropna=False)
        .agg(
            audits_count=("audit_id", "count"),
            current_nonconformities_count=("nonconformity_total", "sum"),
            previous_nonconformities_count=("previous_nonconformity_total", "sum"),
            audits_with_current_nonconformity=("has_current_nonconformity", "sum"),
            audits_with_previous_nonconformity=("has_previous_nonconformity", "sum"),
            recurrent_audits=("has_recurrence", "sum"),
        )
        .reset_index()
    )
    table["recurrence_rate"] = (
        (
            table["recurrent_audits"]
            / table["audits_with_previous_nonconformity"].replace(0, pd.NA)
        )
        .fillna(0)
        .round(2)
    )

    return table.sort_values(
        [
            "recurrent_audits",
            "recurrence_rate",
            "current_nonconformities_count",
            "audits_count",
        ],
        ascending=False,
    ).reset_index(drop=True)


def ensure_dashboard_analysis_tables(tables, audits, nonconformities):
    tables.setdefault(
        "nonconformities_by_area",
        count_dashboard_rows(nonconformities, ["area"], "nonconformities_count"),
    )
    tables.setdefault(
        "recurrence_by_aircraft",
        build_dashboard_recurrence_table(audits, ["aircraft_prefix"]),
    )
    tables.setdefault(
        "recurrence_by_base",
        build_dashboard_recurrence_table(audits, ["base_abbreviation", "base"]),
    )
    tables.setdefault(
        "recurrence_by_operator",
        build_dashboard_recurrence_table(audits, ["operator_abbreviation", "operator"]),
    )
    return tables


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
        default_start = datetime.now().date()
        default_end = datetime.now().date()
    else:
        default_start = audits["date"].min().date()
        default_end = audits["date"].max().date()

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


# ---------------------------------------------------------------------------
# Trend computation (last 30 days vs previous 30 days)
# ---------------------------------------------------------------------------
def compute_period_trends(audits, nonconformities):
    """Returns a dict of optional trend dicts for KPI cards. Safe with empty/sparse data."""
    trends = {"audits": None, "nonconformities": None}

    if audits.empty or "date" not in audits.columns:
        return trends

    max_date = audits["date"].max()
    if pd.isna(max_date):
        return trends

    cutoff = max_date - pd.Timedelta(days=30)
    prev_cutoff = cutoff - pd.Timedelta(days=30)

    recent_audits = int((audits["date"] > cutoff).sum())
    previous_audits = int(
        ((audits["date"] > prev_cutoff) & (audits["date"] <= cutoff)).sum()
    )

    recent_ncs = (
        int((nonconformities["date"] > cutoff).sum())
        if not nonconformities.empty and "date" in nonconformities.columns
        else 0
    )
    previous_ncs = (
        int(
            (
                (nonconformities["date"] > prev_cutoff)
                & (nonconformities["date"] <= cutoff)
            ).sum()
        )
        if not nonconformities.empty and "date" in nonconformities.columns
        else 0
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    apply_style()

    audits = load_csv(PROCESSED_DIR / AUDITS_PROCESSED_FILE)
    nonconformities = load_csv(PROCESSED_DIR / NONCONFORMITIES_PROCESSED_FILE)

    audits = parse_datetime_columns(audits, ["date", "publication_date"])
    nonconformities = parse_datetime_columns(
        nonconformities,
        ["date", "publication_date", "resolution_date"],
    )

    run_update_from_sidebar(audits)

    last_update = get_last_update_label()

    # ---- Page header ----
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-content">
                <h1 class="page-header-title">Dashboard Operacional RINA ACC</h1>
                <p class="page-header-subtitle">
                    Dados puxados em tempo real da api do RINA ACC.
                </p>
                <p class="page-header-meta">Ultima atualizacao dos dados: {last_update}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if audits.empty:
        st.warning(
            "Nenhum dado processado encontrado. Use o botao Atualizar dados ou rode "
            "`uv run python scripts/run_pipeline.py`."
        )
        return

    filtered_audits, filtered_nonconformities = filter_dataframe(
        audits, nonconformities
    )
    kpis = build_kpis(filtered_audits, filtered_nonconformities)
    tables = build_analysis_tables(filtered_audits, filtered_nonconformities)
    tables = ensure_dashboard_analysis_tables(
        tables,
        filtered_audits,
        filtered_nonconformities,
    )

    # ---- KPI cards ----
    metric_columns = st.columns(6)
    with metric_columns[0]:
        metric_card(
            "Auditorias",
            format_number(kpis["total_audits"]),
            icon="clipboard-check",
            accent="blue",
        )
    with metric_columns[1]:
        metric_card(
            "Nao conformidades",
            format_number(kpis["total_nonconformities"]),
            icon="alert-triangle",
            accent="orange",
        )
    with metric_columns[2]:
        metric_card(
            "Taxa de NC",
            format_decimal(kpis["nonconformities_per_audit"]),
            icon="bar-chart",
            accent="purple",
            tooltip=(
                "Media de nao conformidades atuais por auditoria no filtro atual. "
                "Formula: total de NC atuais dividido pelo total de auditorias."
            ),
        )
    with metric_columns[3]:
        metric_card(
            "Auditorias afetadas",
            format_percent(kpis["percent_audits_with_nonconformity"]),
            icon="check-circle",
            accent="green",
            tooltip=(
                "Percentual de auditorias que tiveram pelo menos uma nao conformidade "
                "atual. Formula: auditorias com NC atual dividido pelo total de auditorias."
            ),
        )
    with metric_columns[4]:
        metric_card(
            "Bases",
            format_number(kpis["audited_bases"]),
            icon="building",
            accent="teal",
        )
    with metric_columns[5]:
        metric_card(
            "Aeronaves",
            format_number(kpis["audited_aircraft"]),
            icon="plane",
            accent="sky",
        )

    st.divider()

    # ---- Monthly tables ----
    audits_by_month = add_month_label(
        tables["audits_by_month"].sort_values("audit_month")
    )
    nonconformities_by_month = add_month_label(
        tables["nonconformities_by_month"].sort_values("audit_month")
    )
    monthly_rate = add_month_label(
        tables["monthly_nonconformity_rate"].sort_values("audit_month")
    )
    month_order = audits_by_month["month_label"].tolist()

    monthly_rate_chart = make_area_line_chart(
        monthly_rate,
        "month_label:N",
        "nonconformities_per_audit:Q",
        [
            "month_label",
            "audits_count",
            "nonconformities_count",
            "nonconformities_per_audit",
        ],
        sort=month_order,
        color=CHART_TEAL,
    )

    col_left, col_right = st.columns(2)
    with col_left:
        render_chart(
            "Auditorias por mes",
            "Volume de auditorias realizadas no periodo filtrado.",
            make_bar_chart(
                audits_by_month,
                "month_label:N",
                "audits_count:Q",
                ["month_label", "audits_count"],
                sort=month_order,
                color=CHART_TEAL,
            ),
        )
    with col_right:
        render_chart(
            "Nao conformidades por mes",
            "Quantidade de registros de nao conformidade por mes.",
            make_bar_chart(
                nonconformities_by_month,
                "month_label:N",
                "nonconformities_count:Q",
                ["month_label", "nonconformities_count"],
                sort=month_order,
                color=CHART_RED,
            ),
        )

    col_left, col_right = st.columns(2)
    with col_left:
        render_chart(
            "Taxa mensal de NC por auditoria",
            "Ajuda a comparar meses com volumes diferentes de auditorias.",
            monthly_rate_chart,
        )
    with col_right:
        render_chart(
            "Auditorias por tipo",
            "Distribuicao dos tipos de auditoria no periodo.",
            make_horizontal_bar(
                tables["audits_by_type"],
                "auditing_type:N",
                "audits_count:Q",
                ["auditing_type", "audits_count"],
                color=CHART_TEAL,
            ),
        )

    col_left, col_right = st.columns(2)
    with col_left:
        render_chart(
            "Nao conformidades por operadora",
            "Ranking de operadoras com mais registros de nao conformidade.",
            make_horizontal_bar(
                tables["nonconformities_by_operator"].head(12),
                "operator_abbreviation:N",
                "nonconformities_count:Q",
                ["operator_abbreviation", "operator", "nonconformities_count"],
                color=CHART_TEAL,
            ),
        )
    with col_right:
        render_chart(
            "Nao conformidades por area",
            "Separacao das nao conformidades atuais entre operacional e manutencao.",
            make_horizontal_bar(
                tables["nonconformities_by_area"],
                "area:N",
                "nonconformities_count:Q",
                ["area", "nonconformities_count"],
                color=CHART_GOLD,
            ),
        )

    col_left, col_right = st.columns(2)
    with col_left:
        render_chart(
            "Nao conformidades por base",
            "Concentracao de registros por base operacional.",
            make_horizontal_bar(
                tables["nonconformities_by_base"].head(12),
                "base_abbreviation:N",
                "nonconformities_count:Q",
                ["base_abbreviation", "base", "nonconformities_count"],
                color=CHART_TEAL,
            ),
        )
    with col_right:
        render_chart(
            "ATAs mais recorrentes",
            "Principais categorias ATA presentes nas nao conformidades.",
            make_horizontal_bar(
                tables["ata_ranking"].head(12),
                "ata:N",
                "nonconformities_count:Q",
                ["ata", "nonconformities_count", "audits_count"],
                color=CHART_TEAL,
            ),
        )

    col_left, col_right = st.columns(2)
    with col_left:
        render_chart(
            "Aeronaves com mais NC",
            "Ranking de aeronaves por volume de nao conformidades.",
            make_horizontal_bar(
                tables["aircraft_ranking"].head(12),
                "aircraft_prefix:N",
                "nonconformities_count:Q",
                ["aircraft_prefix", "nonconformities_count", "audits_count"],
                color=CHART_RED,
            ),
        )
    with col_right:
        render_chart(
            "Recorrencia por aeronave",
            "Aeronaves com NC anterior e NC atual no periodo filtrado.",
            make_horizontal_bar(
                tables["recurrence_by_aircraft"].head(12),
                "aircraft_prefix:N",
                "recurrent_audits:Q",
                [
                    "aircraft_prefix",
                    "recurrent_audits",
                    "current_nonconformities_count",
                    "previous_nonconformities_count",
                    "recurrence_rate",
                ],
                color=CHART_PURPLE,
            ),
        )

    col_left, col_right = st.columns(2)
    with col_left:
        render_chart(
            "Titular vs backup",
            "Quantidade de auditorias por condicao da aeronave.",
            make_horizontal_bar(
                tables["aircraft_backup_summary"],
                "aircraft_backup_label:N",
                "audits_count:Q",
                ["aircraft_backup_label", "audits_count"],
                color=CHART_TEAL,
            ),
        )
    with col_right:
        render_chart(
            "Configuracao da aeronave",
            "Distribuicao das configuracoes ativas nas auditorias.",
            make_horizontal_bar(
                tables["aircraft_configuration_summary"].head(12),
                "aircraft_configuration:N",
                "audits_count:Q",
                ["aircraft_configuration", "audits_count"],
                color=CHART_TEAL,
            ),
        )

    st.divider()

    st.markdown(
        '<div class="section-title">Analise de recorrencia</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="section-caption">'
            "Recorrencia considera auditorias que possuem nao conformidades anteriores "
            "e tambem nao conformidades atuais dentro do mesmo agrupamento."
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    recurrence_columns = [
        "audits_count",
        "current_nonconformities_count",
        "previous_nonconformities_count",
        "audits_with_current_nonconformity",
        "audits_with_previous_nonconformity",
        "recurrent_audits",
        "recurrence_rate",
    ]
    recurrence_tabs = st.tabs(["Aeronaves", "Bases", "Operadoras"])
    with recurrence_tabs[0]:
        st.dataframe(
            tables["recurrence_by_aircraft"][
                ["aircraft_prefix", *recurrence_columns]
            ].head(25),
            width="stretch",
            hide_index=True,
        )
    with recurrence_tabs[1]:
        st.dataframe(
            tables["recurrence_by_base"][
                ["base_abbreviation", "base", *recurrence_columns]
            ].head(25),
            width="stretch",
            hide_index=True,
        )
    with recurrence_tabs[2]:
        st.dataframe(
            tables["recurrence_by_operator"][
                ["operator_abbreviation", "operator", *recurrence_columns]
            ].head(25),
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ---- Tables ----
    table_columns = [
        "date",
        "auditing_type",
        "aircraft_prefix",
        "aircraft_backup_label",
        "aircraft_configuration",
        "operator_abbreviation",
        "base_abbreviation",
        "contract",
        "status",
        "nonconformity_total",
        "previous_nonconformity_total",
        "report_name",
        "audit_id",
    ]
    st.markdown(
        '<div class="section-title">Tabela de auditorias</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-caption">Base consolidada para consulta, filtro e exportacao.</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        filtered_audits[table_columns].sort_values("date", ascending=False),
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        '<div class="section-title">Tabela de nao conformidades</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-caption">Registros detalhados por ATA, area e auditoria.</div>',
        unsafe_allow_html=True,
    )
    nonconformity_columns = [
        "date",
        "ata",
        "area",
        "period",
        "aircraft_prefix",
        "operator_abbreviation",
        "base_abbreviation",
        "auditing_type",
        "report_name",
        "audit_id",
    ]
    st.dataframe(
        filtered_nonconformities[nonconformity_columns].sort_values(
            "date", ascending=False
        ),
        width="stretch",
        hide_index=True,
    )


if __name__ == "__main__":
    main()
