import json
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

AUDITS_RAW_FILE = "audits.json"
REPORTS_RAW_FILE = "audit_reports.json"
AIRCRAFT_REPORTS_RAW_FILE = "aircraft_reports.json"
NONCONFORMITIES_CURRENT_RAW_FILE = "nonconformities_current.json"

AUDITS_PROCESSED_FILE = "audits.csv"
NONCONFORMITIES_PROCESSED_FILE = "non_conformities.csv"
KPIS_FILE = "kpis.json"
AUDITS_BY_MONTH_FILE = "audits_by_month.csv"
AUDITS_BY_TYPE_FILE = "audits_by_type.csv"
NONCONFORMITIES_BY_MONTH_FILE = "nonconformities_by_month.csv"
MONTHLY_NONCONFORMITY_RATE_FILE = "monthly_nonconformity_rate.csv"
NONCONFORMITIES_BY_AREA_FILE = "nonconformities_by_area.csv"
NONCONFORMITIES_BY_OPERATOR_FILE = "nonconformities_by_operator.csv"
NONCONFORMITIES_BY_BASE_FILE = "nonconformities_by_base.csv"
NONCONFORMITIES_BY_STATUS_FILE = "nonconformities_by_status.csv"
NONCONFORMITIES_BY_TITLE_FILE = "nonconformities_by_title.csv"
AIRCRAFT_RANKING_FILE = "aircraft_nonconformity_ranking.csv"
AIRCRAFT_BACKUP_SUMMARY_FILE = "aircraft_backup_summary.csv"
AIRCRAFT_CONFIGURATION_SUMMARY_FILE = "aircraft_configuration_summary.csv"
BASE_TYPE_HEATMAP_FILE = "base_auditing_type_heatmap.csv"
ATA_RANKING_FILE = "ata_ranking.csv"
RECURRENCE_BY_AIRCRAFT_FILE = "recurrence_by_aircraft.csv"
RECURRENCE_BY_BASE_FILE = "recurrence_by_base.csv"
RECURRENCE_BY_OPERATOR_FILE = "recurrence_by_operator.csv"

NONCONFORMITY_FIELDS = {
    "_nonconformityOprPrevious": ("operacional", "previous"),
    "_nonconformityOpr": ("operacional", "current"),
    "_nonconformityMntPrevious": ("manutencao", "previous"),
    "_nonconformityMnt": ("manutencao", "current"),
}
CURRENT_NONCONFORMITY_FIELDS = ("_nonconformityOpr", "_nonconformityMnt")

ACCOMPANIMENT_FIELDS = ("_accompanimentPrevious", "_accompaniment")


def load_json(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r") as file:
        return json.load(file)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        json.dump(data, file, indent=4)


def count_items(value):
    if isinstance(value, list):
        return len(value)

    if value:
        return 1

    return 0


def get_nested_value(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)

    return default


def get_aircraft_report_by_audit_id(aircraft_reports):
    return {
        aircraft_report.get("audit_id"): aircraft_report
        for aircraft_report in aircraft_reports
        if isinstance(aircraft_report, dict) and aircraft_report.get("audit_id")
    }


def normalize_backup(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "sim", "yes"}

    return bool(value) if value is not None else False


def normalize_configuration_label(value):
    if value is None:
        return None

    value = str(value).strip().rstrip(":").strip()
    return value or None


def get_active_aircraft_configurations(aircraft_report):
    configurations = aircraft_report.get("aircraftConfiguration")

    if isinstance(configurations, dict):
        configurations = [configurations]

    if not isinstance(configurations, list):
        return []

    active_configurations = []
    for configuration in configurations:
        if (
            not isinstance(configuration, dict)
            or configuration.get("status") is not True
        ):
            continue

        label = normalize_configuration_label(
            configuration.get("configuration")
            or configuration.get("name")
            or configuration.get("title")
            or configuration.get("description")
            or configuration.get("type")
            or configuration.get("_id")
        )

        if label and label not in active_configurations:
            active_configurations.append(label)

    return active_configurations


def get_active_aircraft_configuration(aircraft_report):
    active_configurations = get_active_aircraft_configurations(aircraft_report)

    if not active_configurations:
        return None

    return "; ".join(active_configurations)


def build_nonconformity_summary(nonconformity_payloads):
    summary = {}
    for payload in nonconformity_payloads or []:
        if not isinstance(payload, dict):
            continue

        audit_id = payload.get("audit_id")
        area = payload.get("area")
        period = payload.get("period") or "current"
        total = payload.get("total")

        if not audit_id or not area:
            continue

        if total is None:
            items = (
                payload.get("items") if isinstance(payload.get("items"), list) else []
            )
            total = len(items)

        summary.setdefault(
            audit_id,
            {
                "current": {"operacional": 0, "manutencao": 0},
                "previous": {"operacional": 0, "manutencao": 0},
                "_available": set(),
            },
        )
        if period not in summary[audit_id]:
            summary[audit_id][period] = {"operacional": 0, "manutencao": 0}
        summary[audit_id][period][area] = int(total)
        summary[audit_id]["_available"].add((period, area))

    return summary


def parse_dates(dataframe, columns):
    for column in columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(
                dataframe[column], errors="coerce", utc=True
            )

    return dataframe


def build_audits_dataframe(
    audits, reports, aircraft_reports=None, nonconformity_payloads=None
):
    source = reports or audits
    aircraft_reports_by_audit_id = get_aircraft_report_by_audit_id(
        aircraft_reports or []
    )
    nonconformity_summary = build_nonconformity_summary(nonconformity_payloads)
    rows = []

    for item in source:
        audit_id = item.get("_id")
        aircraft_report = aircraft_reports_by_audit_id.get(audit_id, {})
        date = item.get("date")
        publication_date = item.get("publicationDate")
        auditing_data = item.get("_auditing")
        auditing_type = item.get("auditingType") or get_nested_value(
            auditing_data, "auditorType"
        )

        if nonconformity_payloads:
            summary = nonconformity_summary.get(
                audit_id,
                {
                    "current": {"operacional": 0, "manutencao": 0},
                    "previous": {"operacional": 0, "manutencao": 0},
                    "_available": set(),
                },
            )
            available_payloads = summary.get("_available", set())
            nonconformity_counts = {}
            for field, (area, period) in NONCONFORMITY_FIELDS.items():
                if (period, area) in available_payloads:
                    nonconformity_counts[field] = int(
                        summary.get(period, {}).get(area, 0)
                    )
                else:
                    nonconformity_counts[field] = count_items(item.get(field))
        else:
            nonconformity_counts = {
                field: count_items(item.get(field)) for field in NONCONFORMITY_FIELDS
            }
        accompaniment_previous_count = count_items(item.get("_accompanimentPrevious"))
        accompaniment_current_count = count_items(item.get("_accompaniment"))
        photos_count = count_items(item.get("photos"))
        reviews_count = count_items(item.get("_reviews"))
        nonconformity_total = sum(
            nonconformity_counts[field] for field in CURRENT_NONCONFORMITY_FIELDS
        )
        previous_nonconformity_total = (
            nonconformity_counts["_nonconformityOprPrevious"]
            + nonconformity_counts["_nonconformityMntPrevious"]
        )

        rows.append(
            {
                "audit_id": audit_id,
                "report_name": item.get("reportName"),
                "date": date,
                "publication_date": publication_date,
                "aircraft_prefix": item.get("aircraftPrefix"),
                "aircraft_model": item.get("aircraftModel"),
                "aircraft_backup": normalize_backup(aircraft_report.get("backup")),
                "aircraft_backup_label": (
                    "Backup"
                    if normalize_backup(aircraft_report.get("backup"))
                    else "Titular"
                ),
                "aircraft_configuration": (
                    get_active_aircraft_configuration(aircraft_report)
                    or "Nao informado"
                ),
                "operator": item.get("operator"),
                "operator_abbreviation": item.get("operatorAbbreviation"),
                "base": item.get("base"),
                "base_abbreviation": item.get("baseAbbreviation"),
                "contract": item.get("contract"),
                "auditing_type": auditing_type,
                "status": item.get("status"),
                "auditing_opr": item.get("auditingOpr"),
                "auditing_mnt": item.get("auditingMnt"),
                "nonconformity_opr_previous_count": nonconformity_counts[
                    "_nonconformityOprPrevious"
                ],
                "nonconformity_opr_current_count": nonconformity_counts[
                    "_nonconformityOpr"
                ],
                "nonconformity_mnt_previous_count": nonconformity_counts[
                    "_nonconformityMntPrevious"
                ],
                "nonconformity_mnt_current_count": nonconformity_counts[
                    "_nonconformityMnt"
                ],
                "nonconformity_total": nonconformity_total,
                "previous_nonconformity_total": previous_nonconformity_total,
                "has_nonconformity": nonconformity_total > 0,
                "accompaniment_previous_count": accompaniment_previous_count,
                "accompaniment_current_count": accompaniment_current_count,
                "accompaniment_total": (
                    accompaniment_previous_count + accompaniment_current_count
                ),
                "photos_count": photos_count,
                "reviews_count": reviews_count,
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return dataframe

    dataframe = parse_dates(dataframe, ["date", "publication_date"])
    dataframe["audit_month"] = dataframe["date"].dt.strftime("%Y-%m")

    return dataframe


def normalize_nonconformity_item(item):
    if isinstance(item, dict):
        return {
            "item_id": item.get("_id") or item.get("id"),
            "ata": item.get("ata"),
            "title": item.get("title"),
            "description": (
                item.get("description")
                or item.get("observation")
                or item.get("text")
                or item.get("title")
            ),
            "status": item.get("status"),
            "resolution_date": (
                item.get("dateSolution")
                or item.get("resolutionDate")
                or item.get("resolvedAt")
            ),
            "requirement_type": item.get("requirementType"),
            "contractual": item.get("contractual"),
        }

    return {
        "item_id": item,
        "ata": None,
        "description": None,
        "status": None,
        "resolution_date": None,
    }


def normalize_title(value):
    if value is None:
        return "Sem titulo"

    text = str(value).strip()
    if not text:
        return "Sem titulo"

    text_lower = text.lower()
    if "pbo" in text_lower:
        return "PBO"
    if "aff" in text_lower or "automatic flight folowing" in text_lower:
        return "AFF"
    if "automatic flight following" in text_lower:
        return "AFF"
    if "cockipit" in text_lower or "cockpit" in text_lower:
        return "Cockpit"

    return text


def build_nonconformities_dataframe(audits, reports, nonconformity_payloads=None):
    if nonconformity_payloads is None:
        nonconformity_payloads = []

    if not nonconformity_payloads:
        audits_by_id = {audit.get("_id"): audit for audit in audits}
        rows = []

        for report in reports or audits:
            audit = audits_by_id.get(report.get("_id"), report)

            for field, (area, period) in NONCONFORMITY_FIELDS.items():
                if period != "current":
                    continue

                audit_items = audit.get(field) or []
                report_items = report.get(field) or audit_items

                for index, item in enumerate(report_items):
                    normalized_item = normalize_nonconformity_item(item)
                    audit_item = (
                        audit_items[index] if index < len(audit_items) else None
                    )
                    audit_item_data = (
                        normalize_nonconformity_item(audit_item)
                        if audit_item is not None
                        else {}
                    )
                    normalized_item["ata"] = normalized_item.get(
                        "ata"
                    ) or audit_item_data.get("ata")
                    normalized_item["description"] = normalized_item.get(
                        "description"
                    ) or audit_item_data.get("description")
                    normalized_item["status"] = normalized_item.get(
                        "status"
                    ) or audit_item_data.get("status")
                    normalized_item["resolution_date"] = normalized_item.get(
                        "resolution_date"
                    ) or audit_item_data.get("resolution_date")

                    rows.append(
                        {
                            "audit_id": report.get("_id") or audit.get("_id"),
                            "report_name": report.get("reportName")
                            or audit.get("reportName"),
                            "date": report.get("date") or audit.get("date"),
                            "publication_date": report.get("publicationDate")
                            or audit.get("publicationDate"),
                            "aircraft_prefix": report.get("aircraftPrefix")
                            or audit.get("aircraftPrefix"),
                            "operator": report.get("operator"),
                            "operator_abbreviation": report.get("operatorAbbreviation"),
                            "base": report.get("base"),
                            "base_abbreviation": report.get("baseAbbreviation"),
                            "contract": report.get("contract"),
                            "auditing_type": report.get("auditingType")
                            or get_nested_value(audit.get("_auditing"), "auditorType"),
                            "audit_status": report.get("status"),
                            "source_field": field,
                            "area": area,
                            "period": period,
                            **normalized_item,
                        }
                    )

        dataframe = pd.DataFrame(rows)
    else:
        reports_by_id = {report.get("_id"): report for report in reports}
        audits_by_id = {audit.get("_id"): audit for audit in audits}
        rows = []
        for payload in nonconformity_payloads:
            if not isinstance(payload, dict):
                continue

            audit_id = payload.get("audit_id")
            area = payload.get("area") or "desconhecido"
            period = payload.get("period") or "current"
            items = payload.get("items")
            if not isinstance(items, list):
                items = []

            report = reports_by_id.get(audit_id, {})
            audit = audits_by_id.get(audit_id, {})

            for item in items:
                normalized_item = normalize_nonconformity_item(item)
                rows.append(
                    {
                        "audit_id": audit_id,
                        "report_name": report.get("reportName")
                        or audit.get("reportName"),
                        "date": report.get("date") or audit.get("date"),
                        "publication_date": report.get("publicationDate")
                        or audit.get("publicationDate"),
                        "aircraft_prefix": report.get("aircraftPrefix")
                        or audit.get("aircraftPrefix"),
                        "operator": report.get("operator"),
                        "operator_abbreviation": report.get("operatorAbbreviation"),
                        "base": report.get("base"),
                        "base_abbreviation": report.get("baseAbbreviation"),
                        "contract": report.get("contract"),
                        "auditing_type": report.get("auditingType")
                        or get_nested_value(audit.get("_auditing"), "auditorType"),
                        "audit_status": report.get("status"),
                        "source_field": None,
                        "area": area,
                        "period": period,
                        **normalized_item,
                    }
                )

        dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        return dataframe

    dataframe = parse_dates(dataframe, ["date", "publication_date", "resolution_date"])
    dataframe["audit_month"] = dataframe["date"].dt.strftime("%Y-%m")
    dataframe["is_current"] = dataframe["period"] == "current"
    dataframe["is_previous"] = dataframe["period"] == "previous"
    dataframe["is_resolved"] = dataframe["resolution_date"].notna()

    return dataframe


def build_kpis(audits_dataframe, nonconformities_dataframe):
    total_audits = len(audits_dataframe)
    total_nonconformities = int(audits_dataframe["nonconformity_total"].sum())
    audits_with_nonconformity = int(
        audits_dataframe["has_nonconformity"].sum()
        if "has_nonconformity" in audits_dataframe
        else 0
    )
    percent_with_nonconformity = (
        round((audits_with_nonconformity / total_audits) * 100, 2)
        if total_audits
        else 0
    )

    open_nonconformities = 0
    resolved_nonconformities = 0
    if not nonconformities_dataframe.empty:
        resolved_nonconformities = int(nonconformities_dataframe["is_resolved"].sum())
        open_nonconformities = max(total_nonconformities - resolved_nonconformities, 0)

    return {
        "total_audits": total_audits,
        "total_nonconformities": total_nonconformities,
        "nonconformities_per_audit": (
            round(total_nonconformities / total_audits, 2) if total_audits else 0
        ),
        "audits_with_nonconformity": audits_with_nonconformity,
        "percent_audits_with_nonconformity": percent_with_nonconformity,
        "open_nonconformities": open_nonconformities,
        "resolved_nonconformities": resolved_nonconformities,
        "audited_bases": (
            int(audits_dataframe["base_abbreviation"].nunique())
            if "base_abbreviation" in audits_dataframe
            else 0
        ),
        "audited_aircraft": (
            int(audits_dataframe["aircraft_prefix"].nunique())
            if "aircraft_prefix" in audits_dataframe
            else 0
        ),
    }


def count_by(dataframe, columns, value_name):
    if dataframe.empty:
        return pd.DataFrame(columns=[*columns, value_name])

    sort_columns = [value_name, *columns]
    sort_ascending = [False, *([True] * len(columns))]

    return (
        dataframe.groupby(columns, dropna=False)
        .size()
        .reset_index(name=value_name)
        .sort_values(sort_columns, ascending=sort_ascending)
        .reset_index(drop=True)
    )


def build_recurrence_table(dataframe, group_columns):
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

    recurrence_source = dataframe.copy()
    recurrence_source["has_current_nonconformity"] = (
        recurrence_source["nonconformity_total"] > 0
    )
    recurrence_source["has_previous_nonconformity"] = (
        recurrence_source["previous_nonconformity_total"] > 0
    )
    recurrence_source["has_recurrence"] = (
        recurrence_source["has_current_nonconformity"]
        & recurrence_source["has_previous_nonconformity"]
    )

    recurrence_table = (
        recurrence_source.groupby(group_columns, dropna=False)
        .agg(
            audits_count=("audit_id", "count"),
            current_nonconformities_count=("nonconformity_total", "sum"),
            previous_nonconformities_count=("previous_nonconformity_total", "sum"),
            audits_with_current_nonconformity=(
                "has_current_nonconformity",
                "sum",
            ),
            audits_with_previous_nonconformity=(
                "has_previous_nonconformity",
                "sum",
            ),
            recurrent_audits=("has_recurrence", "sum"),
        )
        .reset_index()
    )
    recurrence_table["recurrence_rate"] = (
        (
            recurrence_table["recurrent_audits"]
            / recurrence_table["audits_with_previous_nonconformity"].replace(0, pd.NA)
        )
        .fillna(0)
        .round(2)
    )

    return recurrence_table.sort_values(
        [
            "recurrent_audits",
            "recurrence_rate",
            "current_nonconformities_count",
            "audits_count",
        ],
        ascending=False,
    ).reset_index(drop=True)


def build_analysis_tables(audits_dataframe, nonconformities_dataframe):
    audits_by_month = count_by(audits_dataframe, ["audit_month"], "audits_count")
    audits_by_type = count_by(audits_dataframe, ["auditing_type"], "audits_count")
    nonconformities_by_month = count_by(
        nonconformities_dataframe,
        ["audit_month"],
        "nonconformities_count",
    )
    monthly_nonconformity_rate = audits_by_month.merge(
        nonconformities_by_month,
        on="audit_month",
        how="left",
    )
    if "nonconformities_count" in monthly_nonconformity_rate:
        monthly_nonconformity_rate["nonconformities_count"] = (
            monthly_nonconformity_rate["nonconformities_count"].fillna(0).astype(int)
        )
        monthly_nonconformity_rate["nonconformities_per_audit"] = (
            monthly_nonconformity_rate["nonconformities_count"]
            / monthly_nonconformity_rate["audits_count"]
        ).round(2)
    else:
        monthly_nonconformity_rate["nonconformities_count"] = pd.Series(dtype=int)
        monthly_nonconformity_rate["nonconformities_per_audit"] = pd.Series(dtype=float)

    nonconformities_by_operator = count_by(
        nonconformities_dataframe,
        ["operator_abbreviation", "operator"],
        "nonconformities_count",
    )
    nonconformities_by_area = count_by(
        nonconformities_dataframe,
        ["area"],
        "nonconformities_count",
    )
    nonconformities_by_base = count_by(
        nonconformities_dataframe,
        ["base_abbreviation", "base"],
        "nonconformities_count",
    )
    if nonconformities_dataframe.empty:
        nonconformities_by_status = pd.DataFrame(
            columns=["status_label", "nonconformities_count"]
        )
    else:
        nonconformities_by_status = count_by(
            nonconformities_dataframe.assign(
                status_label=nonconformities_dataframe["is_resolved"].map(
                    lambda value: "Resolvida" if bool(value) else "Aberta"
                )
            ),
            ["status_label"],
            "nonconformities_count",
        )
    title_source = nonconformities_dataframe.copy()
    if "title" not in title_source.columns:
        title_source["title"] = "Sem titulo"
    if "description" in title_source.columns:
        title_source["title"] = title_source["title"].fillna(
            title_source["description"]
        )
    title_source["title"] = title_source["title"].apply(normalize_title)
    nonconformities_by_title = count_by(
        title_source,
        ["title"],
        "nonconformities_count",
    )
    aircraft_ranking = (
        audits_dataframe[["aircraft_prefix", "nonconformity_total", "audit_id"]]
        .groupby("aircraft_prefix", dropna=False)
        .agg(
            nonconformities_count=("nonconformity_total", "sum"),
            audits_count=("audit_id", "count"),
        )
        .sort_values(["nonconformities_count", "audits_count"], ascending=False)
        .reset_index()
        if not audits_dataframe.empty
        else pd.DataFrame(
            columns=["aircraft_prefix", "nonconformities_count", "audits_count"]
        )
    )
    aircraft_configuration_source = (
        audits_dataframe[["audit_id", "aircraft_configuration"]].copy()
        if not audits_dataframe.empty
        else pd.DataFrame(columns=["audit_id", "aircraft_configuration"])
    )
    if not aircraft_configuration_source.empty:
        aircraft_configuration_source["aircraft_configuration"] = (
            aircraft_configuration_source["aircraft_configuration"]
            .fillna("Nao informado")
            .str.split("; ")
        )
        aircraft_configuration_source = aircraft_configuration_source.explode(
            "aircraft_configuration"
        )

    aircraft_backup_summary = count_by(
        audits_dataframe,
        ["aircraft_backup_label"],
        "audits_count",
    )
    aircraft_configuration_summary = count_by(
        aircraft_configuration_source,
        ["aircraft_configuration"],
        "audits_count",
    )
    ata_ranking = (
        nonconformities_dataframe.assign(
            ata=nonconformities_dataframe["ata"].fillna("Sem ATA")
        )
        .groupby("ata", dropna=False)
        .agg(
            nonconformities_count=("audit_id", "count"),
            audits_count=("audit_id", "nunique"),
        )
        .sort_values(["nonconformities_count", "audits_count"], ascending=False)
        .reset_index()
        if not nonconformities_dataframe.empty
        else pd.DataFrame(columns=["ata", "nonconformities_count", "audits_count"])
    )
    recurrence_by_aircraft = build_recurrence_table(
        audits_dataframe,
        ["aircraft_prefix"],
    )
    recurrence_by_base = build_recurrence_table(
        audits_dataframe,
        ["base_abbreviation", "base"],
    )
    recurrence_by_operator = build_recurrence_table(
        audits_dataframe,
        ["operator_abbreviation", "operator"],
    )

    if audits_dataframe.empty:
        base_type_heatmap = pd.DataFrame()
    else:
        base_type_heatmap = (
            audits_dataframe.pivot_table(
                index="base_abbreviation",
                columns="auditing_type",
                values="audit_id",
                aggfunc="count",
                fill_value=0,
            )
            .reset_index()
            .rename_axis(None, axis=1)
        )

    return {
        "audits_by_month": audits_by_month,
        "audits_by_type": audits_by_type,
        "nonconformities_by_month": nonconformities_by_month,
        "monthly_nonconformity_rate": monthly_nonconformity_rate,
        "nonconformities_by_operator": nonconformities_by_operator,
        "nonconformities_by_area": nonconformities_by_area,
        "nonconformities_by_base": nonconformities_by_base,
        "nonconformities_by_status": nonconformities_by_status,
        "nonconformities_by_title": nonconformities_by_title,
        "aircraft_ranking": aircraft_ranking,
        "aircraft_backup_summary": aircraft_backup_summary,
        "aircraft_configuration_summary": aircraft_configuration_summary,
        "base_type_heatmap": base_type_heatmap,
        "ata_ranking": ata_ranking,
        "recurrence_by_aircraft": recurrence_by_aircraft,
        "recurrence_by_base": recurrence_by_base,
        "recurrence_by_operator": recurrence_by_operator,
    }


def save_dataframe(path, dataframe):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def run_transform(raw_dir=RAW_DIR, processed_dir=PROCESSED_DIR):
    raw_dir = Path(raw_dir)
    processed_dir = Path(processed_dir)

    audits = load_json(raw_dir / AUDITS_RAW_FILE)
    reports = load_json(raw_dir / REPORTS_RAW_FILE)
    aircraft_reports = load_json(raw_dir / AIRCRAFT_REPORTS_RAW_FILE)
    nonconformity_payloads = load_json(raw_dir / NONCONFORMITIES_CURRENT_RAW_FILE)

    audits_dataframe = build_audits_dataframe(
        audits,
        reports,
        aircraft_reports,
        nonconformity_payloads,
    )
    nonconformities_dataframe = build_nonconformities_dataframe(
        audits,
        reports,
        nonconformity_payloads,
    )
    kpis = build_kpis(audits_dataframe, nonconformities_dataframe)
    analysis_tables = build_analysis_tables(audits_dataframe, nonconformities_dataframe)

    save_dataframe(processed_dir / AUDITS_PROCESSED_FILE, audits_dataframe)
    save_dataframe(
        processed_dir / NONCONFORMITIES_PROCESSED_FILE,
        nonconformities_dataframe,
    )
    save_json(processed_dir / KPIS_FILE, kpis)
    save_dataframe(
        processed_dir / AUDITS_BY_MONTH_FILE, analysis_tables["audits_by_month"]
    )
    save_dataframe(
        processed_dir / AUDITS_BY_TYPE_FILE, analysis_tables["audits_by_type"]
    )
    save_dataframe(
        processed_dir / NONCONFORMITIES_BY_MONTH_FILE,
        analysis_tables["nonconformities_by_month"],
    )
    save_dataframe(
        processed_dir / MONTHLY_NONCONFORMITY_RATE_FILE,
        analysis_tables["monthly_nonconformity_rate"],
    )
    save_dataframe(
        processed_dir / NONCONFORMITIES_BY_OPERATOR_FILE,
        analysis_tables["nonconformities_by_operator"],
    )
    save_dataframe(
        processed_dir / NONCONFORMITIES_BY_AREA_FILE,
        analysis_tables["nonconformities_by_area"],
    )
    save_dataframe(
        processed_dir / NONCONFORMITIES_BY_BASE_FILE,
        analysis_tables["nonconformities_by_base"],
    )
    save_dataframe(
        processed_dir / NONCONFORMITIES_BY_STATUS_FILE,
        analysis_tables["nonconformities_by_status"],
    )
    save_dataframe(
        processed_dir / NONCONFORMITIES_BY_TITLE_FILE,
        analysis_tables["nonconformities_by_title"],
    )
    save_dataframe(
        processed_dir / AIRCRAFT_RANKING_FILE,
        analysis_tables["aircraft_ranking"],
    )
    save_dataframe(
        processed_dir / AIRCRAFT_BACKUP_SUMMARY_FILE,
        analysis_tables["aircraft_backup_summary"],
    )
    save_dataframe(
        processed_dir / AIRCRAFT_CONFIGURATION_SUMMARY_FILE,
        analysis_tables["aircraft_configuration_summary"],
    )
    save_dataframe(
        processed_dir / BASE_TYPE_HEATMAP_FILE,
        analysis_tables["base_type_heatmap"],
    )
    save_dataframe(
        processed_dir / ATA_RANKING_FILE,
        analysis_tables["ata_ranking"],
    )
    save_dataframe(
        processed_dir / RECURRENCE_BY_AIRCRAFT_FILE,
        analysis_tables["recurrence_by_aircraft"],
    )
    save_dataframe(
        processed_dir / RECURRENCE_BY_BASE_FILE,
        analysis_tables["recurrence_by_base"],
    )
    save_dataframe(
        processed_dir / RECURRENCE_BY_OPERATOR_FILE,
        analysis_tables["recurrence_by_operator"],
    )

    return {
        "audits": audits_dataframe,
        "non_conformities": nonconformities_dataframe,
        "kpis": kpis,
        **analysis_tables,
    }
