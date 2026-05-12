import os
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

pipeline = import_module("scripts.run_pipeline")
transform_audits = import_module("transforms.transform_audits")

AUDITS_PROCESSED_FILE = transform_audits.AUDITS_PROCESSED_FILE
KPIS_FILE = transform_audits.KPIS_FILE
NONCONFORMITIES_PROCESSED_FILE = transform_audits.NONCONFORMITIES_PROCESSED_FILE
PROCESSED_DIR = transform_audits.PROCESSED_DIR
build_analysis_tables = transform_audits.build_analysis_tables
build_kpis = transform_audits.build_kpis

RAW_DIR = Path("data/raw")
FETCH_METADATA_FILE = RAW_DIR / "fetch_metadata.json"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo-rina.png"
FAVICON_PATH = PROJECT_ROOT / "assets" / "favicon.png"
LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
DEFAULT_FETCH_START_DATE = datetime(2025, 1, 1).date()

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

CHART_TEAL = "#139a8f"
CHART_GOLD = "#d89c22"
CHART_RED = "#d65f5f"
CHART_PURPLE = "#7c5cc4"
CHART_HEIGHT = 320

DEFAULT_DASHBOARD_USERNAME = "rina"
DEFAULT_DASHBOARD_PASSWORD = "rina@2026"
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", DEFAULT_DASHBOARD_USERNAME)
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", DEFAULT_DASHBOARD_PASSWORD)
