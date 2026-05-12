import json

import pytest

import scripts.run_pipeline as run_pipeline_module
from scripts.run_pipeline import (
    PipelineAlreadyRunningError,
    is_pipeline_locked,
    pipeline_lock,
    read_pipeline_lock,
    run_pipeline,
)


def test_pipeline_lock_creates_and_removes_lock_file(tmp_path):
    raw_dir = tmp_path / "raw"

    with pipeline_lock(raw_dir):
        assert is_pipeline_locked(raw_dir) is True
        assert read_pipeline_lock(raw_dir)["pid"] is not None

    assert is_pipeline_locked(raw_dir) is False


def test_pipeline_lock_blocks_concurrent_updates(tmp_path):
    raw_dir = tmp_path / "raw"

    with pipeline_lock(raw_dir):
        with pytest.raises(PipelineAlreadyRunningError):
            with pipeline_lock(raw_dir):
                pass


def test_run_pipeline_fetches_requested_period_and_replaces_raw_data(
    tmp_path, monkeypatch
):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True)
    (raw_dir / run_pipeline_module.fetch_audits.AUDITS_FILE).write_text(
        json.dumps([{"_id": "audit-1", "value": "old"}])
    )
    captured = {}

    class FakeFetchAudits:
        def __init__(self, output_dir):
            self.output_dir = output_dir
            self.initial_date = None
            self.final_date = None

        def set_initial_date(self, value):
            self.initial_date = value

        def set_final_date(self, value):
            self.final_date = value

        def run(self):
            captured["initial_date"] = self.initial_date
            captured["final_date"] = self.final_date
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / run_pipeline_module.fetch_audits.AUDITS_FILE).write_text(
                json.dumps(
                    [
                        {"_id": "audit-1", "value": "new"},
                        {"_id": "audit-2", "value": "added"},
                    ]
                )
            )
            (self.output_dir / run_pipeline_module.fetch_audits.REPORTS_FILE).write_text(
                json.dumps([{"_id": "audit-2", "value": "added-report"}])
            )
            (
                self.output_dir
                / run_pipeline_module.fetch_audits.AIRCRAFT_REPORTS_FILE
            ).write_text(json.dumps([{"audit_id": "audit-2", "value": "added-aircraft"}]))
            (
                self.output_dir
                / run_pipeline_module.fetch_audits.NONCONFORMITIES_CURRENT_FILE
            ).write_text(
                json.dumps(
                    [
                        {
                            "audit_id": "audit-2",
                            "area": "manutencao",
                            "period": "current",
                            "total": 1,
                            "items": ["added"],
                        }
                    ]
                )
            )
            (self.output_dir / run_pipeline_module.METADATA_FILE).write_text("{}")

    def fake_run_transform(raw_dir, processed_dir):
        processed_dir.mkdir(parents=True, exist_ok=True)
        audits = json.loads(
            (raw_dir / run_pipeline_module.fetch_audits.AUDITS_FILE).read_text()
        )
        captured["raw_audits"] = audits
        return {"kpis": {"total_audits": len(audits), "total_nonconformities": 0}}

    monkeypatch.setattr(run_pipeline_module, "FetchAudits", FakeFetchAudits)
    monkeypatch.setattr(run_pipeline_module, "run_transform", fake_run_transform)

    result = run_pipeline(
        initial_date="2025-01-01",
        final_date="2026-05-11",
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        fetch=True,
    )

    assert captured["initial_date"] == "2025-01-01"
    assert captured["final_date"] == "2026-05-11T23:59:00Z"
    assert captured["raw_audits"] == [
        {"_id": "audit-1", "value": "new"},
        {"_id": "audit-2", "value": "added"},
    ]
    assert json.loads(
        (raw_dir / run_pipeline_module.fetch_audits.AUDITS_FILE).read_text()
    ) == [
        {"_id": "audit-1", "value": "new"},
        {"_id": "audit-2", "value": "added"},
    ]
    assert result["kpis"]["total_audits"] == 2
