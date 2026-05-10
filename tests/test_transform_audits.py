import json

import pandas as pd

from transforms.transform_audits import (
    AIRCRAFT_BACKUP_SUMMARY_FILE,
    AIRCRAFT_CONFIGURATION_SUMMARY_FILE,
    AIRCRAFT_RANKING_FILE,
    AIRCRAFT_REPORTS_RAW_FILE,
    ATA_RANKING_FILE,
    AUDITS_BY_MONTH_FILE,
    AUDITS_BY_TYPE_FILE,
    AUDITS_PROCESSED_FILE,
    AUDITS_RAW_FILE,
    BASE_TYPE_HEATMAP_FILE,
    KPIS_FILE,
    MONTHLY_NONCONFORMITY_RATE_FILE,
    NONCONFORMITIES_BY_AREA_FILE,
    NONCONFORMITIES_BY_BASE_FILE,
    NONCONFORMITIES_BY_MONTH_FILE,
    NONCONFORMITIES_BY_OPERATOR_FILE,
    NONCONFORMITIES_PROCESSED_FILE,
    RECURRENCE_BY_AIRCRAFT_FILE,
    RECURRENCE_BY_BASE_FILE,
    RECURRENCE_BY_OPERATOR_FILE,
    REPORTS_RAW_FILE,
    build_analysis_tables,
    build_audits_dataframe,
    build_kpis,
    build_nonconformities_dataframe,
    count_items,
    get_active_aircraft_configuration,
    load_json,
    normalize_nonconformity_item,
    run_transform,
    save_json,
)


def sample_audits():
    return [
        {
            "_id": "audit-1",
            "reportName": "REPORT-1",
            "publicationDate": "2026-01-02T03:00:00.000Z",
            "date": "2026-01-02T06:00:00.000Z",
            "aircraftPrefix": "PR-AAA",
            "_auditing": {"auditorType": "ACC"},
            "_nonconformityOprPrevious": [{"ata": "23 - COMMUNICATIONS"}],
            "_nonconformityOpr": [],
            "_nonconformityMntPrevious": [],
            "_nonconformityMnt": [
                {
                    "_id": "nc-1",
                    "ata": "32 - LANDING GEAR",
                    "description": "Inspection finding",
                    "resolutionDate": "2026-01-05T00:00:00.000Z",
                }
            ],
        },
        {
            "_id": "audit-2",
            "reportName": "REPORT-2",
            "publicationDate": "2026-02-10T03:00:00.000Z",
            "date": "2026-02-10T06:00:00.000Z",
            "aircraftPrefix": "PR-BBB",
            "_auditing": {"auditorType": "ACCD"},
            "_nonconformityOprPrevious": [],
            "_nonconformityOpr": [],
            "_nonconformityMntPrevious": [],
            "_nonconformityMnt": [],
        },
    ]


def sample_reports():
    return [
        {
            "_id": "audit-1",
            "reportName": "REPORT-1",
            "contract": "123",
            "base": "Macae",
            "baseAbbreviation": "MEA",
            "operator": "OMNI Taxi Aereo",
            "operatorAbbreviation": "OMNI",
            "publicationDate": "2026-01-02T03:00:00.000Z",
            "date": "2026-01-02T06:00:00.000Z",
            "auditingOpr": "N/A",
            "auditingMnt": "Inspector 1",
            "aircraftPrefix": "PR-AAA",
            "aircraftModel": "AW 139",
            "auditingType": "ACC",
            "status": "Revisado",
            "_reviews": ["review-1"],
            "_nonconformityOprPrevious": ["nc-prev-1"],
            "_nonconformityOpr": [],
            "_nonconformityMntPrevious": [],
            "_nonconformityMnt": ["nc-1"],
            "_accompanimentPrevious": ["ac-1"],
            "_accompaniment": [],
            "photos": [{"url": "https://example.test/photo.jpg"}],
        },
        {
            "_id": "audit-2",
            "reportName": "REPORT-2",
            "contract": "456",
            "base": "Cabo Frio",
            "baseAbbreviation": "CFB",
            "operator": "CHC Helicopteros",
            "operatorAbbreviation": "CHC",
            "publicationDate": "2026-02-10T03:00:00.000Z",
            "date": "2026-02-10T06:00:00.000Z",
            "auditingOpr": "N/A",
            "auditingMnt": "Inspector 2",
            "aircraftPrefix": "PR-BBB",
            "aircraftModel": "S92-A",
            "auditingType": "ACCD",
            "status": "Cancelado",
            "_reviews": [],
            "_nonconformityOprPrevious": [],
            "_nonconformityOpr": [],
            "_nonconformityMntPrevious": [],
            "_nonconformityMnt": [],
            "_accompanimentPrevious": [],
            "_accompaniment": ["ac-2"],
            "photos": [],
        },
    ]


def sample_aircraft_reports():
    return [
        {
            "_id": "aircraft-report-1",
            "audit_id": "audit-1",
            "backup": True,
            "aircraftConfiguration": [
                {"configuration": "Offshore", "status": False},
                {"configuration": "SAR", "status": True},
                {"configuration": "Passageiros:", "status": True},
            ],
        },
        {
            "_id": "aircraft-report-2",
            "audit_id": "audit-2",
            "backup": False,
            "aircraftConfiguration": [
                {"configuration": "Passenger", "status": True},
            ],
        },
    ]


def test_count_items_handles_lists_scalar_and_empty_values():
    assert count_items([1, 2]) == 2
    assert count_items("item-id") == 1
    assert count_items("") == 0
    assert count_items(None) == 0


def test_load_and_save_json(tmp_path):
    path = tmp_path / "nested" / "file.json"

    save_json(path, {"ok": True})

    assert load_json(path) == {"ok": True}
    assert load_json(tmp_path / "missing.json") == []


def test_normalize_nonconformity_item_supports_dict_and_id_string():
    dict_item = normalize_nonconformity_item(
        {
            "_id": "nc-1",
            "ata": "23 - COMMUNICATIONS",
            "observation": "Observation text",
            "status": "open",
        }
    )
    string_item = normalize_nonconformity_item("nc-2")

    assert dict_item["item_id"] == "nc-1"
    assert dict_item["description"] == "Observation text"
    assert string_item["item_id"] == "nc-2"
    assert string_item["ata"] is None


def test_get_active_aircraft_configuration_returns_status_true_configuration():
    assert (
        get_active_aircraft_configuration(sample_aircraft_reports()[0])
        == "SAR; Passageiros"
    )
    assert get_active_aircraft_configuration({"aircraftConfiguration": []}) is None


def test_build_audits_dataframe_prefers_reports_and_creates_dashboard_columns():
    dataframe = build_audits_dataframe(
        sample_audits(), sample_reports(), sample_aircraft_reports()
    )

    assert len(dataframe) == 2
    assert dataframe.loc[0, "audit_id"] == "audit-1"
    assert dataframe.loc[0, "operator_abbreviation"] == "OMNI"
    assert dataframe.loc[0, "base_abbreviation"] == "MEA"
    assert dataframe.loc[0, "nonconformity_total"] == 1
    assert dataframe.loc[0, "previous_nonconformity_total"] == 1
    assert bool(dataframe.loc[0, "has_nonconformity"]) is True
    assert dataframe.loc[0, "photos_count"] == 1
    assert dataframe.loc[0, "audit_month"] == "2026-01"
    assert bool(dataframe.loc[0, "aircraft_backup"]) is True
    assert dataframe.loc[0, "aircraft_backup_label"] == "Backup"
    assert dataframe.loc[0, "aircraft_configuration"] == "SAR; Passageiros"
    assert dataframe.loc[1, "aircraft_backup_label"] == "Titular"
    assert dataframe.loc[1, "aircraft_configuration"] == "Passenger"
    assert pd.api.types.is_datetime64_any_dtype(dataframe["date"])


def test_build_audits_dataframe_falls_back_to_search_audits_when_reports_are_empty():
    dataframe = build_audits_dataframe(sample_audits(), reports=[])

    assert len(dataframe) == 2
    assert dataframe.loc[0, "auditing_type"] == "ACC"
    assert dataframe.loc[0, "aircraft_prefix"] == "PR-AAA"


def test_build_nonconformities_dataframe_enriches_rows_with_report_context():
    dataframe = build_nonconformities_dataframe(sample_audits(), sample_reports())

    assert len(dataframe) == 1
    assert set(dataframe["area"]) == {"manutencao"}
    assert set(dataframe["period"]) == {"current"}
    assert (
        bool(dataframe.loc[dataframe["item_id"] == "nc-1", "is_resolved"].iloc[0])
        is True
    )
    assert (
        dataframe.loc[dataframe["item_id"] == "nc-1", "operator_abbreviation"].iloc[0]
        == "OMNI"
    )


def test_build_kpis_calculates_main_dashboard_numbers():
    audits_dataframe = build_audits_dataframe(
        sample_audits(), sample_reports(), sample_aircraft_reports()
    )
    nonconformities_dataframe = build_nonconformities_dataframe(
        sample_audits(), sample_reports()
    )

    kpis = build_kpis(audits_dataframe, nonconformities_dataframe)

    assert kpis == {
        "total_audits": 2,
        "total_nonconformities": 1,
        "nonconformities_per_audit": 0.5,
        "audits_with_nonconformity": 1,
        "percent_audits_with_nonconformity": 50.0,
        "open_nonconformities": 0,
        "resolved_nonconformities": 1,
        "audited_bases": 2,
        "audited_aircraft": 2,
    }


def test_build_analysis_tables_creates_chart_ready_outputs():
    audits_dataframe = build_audits_dataframe(
        sample_audits(), sample_reports(), sample_aircraft_reports()
    )
    nonconformities_dataframe = build_nonconformities_dataframe(
        sample_audits(), sample_reports()
    )

    tables = build_analysis_tables(audits_dataframe, nonconformities_dataframe)

    assert tables["audits_by_month"].to_dict("records") == [
        {"audit_month": "2026-01", "audits_count": 1},
        {"audit_month": "2026-02", "audits_count": 1},
    ]
    assert tables["nonconformities_by_month"].to_dict("records") == [
        {"audit_month": "2026-01", "nonconformities_count": 1}
    ]
    assert tables["monthly_nonconformity_rate"].to_dict("records") == [
        {
            "audit_month": "2026-01",
            "audits_count": 1,
            "nonconformities_count": 1,
            "nonconformities_per_audit": 1.0,
        },
        {
            "audit_month": "2026-02",
            "audits_count": 1,
            "nonconformities_count": 0,
            "nonconformities_per_audit": 0.0,
        },
    ]
    assert set(tables["audits_by_type"]["auditing_type"]) == {"ACC", "ACCD"}
    assert tables["nonconformities_by_operator"].iloc[0]["nonconformities_count"] == 1
    assert tables["nonconformities_by_area"].to_dict("records") == [
        {"area": "manutencao", "nonconformities_count": 1}
    ]
    assert tables["nonconformities_by_base"].iloc[0]["base_abbreviation"] == "MEA"
    assert tables["aircraft_ranking"].iloc[0]["aircraft_prefix"] == "PR-AAA"
    assert tables["aircraft_backup_summary"].to_dict("records") == [
        {"aircraft_backup_label": "Backup", "audits_count": 1},
        {"aircraft_backup_label": "Titular", "audits_count": 1},
    ]
    assert tables["aircraft_configuration_summary"].to_dict("records") == [
        {"aircraft_configuration": "Passageiros", "audits_count": 1},
        {"aircraft_configuration": "Passenger", "audits_count": 1},
        {"aircraft_configuration": "SAR", "audits_count": 1},
    ]
    assert tables["ata_ranking"].to_dict("records") == [
        {
            "ata": "32 - LANDING GEAR",
            "nonconformities_count": 1,
            "audits_count": 1,
        },
    ]
    assert tables["recurrence_by_aircraft"].to_dict("records") == [
        {
            "aircraft_prefix": "PR-AAA",
            "audits_count": 1,
            "current_nonconformities_count": 1,
            "previous_nonconformities_count": 1,
            "audits_with_current_nonconformity": 1,
            "audits_with_previous_nonconformity": 1,
            "recurrent_audits": 1,
            "recurrence_rate": 1.0,
        },
        {
            "aircraft_prefix": "PR-BBB",
            "audits_count": 1,
            "current_nonconformities_count": 0,
            "previous_nonconformities_count": 0,
            "audits_with_current_nonconformity": 0,
            "audits_with_previous_nonconformity": 0,
            "recurrent_audits": 0,
            "recurrence_rate": 0.0,
        },
    ]
    assert tables["recurrence_by_base"].iloc[0]["base_abbreviation"] == "MEA"
    assert tables["recurrence_by_operator"].iloc[0]["operator_abbreviation"] == "OMNI"
    assert "ACC" in tables["base_type_heatmap"].columns


def test_run_transform_reads_raw_json_and_writes_processed_files(tmp_path):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / AUDITS_RAW_FILE).write_text(json.dumps(sample_audits()))
    (raw_dir / REPORTS_RAW_FILE).write_text(json.dumps(sample_reports()))
    (raw_dir / AIRCRAFT_REPORTS_RAW_FILE).write_text(
        json.dumps(sample_aircraft_reports())
    )

    result = run_transform(raw_dir=raw_dir, processed_dir=processed_dir)

    assert len(result["audits"]) == 2
    assert len(result["non_conformities"]) == 1
    assert result["kpis"]["total_audits"] == 2
    assert (processed_dir / AUDITS_PROCESSED_FILE).exists()
    assert (processed_dir / NONCONFORMITIES_PROCESSED_FILE).exists()
    assert (processed_dir / KPIS_FILE).exists()
    assert (processed_dir / AUDITS_BY_MONTH_FILE).exists()
    assert (processed_dir / AUDITS_BY_TYPE_FILE).exists()
    assert (processed_dir / NONCONFORMITIES_BY_MONTH_FILE).exists()
    assert (processed_dir / MONTHLY_NONCONFORMITY_RATE_FILE).exists()
    assert (processed_dir / NONCONFORMITIES_BY_OPERATOR_FILE).exists()
    assert (processed_dir / NONCONFORMITIES_BY_AREA_FILE).exists()
    assert (processed_dir / NONCONFORMITIES_BY_BASE_FILE).exists()
    assert (processed_dir / AIRCRAFT_RANKING_FILE).exists()
    assert (processed_dir / AIRCRAFT_BACKUP_SUMMARY_FILE).exists()
    assert (processed_dir / AIRCRAFT_CONFIGURATION_SUMMARY_FILE).exists()
    assert (processed_dir / BASE_TYPE_HEATMAP_FILE).exists()
    assert (processed_dir / ATA_RANKING_FILE).exists()
    assert (processed_dir / RECURRENCE_BY_AIRCRAFT_FILE).exists()
    assert (processed_dir / RECURRENCE_BY_BASE_FILE).exists()
    assert (processed_dir / RECURRENCE_BY_OPERATOR_FILE).exists()

    audits_csv = pd.read_csv(processed_dir / AUDITS_PROCESSED_FILE)
    kpis = json.loads((processed_dir / KPIS_FILE).read_text())

    assert list(audits_csv["audit_id"]) == ["audit-1", "audit-2"]
    assert list(audits_csv["aircraft_backup_label"]) == ["Backup", "Titular"]
    assert list(audits_csv["aircraft_configuration"]) == [
        "SAR; Passageiros",
        "Passenger",
    ]
    assert kpis["percent_audits_with_nonconformity"] == 50.0
    assert kpis["nonconformities_per_audit"] == 0.5
