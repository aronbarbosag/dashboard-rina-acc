import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import local
from time import perf_counter, sleep

import requests
from dotenv import load_dotenv

load_dotenv()


def get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


REQUEST_TIMEOUT = max(5, get_int_env("REQUEST_TIMEOUT", 30))
REQUEST_RETRIES = max(0, get_int_env("REQUEST_RETRIES", 2))
RETRY_BACKOFF_SECONDS = 0.5
RETRY_STATUS_CODES = {429, 502, 503, 504}
MAX_REPORT_WORKERS = max(1, get_int_env("MAX_REPORT_WORKERS", 16))
DEFAULT_RAW_DIR = Path("data/raw")
AUDITS_FILE = "audits.json"
REPORTS_FILE = "audit_reports.json"
AIRCRAFT_REPORTS_FILE = "aircraft_reports.json"
METADATA_FILE = "fetch_metadata.json"
NONCONFORMITIES_CURRENT_FILE = "nonconformities_current.json"
ACCOMPANIMENTS_CURRENT_FILE = "accompaniments_current.json"


def clean_env_value(value):
    if value is None:
        return None

    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()

    return value


def clean_api_url(value):
    value = clean_env_value(value)
    if not value:
        return value

    return value.rstrip("/")


class FetchAudits:
    USERNAME = clean_env_value(os.getenv("USERNAME"))
    PASSWORD = clean_env_value(os.getenv("PASSWORD"))
    URL = clean_api_url(os.getenv("API_URL"))
    BASES = [
        "AJU",
        "BEL",
        "BJP",
        "CFB",
        "CAW",
        "SNAO",
        "CIZ",
        "FST",
        "FOR",
        "GIG",
        "GMR",
        "ITA",
        "JPA",
        "MCP",
        "MEA",
        "MAO",
        "MRC",
        "OIA",
        "PRC",
        "PUC",
        "RAO",
        "SSA",
        "TST",
        "VIX",
    ]
    OPERATORS = [
        "AEROLEO",
        "AZUL",
        "BRISTOW",
        "CHC",
        "CDS",
        "FOTOTERRA",
        "LIDER",
        "OMNI",
        "RICO",
        "TOTAL",
        "TREINAMENTO",
        "VOE",
    ]
    AUDITING_TYPES = ["ACCI", "RMNR", "ACCD", "Extra", "ACC"]
    NONCONFORMITY_CURRENT_ROUTES = {
        "operacional": "/nonconformityOprReportListCurrent/{audit_id}",
        "manutencao": "/nonconformityMntReportListCurrent/{audit_id}",
    }
    NONCONFORMITY_CURRENT_KEYS = {
        "operacional": "nonconformityOpr",
        "manutencao": "nonconformityMnt",
    }
    NONCONFORMITY_PREVIOUS_ROUTES = {
        "operacional": "/nonconformityOprReportListPrevious/{audit_id}",
        "manutencao": "/nonconformityMntReportListPrevious/{audit_id}",
    }
    NONCONFORMITY_PREVIOUS_KEYS = {
        "operacional": "nonconformityOpr",
        "manutencao": "nonconformityMnt",
    }
    ACCOMPANIMENT_CURRENT_ROUTE = "/accompanimentReport/{accompaniment_id}"

    def __init__(self, output_dir=DEFAULT_RAW_DIR):

        self.output_dir = Path(output_dir)
        self.__token = None
        self.__login_status = False
        self.initial_date = "2025-01-01"
        self.final_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        self.audit_id = None
        self._aircraft_prefixes = None
        self._thread_local = local()
        self._timings = {}

    def set_initial_date(self, initial_date):
        self.initial_date = initial_date

    def set_final_date(self, final_date):
        self.final_date = final_date

    def get_login_status(self):
        return self.__login_status

    def get_token(self):

        return self.__token

    def validate_config(self):
        missing = [
            name
            for name, value in {
                "USERNAME": FetchAudits.USERNAME,
                "PASSWORD": FetchAudits.PASSWORD,
                "API_URL": FetchAudits.URL,
            }.items()
            if not value
        ]

        if missing:
            missing_variables = ", ".join(missing)
            raise ValueError(
                f"Missing required environment variables: {missing_variables}"
            )

        return True

    def login(self):
        self.validate_config()
        data = {
            "login": FetchAudits.USERNAME,
            "password": FetchAudits.PASSWORD,
        }
        response = self.post_with_retries(f"{FetchAudits.URL}/login", json=data)
        response.raise_for_status()

        token = response.json().get("token")

        self.__token = token
        self.__login_status = token is not None

        return self

    def get_session(self):
        if not hasattr(self._thread_local, "session"):
            self._thread_local.session = requests.Session()

        return self._thread_local.session

    def should_retry_response(self, response):
        return response.status_code in RETRY_STATUS_CODES

    def sleep_before_retry(self, attempt):
        sleep(RETRY_BACKOFF_SECONDS * attempt)

    def post_with_retries(self, url, **kwargs):
        last_error = None
        session = self.get_session()

        for attempt in range(1, REQUEST_RETRIES + 2):
            try:
                response = session.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
            except (requests.Timeout, requests.ConnectionError) as error:
                last_error = error
            else:
                if not self.should_retry_response(response):
                    return response

                last_error = requests.HTTPError(f"HTTP {response.status_code}")

            if attempt <= REQUEST_RETRIES:
                self.sleep_before_retry(attempt)

        if last_error:
            raise last_error

        raise requests.RequestException("Request failed without a response.")

    def request_with_retries(self, method, path, **kwargs):
        last_error = None
        session = self.get_session()

        for attempt in range(1, REQUEST_RETRIES + 2):
            try:
                response = session.request(
                    method,
                    f"{FetchAudits.URL}{path}",
                    timeout=REQUEST_TIMEOUT,
                    **kwargs,
                )
            except (requests.Timeout, requests.ConnectionError) as error:
                last_error = error
            else:
                if not self.should_retry_response(response):
                    return response

                last_error = requests.HTTPError(f"HTTP {response.status_code}")

            if attempt <= REQUEST_RETRIES:
                self.sleep_before_retry(attempt)

        if last_error:
            raise last_error

        raise requests.RequestException("Request failed without a response.")

    def request_with_auth(self, method, path, **kwargs):
        if self.get_token() is None:
            self.login()

        response = self.request_with_retries(
            method,
            path,
            headers={"Authorization": f"{self.get_token()}"},
            **kwargs,
        )

        if response.status_code == 401:
            self.login()
            response = self.request_with_retries(
                method,
                path,
                headers={"Authorization": f"{self.get_token()}"},
                **kwargs,
            )

        response.raise_for_status()
        return response

    def get_output_path(self, filename):
        return self.output_dir / filename

    def save_json(self, filename, data):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with self.get_output_path(filename).open("w") as f:
            json.dump(data, f, indent=4)

    def load_json(self, filename):
        with self.get_output_path(filename).open("r") as f:
            return json.load(f)

    def save_response(self, response_json):
        self.save_json(AUDITS_FILE, response_json)

    def get_all_id_audits(self, response_json):
        return [audit.get("_id") for audit in response_json if "_id" in audit]

    def get_all_aircraft_report_ids(self, audits):
        return self.get_all_id_audits(audits)

    def get_all_aircraft_prefixes(self):
        if self._aircraft_prefixes is not None:
            return self._aircraft_prefixes

        try:
            response = self.request_with_auth("GET", "/aircraft/get-all?limit=300")
            aircrafts = response.json().get("aircrafts", [])
            self._aircraft_prefixes = [
                aircraft.get("prefix") if isinstance(aircraft, dict) else aircraft
                for aircraft in aircrafts
            ]
            self._aircraft_prefixes = [
                prefix for prefix in self._aircraft_prefixes if prefix
            ]
        except requests.RequestException:
            self._aircraft_prefixes = []

        if not self._aircraft_prefixes:
            return [
                "PP-NLX",
                "PR-AEH",
                "PR-AEK",
                "PR-AEV",
                "PR-AIE",
                "PR-AIF",
                "PR-AIG",
                "PR-AQH",
                "PR-AQJ",
                "PR-AQZ",
                "PR-BGB",
                "PR-BGC",
                "PR-BGG",
                "PR-BGJ",
                "PR-BGM",
                "PR-BGN",
                "PR-BGP",
                "PR-BGQ",
                "PR-BGT",
                "PR-BGU",
                "PR-BGX",
                "PR-BGY",
                "PR-BGZ",
                "PR-CDV",
                "PR-CFX",
                "PR-CGD",
                "PR-CGE",
                "PR-CGF",
                "PR-CGH",
                "PR-CGJ",
                "PR-CGK",
                "PR-CGN",
                "PR-CGO",
                "PR-CGP",
                "PR-CGS",
                "PR-CGT",
                "PR-CGU",
                "PR-CGW",
                "PR-CHA",
                "PR-CHC",
                "PR-CHD",
                "PR-CHE",
                "PR-CHG",
                "PR-CHI",
                "PR-CHQ",
                "PR-CHS",
                "PR-CHT",
                "PR-CPV",
                "PR-CPX",
                "PR-EFX",
                "PR-EPV",
                "PR-JAA",
                "PR-JAR",
                "PR-JAW",
                "PR-JBE",
                "PR-JBI",
                "PR-JBK",
                "PR-JBO",
                "PR-JBP",
                "PR-JBQ",
                "PR-JBU",
                "PR-JBX",
                "PR-JHA",
                "PR-JHC",
                "PR-JHD",
                "PR-JHE",
                "PR-JHG",
                "PR-JHH",
                "PR-JHI",
                "PR-JKC",
                "PR-JKE",
                "PR-JKJ",
                "PR-JKK",
                "PR-JKM",
                "PR-LBA",
                "PR-LCD",
                "PR-LCH",
                "PR-LCO",
                "PR-LCP",
                "PR-LCQ",
                "PR-LCR",
                "PR-LCT",
                "PR-LCV",
                "PR-LCZ",
                "PR-LDC",
                "PR-LDE",
                "PR-LDG",
                "PR-LDT",
                "PR-LDV",
                "PR-LDW",
                "PR-LDZ",
                "PR-MEO",
                "PR-MEP",
                "PR-MEX",
                "PR-MEZ",
                "PR-MLL",
                "PR-MPN",
                "PR-MPO",
                "PR-MPY",
                "PR-MPZ",
                "PR-MRT",
                "PR-NLN",
                "PR-NSP",
                "PR-OFC",
                "PR-OFD",
                "PR-OFE",
                "PR-OFH",
                "PR-OFJ",
                "PR-OFK",
                "PR-OFL",
                "PR-OHA",
                "PR-OHB",
                "PR-OHC",
                "PR-OHD",
                "PR-OHE",
                "PR-OHF",
                "PR-OHG",
                "PR-OHI",
                "PR-OHJ",
                "PR-OHK",
                "PR-OHL",
                "PR-OHN",
                "PR-OHO",
                "PR-OHP",
                "PR-OHQ",
                "PR-OHR",
                "PR-OHS",
                "PR-OHU",
                "PR-OHV",
                "PR-OHX",
                "PR-OHY",
                "PR-OHZ",
                "PR-OMA",
                "PR-OMB",
                "PR-OMH",
                "PR-OMK",
                "PR-OMT",
                "PR-OMY",
                "PR-OOA",
                "PR-OOB",
                "PR-OOC",
                "PR-OOG",
                "PR-OOI",
                "PR-OOL",
                "PR-OOM",
                "PR-OON",
                "PR-OOP",
                "PR-OOQ",
                "PR-OOR",
                "PR-OOS",
                "PR-OOT",
                "PR-OOU",
                "PR-OOV",
                "PR-OOW",
                "PR-OOX",
                "PR-OOY",
                "PR-OTD",
                "PR-OTF",
                "PR-OTH",
                "PR-OTI",
                "PR-OTN",
                "PR-OTP",
                "PR-OTQ",
                "PR-OTR",
                "PR-OTS",
                "PR-OTU",
                "PR-OTW",
                "PR-OTX",
                "PR-OTY",
                "PR-PDP",
                "PR-PDS",
                "PR-PDT",
                "PR-PMS",
                "PR-SEC",
                "PR-SED",
                "PR-SEE",
                "PR-SEF",
                "PR-SEO",
                "PR-SES",
                "PR-SET",
                "PR-SEU",
                "PR-SHL",
                "PR-TTK",
                "PR-WSG",
                "PR-YXB",
                "PR-YXT",
                "PS-BTA",
                "PS-BTB",
                "PS-BTC",
                "PS-BTD",
                "PS-BTF",
                "PS-BTJ",
                "PS-BTK",
                "PS-BTL",
                "PS-BTO",
                "PS-BTP",
                "PS-BTW",
                "PS-CDR",
                "PS-CDT",
                "PS-CDU",
                "PS-CDV",
                "PS-CDW",
                "PS-CPU",
                "PS-FCB",
                "PS-GBN",
                "PS-GBP",
                "PS-LSC",
                "PS-MSV",
                "PT-GAD",
                "PT-GAX",
                "PT-MFE",
                "PT-OCV",
                "PT-SHO",
            ]

        return self._aircraft_prefixes

    def build_search_payload(self):
        return {
            "base": self.BASES,
            "operator": self.OPERATORS,
            "aircraftPrefix": self.get_all_aircraft_prefixes(),
            "auditingType": self.AUDITING_TYPES,
            "contract": "",
            "reportName": "",
            "ata": None,
            "initialDateDoc": self.initial_date,
            "finalDateDoc": self.final_date,
            "initialDatePub": None,
            "finalDatePub": None,
        }

    def fetch_audits(self):

        data = self.build_search_payload()

        response = self.request_with_auth("POST", "/search", json=data)

        response_json = response.json()

        if isinstance(response_json, dict) and response_json.get("message"):
            response_json = []

        self.save_response(response_json)

        return response_json

    def fetch_audit_by_id(self, audit_id):

        response = self.request_with_auth("GET", f"/report/{audit_id}")

        return response.json()

    def fetch_aircraft_report_by_id(self, audit_id):

        response = self.request_with_auth("GET", f"/aircraftReport/{audit_id}")

        return response.json()

    def save_reports(self, reports):
        self.save_json(REPORTS_FILE, reports)

    def save_aircraft_reports(self, aircraft_reports):
        self.save_json(AIRCRAFT_REPORTS_FILE, aircraft_reports)

    def save_nonconformities_current(self, nonconformities):
        self.save_json(NONCONFORMITIES_CURRENT_FILE, nonconformities)

    def save_accompaniments_current(self, accompaniments):
        self.save_json(ACCOMPANIMENTS_CURRENT_FILE, accompaniments)

    def build_metadata(
        self,
        audits,
        reports,
        aircraft_reports=None,
        accompaniments=None,
        timings=None,
    ):
        aircraft_reports = aircraft_reports or []
        accompaniments = accompaniments or []
        timings = timings or {}
        audits_count = len(audits)
        return {
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
            "initial_date": self.initial_date,
            "final_date": self.final_date,
            "audits_count": audits_count,
            "reports_count": len(reports),
            "aircraft_reports_count": len(aircraft_reports),
            "accompaniments_current_count": len(accompaniments),
            "estimated_request_count": 2 + (audits_count * 4) + len(accompaniments),
            "max_report_workers": MAX_REPORT_WORKERS,
            "request_timeout": REQUEST_TIMEOUT,
            "request_retries": REQUEST_RETRIES,
            "timings_seconds": timings,
            "audits_file": str(self.get_output_path(AUDITS_FILE)),
            "reports_file": str(self.get_output_path(REPORTS_FILE)),
            "aircraft_reports_file": str(self.get_output_path(AIRCRAFT_REPORTS_FILE)),
            "nonconformities_current_file": str(
                self.get_output_path(NONCONFORMITIES_CURRENT_FILE)
            ),
            "accompaniments_current_file": str(
                self.get_output_path(ACCOMPANIMENTS_CURRENT_FILE)
            ),
        }

    def _extract_nonconformity_items(self, response_json, key):
        if isinstance(response_json, dict):
            items = response_json.get(key)
            if items is None:
                items = response_json.get("items") or response_json.get("data") or []
            total = response_json.get("total")
        elif isinstance(response_json, list):
            items = response_json
            total = None
        else:
            items = []
            total = None

        if not isinstance(items, list):
            items = []

        if total is None:
            total = len(items)

        return items, total

    def fetch_nonconformity(self, audit_id, area, period):
        if period == "previous":
            route = self.NONCONFORMITY_PREVIOUS_ROUTES[area]
            key = self.NONCONFORMITY_PREVIOUS_KEYS[area]
        else:
            route = self.NONCONFORMITY_CURRENT_ROUTES[area]
            key = self.NONCONFORMITY_CURRENT_KEYS[area]
        response = self.request_with_auth("GET", route.format(audit_id=audit_id))
        response_json = response.json()
        items, total = self._extract_nonconformity_items(response_json, key)

        return {
            "audit_id": audit_id,
            "area": area,
            "period": period,
            "total": total,
            "items": items,
        }

    def _fetch_nonconformity_task(self, task):
        audit_id, area, period = task
        return self.fetch_nonconformity(audit_id, area, period)

    def fetch_all_nonconformities_current(self, audits):
        audit_ids = self.get_all_id_audits(audits)
        tasks = [
            (audit_id, area, "current")
            for audit_id in audit_ids
            for area in self.NONCONFORMITY_CURRENT_ROUTES
        ]
        with ThreadPoolExecutor(max_workers=MAX_REPORT_WORKERS) as executor:
            results = list(executor.map(self._fetch_nonconformity_task, tasks))

        self.save_nonconformities_current(results)
        return results

    def fetch_accompaniment(self, audit_id, accompaniment_id):
        response = self.request_with_auth(
            "GET",
            self.ACCOMPANIMENT_CURRENT_ROUTE.format(accompaniment_id=accompaniment_id),
        )
        item = response.json()
        if isinstance(item, dict):
            item.setdefault("_id", accompaniment_id)

        return {
            "audit_id": audit_id,
            "period": "current",
            "item": item,
        }

    def _fetch_accompaniment_task(self, task):
        audit_id, accompaniment_id = task
        return self.fetch_accompaniment(audit_id, accompaniment_id)

    def get_current_accompaniment_tasks(self, reports):
        tasks = []
        for report in reports:
            if not isinstance(report, dict):
                continue

            audit_id = report.get("_id")
            accompaniment_ids = report.get("_accompaniment") or []
            if not audit_id or not isinstance(accompaniment_ids, list):
                continue

            tasks.extend(
                (audit_id, accompaniment_id)
                for accompaniment_id in accompaniment_ids
                if accompaniment_id
            )

        return tasks

    def fetch_all_accompaniments_current(self, reports):
        tasks = self.get_current_accompaniment_tasks(reports)
        with ThreadPoolExecutor(max_workers=MAX_REPORT_WORKERS) as executor:
            results = list(executor.map(self._fetch_accompaniment_task, tasks))

        self.save_accompaniments_current(results)
        return results

    def fetch_all_reports(self):
        audits = self.fetch_audits()
        audit_ids = self.get_all_id_audits(audits)
        with ThreadPoolExecutor(max_workers=MAX_REPORT_WORKERS) as executor:
            reports = list(executor.map(self.fetch_audit_by_id, audit_ids))

        self.save_reports(reports)

        return reports

    def fetch_all_aircraft_reports(self, audits):
        aircraft_report_ids = self.get_all_aircraft_report_ids(audits)
        with ThreadPoolExecutor(max_workers=MAX_REPORT_WORKERS) as executor:
            aircraft_reports = list(
                executor.map(self.fetch_aircraft_report_by_id, aircraft_report_ids)
            )

        for audit_id, aircraft_report in zip(aircraft_report_ids, aircraft_reports):
            if isinstance(aircraft_report, dict):
                aircraft_report.setdefault("audit_id", audit_id)

        self.save_aircraft_reports(aircraft_reports)

        return aircraft_reports

    def run(self):
        total_started_at = perf_counter()
        timings = {}

        phase_started_at = perf_counter()
        audits = self.fetch_audits()
        timings["search"] = round(perf_counter() - phase_started_at, 3)

        audit_ids = self.get_all_id_audits(audits)
        phase_started_at = perf_counter()
        with ThreadPoolExecutor(max_workers=MAX_REPORT_WORKERS) as executor:
            reports = list(executor.map(self.fetch_audit_by_id, audit_ids))
        timings["reports"] = round(perf_counter() - phase_started_at, 3)

        phase_started_at = perf_counter()
        self.save_reports(reports)
        timings["save_reports"] = round(perf_counter() - phase_started_at, 3)

        phase_started_at = perf_counter()
        aircraft_reports = self.fetch_all_aircraft_reports(audits)
        timings["aircraft_reports"] = round(perf_counter() - phase_started_at, 3)

        phase_started_at = perf_counter()
        nonconformities = self.fetch_all_nonconformities_current(audits)
        timings["nonconformities"] = round(perf_counter() - phase_started_at, 3)

        phase_started_at = perf_counter()
        accompaniments = self.fetch_all_accompaniments_current(reports)
        timings["accompaniments"] = round(perf_counter() - phase_started_at, 3)

        timings["total"] = round(perf_counter() - total_started_at, 3)
        self._timings = timings

        metadata = self.build_metadata(
            audits,
            reports,
            aircraft_reports,
            accompaniments,
            timings=timings,
        )
        self.save_json(METADATA_FILE, metadata)

        return {
            "audits": audits,
            "reports": reports,
            "aircraft_reports": aircraft_reports,
            "nonconformities": nonconformities,
            "accompaniments": accompaniments,
            "metadata": metadata,
        }
