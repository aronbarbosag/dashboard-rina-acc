import pandas as pd
import streamlit as st


def filter_dataframe(audits, nonconformities, accompaniments=None):
    st.sidebar.markdown("### Filtros")

    if audits.empty:
        if accompaniments is None:
            return audits, nonconformities
        return audits, nonconformities, accompaniments

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

    if accompaniments is None:
        return filtered, filtered_nonconformities

    if accompaniments.empty or "audit_id" not in accompaniments.columns:
        filtered_accompaniments = accompaniments.copy()
    else:
        filtered_accompaniments = accompaniments[
            accompaniments["audit_id"].isin(audit_ids)
        ].copy()

    return filtered, filtered_nonconformities, filtered_accompaniments


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
    if "nonconformities_by_status" not in tables:
        if not nonconformities.empty:
            status_source = nonconformities.copy()
            if "is_resolved" not in status_source.columns:
                status_source["is_resolved"] = status_source["resolution_date"].notna()
            status_source["status_label"] = status_source["is_resolved"].map(
                lambda value: "Resolvida" if bool(value) else "Aberta"
            )
            tables["nonconformities_by_status"] = count_dashboard_rows(
                status_source,
                ["status_label"],
                "nonconformities_count",
            )
        else:
            tables["nonconformities_by_status"] = pd.DataFrame(
                columns=["status_label", "nonconformities_count"]
            )
    if "nonconformities_by_title" not in tables:
        if not nonconformities.empty:
            title_source = nonconformities.copy()
            if "title" not in title_source.columns:
                title_source["title"] = "Sem titulo"
            title_source["title"] = title_source["title"].fillna("Sem titulo")
            tables["nonconformities_by_title"] = count_dashboard_rows(
                title_source,
                ["title"],
                "nonconformities_count",
            )
        else:
            tables["nonconformities_by_title"] = pd.DataFrame(
                columns=["title", "nonconformities_count"]
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
