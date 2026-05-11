import json

import pytest

import scripts.run_pipeline as run_pipeline_module
from scripts.run_pipeline import (
    PipelineAlreadyRunningError,
    can_incremental_update,
    is_pipeline_locked,
    merge_lists_by_key,
    pipeline_lock,
    raw_data_covers_period,
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


def write_cached_raw_data(raw_dir, initial_date="2025-01-01", final_date="2026-05-10"):
    raw_dir.mkdir(parents=True)
    for filename in run_pipeline_module.RAW_FETCH_FILES:
        (raw_dir / filename).write_text("[]")

    (raw_dir / run_pipeline_module.METADATA_FILE).write_text(
        json.dumps(
            {
                "initial_date": initial_date,
                "final_date": f"{final_date}T23:59:00Z",
            }
        )
    )


def test_raw_data_covers_period_when_requested_dates_are_inside_cache(tmp_path):
    raw_dir = tmp_path / "raw"
    write_cached_raw_data(raw_dir)

    assert (
        raw_data_covers_period(
            raw_dir,
            initial_date="2025-02-01",
            final_date="2026-05-01T23:59:00Z",
        )
        is True
    )


def test_raw_data_does_not_cover_period_when_requested_final_date_is_newer(tmp_path):
    raw_dir = tmp_path / "raw"
    write_cached_raw_data(raw_dir)

    assert (
        raw_data_covers_period(
            raw_dir,
            initial_date="2025-01-01",
            final_date="2026-05-11T23:59:00Z",
        )
        is False
    )


def test_can_incremental_update_when_cache_covers_start_but_not_final_date(tmp_path):
    raw_dir = tmp_path / "raw"
    write_cached_raw_data(raw_dir)

    assert (
        can_incremental_update(
            raw_dir,
            initial_date="2025-01-01",
            final_date="2026-05-11T23:59:00Z",
        )
        is True
    )


def test_can_incremental_update_rejects_period_before_cached_start(tmp_path):
    raw_dir = tmp_path / "raw"
    write_cached_raw_data(raw_dir)

    assert (
        can_incremental_update(
            raw_dir,
            initial_date="2024-12-31",
            final_date="2026-05-11T23:59:00Z",
        )
        is False
    )


def test_merge_lists_by_key_replaces_existing_ids_and_appends_new_items():
    merged = merge_lists_by_key(
        "audits.json",
        [{"_id": "audit-1", "value": "old"}, {"_id": "audit-2", "value": "kept"}],
        [{"_id": "audit-1", "value": "new"}, {"_id": "audit-3", "value": "added"}],
    )

    assert merged == [
        {"_id": "audit-1", "value": "new"},
        {"_id": "audit-2", "value": "kept"},
        {"_id": "audit-3", "value": "added"},
    ]


def test_merge_lists_by_key_uses_nonconformity_area_period_key():
    filename = run_pipeline_module.fetch_audits.NONCONFORMITIES_CURRENT_FILE
    merged = merge_lists_by_key(
        filename,
        [
            {
                "audit_id": "audit-1",
                "area": "operacional",
                "total": 1,
                "items": ["old"],
            }
        ],
        [
            {
                "audit_id": "audit-1",
                "area": "operacional",
                "period": "current",
                "total": 2,
                "items": ["new"],
            }
        ],
    )

    assert merged == [
        {
            "audit_id": "audit-1",
            "area": "operacional",
            "period": "current",
            "total": 2,
            "items": ["new"],
        }
    ]


def test_merge_lists_by_key_drops_legacy_previous_nonconformity_payloads():
    filename = run_pipeline_module.fetch_audits.NONCONFORMITIES_CURRENT_FILE
    merged = merge_lists_by_key(
        filename,
        [
            {
                "audit_id": "audit-1",
                "area": "operacional",
                "period": "previous",
                "total": 3,
                "items": ["legacy"],
            },
            {
                "audit_id": "audit-1",
                "area": "operacional",
                "period": "current",
                "total": 1,
                "items": ["current"],
            },
        ],
        [],
    )

    assert merged == [
        {
            "audit_id": "audit-1",
            "area": "operacional",
            "period": "current",
            "total": 1,
            "items": ["current"],
        }
    ]


def test_run_pipeline_fetches_incremental_delta_and_transforms_merged_raw_data(
    tmp_path, monkeypatch
):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    write_cached_raw_data(raw_dir)
    (raw_dir / run_pipeline_module.fetch_audits.AUDITS_FILE).write_text(
        json.dumps([{"_id": "audit-1", "value": "old"}])
    )
    (raw_dir / run_pipeline_module.fetch_audits.REPORTS_FILE).write_text(
        json.dumps([{"_id": "audit-1", "value": "old-report"}])
    )
    (raw_dir / run_pipeline_module.fetch_audits.AIRCRAFT_REPORTS_FILE).write_text(
        json.dumps([{"audit_id": "audit-1", "value": "old-aircraft"}])
    )
    (
        raw_dir / run_pipeline_module.fetch_audits.NONCONFORMITIES_CURRENT_FILE
    ).write_text(
        json.dumps(
            [
                {
                    "audit_id": "audit-1",
                    "area": "operacional",
                    "period": "current",
                    "total": 1,
                    "items": ["old"],
                }
            ]
        )
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
        captured["merged_audits"] = audits
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

    assert captured["initial_date"] == "2026-05-10"
    assert captured["final_date"] == "2026-05-11T23:59:00Z"
    assert captured["merged_audits"] == [
        {"_id": "audit-1", "value": "new"},
        {"_id": "audit-2", "value": "added"},
    ]
    assert result["kpis"]["total_audits"] == 2
