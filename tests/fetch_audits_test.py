import pytest
import requests

from fetches.fetch_audits import (
    AIRCRAFT_REPORTS_FILE,
    AUDITS_FILE,
    METADATA_FILE,
    NONCONFORMITIES_CURRENT_FILE,
    REPORTS_FILE,
    REQUEST_TIMEOUT,
    FetchAudits,
    clean_api_url,
    clean_env_value,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.raise_for_status_called = False

    def json(self):
        return self.payload

    def raise_for_status(self):
        self.raise_for_status_called = True
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, post_responses=None, request_responses=None):
        self.post_responses = list(post_responses or [])
        self.request_responses = list(request_responses or [])
        self.posts = []
        self.requests = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self.post_responses.pop(0)

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.request_responses.pop(0)


def test_env_variables():
    assert FetchAudits.USERNAME is not None
    assert FetchAudits.PASSWORD is not None
    assert FetchAudits.URL is not None


def test_clean_env_value_strips_render_quotes_and_spaces():
    assert (
        clean_env_value('"https://api.rinaacc.com.br"') == "https://api.rinaacc.com.br"
    )
    assert clean_env_value(" 'secret' ") == "secret"
    assert clean_env_value(None) is None
    assert (
        clean_api_url('"https://api.rinaacc.com.br/"') == "https://api.rinaacc.com.br"
    )


def test_setters_and_initial_login_status():
    fetch_audits = FetchAudits(output_dir="custom/raw")

    fetch_audits.set_initial_date("2026-02-01")
    fetch_audits.set_final_date("2026-02-28")

    assert fetch_audits.initial_date == "2026-02-01"
    assert fetch_audits.final_date == "2026-02-28"
    assert fetch_audits.get_login_status() is False
    assert fetch_audits.get_token() is None
    assert str(fetch_audits.output_dir) == "custom/raw"


def test_validate_config_raises_for_missing_required_env(monkeypatch):
    monkeypatch.setattr(FetchAudits, "USERNAME", "")
    monkeypatch.setattr(FetchAudits, "PASSWORD", None)
    monkeypatch.setattr(FetchAudits, "URL", "https://api.example.test")

    with pytest.raises(ValueError, match="USERNAME, PASSWORD"):
        FetchAudits().validate_config()


def test_login_stores_token_and_uses_json_payload(monkeypatch):
    session = FakeSession(post_responses=[FakeResponse({"token": "token-123"})])
    monkeypatch.setattr(requests, "Session", lambda: session)

    fetch_audits = FetchAudits().login()

    assert fetch_audits.get_token() == "token-123"
    assert fetch_audits.get_login_status() is True
    assert session.posts == [
        (
            f"{FetchAudits.URL}/login",
            {
                "json": {
                    "login": FetchAudits.USERNAME,
                    "password": FetchAudits.PASSWORD,
                },
                "timeout": REQUEST_TIMEOUT,
            },
        )
    ]


def test_validate_config_returns_true_when_config_exists():
    assert FetchAudits().validate_config() is True


def test_request_with_auth_logs_in_and_retries_once_after_unauthorized(monkeypatch):
    session = FakeSession(
        request_responses=[
            FakeResponse({"message": "unauthorized"}, status_code=401),
            FakeResponse({"ok": True}),
        ]
    )
    fetch_audits = FetchAudits()
    login_calls = []

    def fake_login():
        login_calls.append(True)
        fetch_audits._FetchAudits__token = f"token-{len(login_calls)}"
        return fetch_audits

    monkeypatch.setattr(fetch_audits, "get_session", lambda: session)
    monkeypatch.setattr(fetch_audits, "login", fake_login)

    response = fetch_audits.request_with_auth("GET", "/resource")

    assert response.json() == {"ok": True}
    assert len(login_calls) == 2
    assert session.requests == [
        (
            "GET",
            f"{FetchAudits.URL}/resource",
            {"headers": {"Authorization": "token-1"}, "timeout": REQUEST_TIMEOUT},
        ),
        (
            "GET",
            f"{FetchAudits.URL}/resource",
            {"headers": {"Authorization": "token-2"}, "timeout": REQUEST_TIMEOUT},
        ),
    ]


def test_save_load_response_and_save_reports_write_json(tmp_path):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")

    fetch_audits.save_response([{"_id": "audit-1"}])
    fetch_audits.save_reports([{"reportName": "report-1"}])

    assert fetch_audits.load_json(AUDITS_FILE) == [{"_id": "audit-1"}]
    assert fetch_audits.load_json(REPORTS_FILE) == [{"reportName": "report-1"}]


def test_get_all_id_audits_returns_only_existing_ids():
    response_json = [
        {"_id": "audit1", "name": "Audit 1"},
        {"_id": "audit2", "name": "Audit 2"},
        {"name": "Audit 3"},
    ]

    ids = FetchAudits().get_all_id_audits(response_json)

    assert ids == ["audit1", "audit2"]


def test_get_all_aircraft_report_ids_returns_audit_ids():
    audits = [
        {"_id": "audit-1"},
        {"_id": "audit-2"},
        {"name": "missing-id"},
    ]

    ids = FetchAudits().get_all_aircraft_report_ids(audits)

    assert ids == ["audit-1", "audit-2"]


def test_get_all_aircraft_prefixes_extracts_strings_and_uses_cache(monkeypatch):
    fetch_audits = FetchAudits()
    calls = []

    def fake_request_with_auth(method, path):
        calls.append((method, path))
        return FakeResponse(
            {
                "aircrafts": [
                    {"prefix": "PR-AAA"},
                    {"prefix": ""},
                    "PR-BBB",
                    {"serial_number": "without-prefix"},
                ]
            }
        )

    monkeypatch.setattr(fetch_audits, "request_with_auth", fake_request_with_auth)

    assert fetch_audits.get_all_aircraft_prefixes() == ["PR-AAA", "PR-BBB"]
    assert fetch_audits.get_all_aircraft_prefixes() == ["PR-AAA", "PR-BBB"]
    assert calls == [("GET", "/aircraft/get-all?limit=300")]


def test_get_all_aircraft_prefixes_falls_back_when_request_fails(monkeypatch):
    fetch_audits = FetchAudits()

    def fake_request_with_auth(method, path):
        raise requests.RequestException("network unavailable")

    monkeypatch.setattr(fetch_audits, "request_with_auth", fake_request_with_auth)

    prefixes = fetch_audits.get_all_aircraft_prefixes()

    assert "PP-NLX" in prefixes
    assert "PT-SHO" in prefixes


def test_build_search_payload_respects_date_filters_and_prefixes(monkeypatch):
    fetch_audits = FetchAudits()
    fetch_audits.set_initial_date("2026-05-01")
    fetch_audits.set_final_date("2026-05-10")
    monkeypatch.setattr(fetch_audits, "get_all_aircraft_prefixes", lambda: ["PR-AAA"])

    payload = fetch_audits.build_search_payload()

    assert payload["initialDateDoc"] == "2026-05-01"
    assert payload["finalDateDoc"] == "2026-05-10"
    assert payload["aircraftPrefix"] == ["PR-AAA"]
    assert payload["base"] == FetchAudits.BASES
    assert payload["operator"] == FetchAudits.OPERATORS
    assert payload["auditingType"] == FetchAudits.AUDITING_TYPES


def test_fetch_audits_builds_payload_saves_response_and_returns_list(
    tmp_path, monkeypatch
):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")
    captured = {}

    monkeypatch.setattr(
        fetch_audits, "get_all_aircraft_prefixes", lambda: ["PR-AAA", "PR-BBB"]
    )

    def fake_request_with_auth(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return FakeResponse([{"_id": "audit-1"}])

    monkeypatch.setattr(fetch_audits, "request_with_auth", fake_request_with_auth)

    audits = fetch_audits.fetch_audits()

    assert audits == [{"_id": "audit-1"}]
    assert captured["method"] == "POST"
    assert captured["path"] == "/search"
    assert captured["json"]["aircraftPrefix"] == ["PR-AAA", "PR-BBB"]
    assert captured["json"]["initialDateDoc"] == "2026-01-01"
    assert fetch_audits.load_json(AUDITS_FILE) == audits


def test_fetch_audits_returns_empty_list_when_api_returns_message(
    tmp_path, monkeypatch
):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")

    monkeypatch.setattr(fetch_audits, "get_all_aircraft_prefixes", lambda: ["PR-AAA"])
    monkeypatch.setattr(
        fetch_audits,
        "request_with_auth",
        lambda method, path, **kwargs: FakeResponse({"message": "Nenhum registro"}),
    )

    assert fetch_audits.fetch_audits() == []
    assert fetch_audits.load_json(AUDITS_FILE) == []


def test_fetch_audit_by_id_requests_report_endpoint(monkeypatch):
    fetch_audits = FetchAudits()
    calls = []

    def fake_request_with_auth(method, path):
        calls.append((method, path))
        return FakeResponse({"_id": "audit-1", "reportName": "Report"})

    monkeypatch.setattr(fetch_audits, "request_with_auth", fake_request_with_auth)

    assert fetch_audits.fetch_audit_by_id("audit-1") == {
        "_id": "audit-1",
        "reportName": "Report",
    }
    assert calls == [("GET", "/report/audit-1")]


def test_fetch_aircraft_report_by_id_requests_aircraft_report_endpoint_with_audit_id(
    monkeypatch,
):
    fetch_audits = FetchAudits()
    calls = []

    def fake_request_with_auth(method, path):
        calls.append((method, path))
        return FakeResponse({"_id": "aircraft-report-1", "backup": True})

    monkeypatch.setattr(fetch_audits, "request_with_auth", fake_request_with_auth)

    assert fetch_audits.fetch_aircraft_report_by_id("audit-1") == {
        "_id": "aircraft-report-1",
        "backup": True,
    }
    assert calls == [("GET", "/aircraftReport/audit-1")]


def test_build_metadata_describes_saved_outputs(tmp_path):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")
    fetch_audits.set_initial_date("2026-03-01")
    fetch_audits.set_final_date("2026-03-31")

    metadata = fetch_audits.build_metadata(
        audits=[{"_id": "audit-1"}],
        reports=[{"_id": "audit-1"}, {"_id": "audit-2"}],
        aircraft_reports=[{"_id": "aircraft-report-1"}],
    )

    assert metadata["initial_date"] == "2026-03-01"
    assert metadata["final_date"] == "2026-03-31"
    assert metadata["audits_count"] == 1
    assert metadata["reports_count"] == 2
    assert metadata["aircraft_reports_count"] == 1
    assert metadata["audits_file"].endswith(AUDITS_FILE)
    assert metadata["reports_file"].endswith(REPORTS_FILE)
    assert metadata["aircraft_reports_file"].endswith(AIRCRAFT_REPORTS_FILE)
    assert metadata["nonconformities_current_file"].endswith(
        NONCONFORMITIES_CURRENT_FILE
    )


def test_fetch_all_nonconformities_current_fetches_each_area_and_saves(
    tmp_path, monkeypatch
):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")

    monkeypatch.setattr(
        fetch_audits,
        "fetch_nonconformity",
        lambda audit_id, area, period: {
            "audit_id": audit_id,
            "area": area,
            "period": period,
            "total": 1 if area == "manutencao" else 0,
            "items": [],
        },
    )

    results = fetch_audits.fetch_all_nonconformities_current(
        [{"_id": "audit-1"}, {"_id": "audit-2"}]
    )

    assert results == [
        {
            "audit_id": "audit-1",
            "area": "operacional",
            "period": "current",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-1",
            "area": "manutencao",
            "period": "current",
            "total": 1,
            "items": [],
        },
        {
            "audit_id": "audit-1",
            "area": "operacional",
            "period": "previous",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-1",
            "area": "manutencao",
            "period": "previous",
            "total": 1,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "operacional",
            "period": "current",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "manutencao",
            "period": "current",
            "total": 1,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "operacional",
            "period": "previous",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "manutencao",
            "period": "previous",
            "total": 1,
            "items": [],
        },
    ]
    assert fetch_audits.load_json(NONCONFORMITIES_CURRENT_FILE) == results


def test_fetch_all_reports_fetches_each_audit_report_and_saves(tmp_path, monkeypatch):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")

    monkeypatch.setattr(
        fetch_audits,
        "fetch_audits",
        lambda: [{"_id": "audit-1"}, {"_id": "audit-2"}, {"name": "missing-id"}],
    )
    monkeypatch.setattr(
        fetch_audits,
        "fetch_audit_by_id",
        lambda audit_id: {"_id": audit_id, "reportName": f"report-{audit_id}"},
    )

    reports = fetch_audits.fetch_all_reports()

    assert reports == [
        {"_id": "audit-1", "reportName": "report-audit-1"},
        {"_id": "audit-2", "reportName": "report-audit-2"},
    ]
    assert fetch_audits.load_json(REPORTS_FILE) == reports


def test_fetch_all_aircraft_reports_fetches_each_aircraft_report_and_saves(
    tmp_path, monkeypatch
):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")

    monkeypatch.setattr(
        fetch_audits,
        "fetch_aircraft_report_by_id",
        lambda audit_id: {
            "_id": f"aircraft-report-{audit_id}",
            "backup": audit_id.endswith("1"),
        },
    )

    aircraft_reports = fetch_audits.fetch_all_aircraft_reports(
        [
            {"_id": "audit-1"},
            {"_id": "audit-2"},
            {"name": "missing-id"},
        ]
    )

    assert aircraft_reports == [
        {"_id": "aircraft-report-audit-1", "backup": True, "audit_id": "audit-1"},
        {"_id": "aircraft-report-audit-2", "backup": False, "audit_id": "audit-2"},
    ]
    assert fetch_audits.load_json(AIRCRAFT_REPORTS_FILE) == aircraft_reports


def test_run_fetches_filtered_audits_reports_and_metadata(tmp_path, monkeypatch):
    fetch_audits = FetchAudits(output_dir=tmp_path / "raw")
    fetch_audits.set_initial_date("2026-04-01")
    fetch_audits.set_final_date("2026-04-30")

    monkeypatch.setattr(
        fetch_audits,
        "fetch_audits",
        lambda: [{"_id": "audit-1"}, {"_id": "audit-2"}],
    )
    monkeypatch.setattr(
        fetch_audits,
        "fetch_audit_by_id",
        lambda audit_id: {
            "_id": audit_id,
            "reportName": f"report-{audit_id}",
        },
    )
    monkeypatch.setattr(
        fetch_audits,
        "fetch_aircraft_report_by_id",
        lambda audit_id: {"_id": f"aircraft-report-{audit_id}", "backup": False},
    )
    monkeypatch.setattr(
        fetch_audits,
        "fetch_all_nonconformities_current",
        lambda audits: save_and_return_nonconformities(fetch_audits),
    )

    result = fetch_audits.run()

    assert result["audits"] == [{"_id": "audit-1"}, {"_id": "audit-2"}]
    assert result["reports"] == [
        {
            "_id": "audit-1",
            "reportName": "report-audit-1",
        },
        {
            "_id": "audit-2",
            "reportName": "report-audit-2",
        },
    ]
    assert result["aircraft_reports"] == [
        {"_id": "aircraft-report-audit-1", "backup": False, "audit_id": "audit-1"},
        {"_id": "aircraft-report-audit-2", "backup": False, "audit_id": "audit-2"},
    ]
    assert len(result["nonconformities"]) == 8
    assert result["metadata"]["initial_date"] == "2026-04-01"
    assert result["metadata"]["final_date"] == "2026-04-30"
    assert fetch_audits.load_json(REPORTS_FILE) == result["reports"]
    assert fetch_audits.load_json(AIRCRAFT_REPORTS_FILE) == result["aircraft_reports"]
    assert (
        fetch_audits.load_json(NONCONFORMITIES_CURRENT_FILE)
        == result["nonconformities"]
    )
    assert fetch_audits.load_json(METADATA_FILE) == result["metadata"]


def save_and_return_nonconformities(fetch_audits):
    results = [
        {
            "audit_id": "audit-1",
            "area": "operacional",
            "period": "current",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-1",
            "area": "manutencao",
            "period": "current",
            "total": 1,
            "items": [],
        },
        {
            "audit_id": "audit-1",
            "area": "operacional",
            "period": "previous",
            "total": 1,
            "items": [],
        },
        {
            "audit_id": "audit-1",
            "area": "manutencao",
            "period": "previous",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "operacional",
            "period": "current",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "manutencao",
            "period": "current",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "operacional",
            "period": "previous",
            "total": 0,
            "items": [],
        },
        {
            "audit_id": "audit-2",
            "area": "manutencao",
            "period": "previous",
            "total": 0,
            "items": [],
        },
    ]
    fetch_audits.save_nonconformities_current(results)
    return results
