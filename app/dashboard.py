import streamlit as st

from app.auth import render_logout_control, require_login
from app.charts import make_area_line_chart, make_bar_chart, make_horizontal_bar
from app.components import (
    format_decimal,
    format_number,
    format_percent,
    metric_card,
    render_chart,
    truncate_label,
)
from app.config import (
    AUDITS_PROCESSED_FILE,
    CHART_GOLD,
    CHART_PURPLE,
    CHART_RED,
    CHART_TEAL,
    FAVICON_PATH,
    NONCONFORMITIES_PROCESSED_FILE,
    PROCESSED_DIR,
    build_analysis_tables,
    build_kpis,
)
from app.data import (
    add_month_label,
    get_last_update_label,
    load_csv,
    parse_datetime_columns,
)
from app.filters import ensure_dashboard_analysis_tables, filter_dataframe
from app.sidebar import run_update_from_sidebar
from app.styles import apply_style

st.set_page_config(
    page_title="RINA ACC Dashboard",
    page_icon=str(FAVICON_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_page_header():
    last_update = get_last_update_label()
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


def render_kpi_cards(kpis):
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


def render_summary_charts(tables, has_previous_nonconformities):
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
            "Nao conformidades resolvidas",
            "Comparativo entre nao conformidades abertas e resolvidas.",
            make_horizontal_bar(
                tables["nonconformities_by_status"],
                "status_label:N",
                "nonconformities_count:Q",
                ["status_label", "nonconformities_count"],
                color=CHART_PURPLE,
            ),
        )
    with col_right:
        title_chart_source = tables["nonconformities_by_title"].head(12).copy()
        if not title_chart_source.empty:
            title_chart_source["title_short"] = title_chart_source["title"].apply(
                truncate_label
            )
        render_chart(
            "Titulos mais frequentes",
            "Nao conformidades mais recorrentes por titulo.",
            make_horizontal_bar(
                title_chart_source,
                "title_short:N",
                "nonconformities_count:Q",
                ["title", "nonconformities_count"],
                color=CHART_RED,
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
        if has_previous_nonconformities:
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
        else:
            st.info("Sem dados de nao conformidades anteriores no periodo filtrado.")

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


def render_recurrence_tables(tables, has_previous_nonconformities):
    st.markdown(
        '<div class="section-title">Analise de recorrencia</div>',
        unsafe_allow_html=True,
    )
    if not has_previous_nonconformities:
        st.info(
            "Sem dados de nao conformidades anteriores no periodo filtrado. "
            "Os indicadores de recorrencia permanecem zerados."
        )
        return

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


def render_detail_tables(filtered_audits, filtered_nonconformities):
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
    for column in ["title", "requirement_type", "contractual"]:
        if column not in filtered_nonconformities.columns:
            filtered_nonconformities[column] = ""
    nonconformity_columns = [
        "date",
        "title",
        "ata",
        "area",
        "period",
        "aircraft_prefix",
        "operator_abbreviation",
        "base_abbreviation",
        "auditing_type",
        "requirement_type",
        "contractual",
        "is_resolved",
        "resolution_date",
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


def main():
    apply_style()

    if not require_login():
        return

    st.markdown('<div class="dashboard-view"></div>', unsafe_allow_html=True)

    audits = load_csv(PROCESSED_DIR / AUDITS_PROCESSED_FILE)
    nonconformities = load_csv(PROCESSED_DIR / NONCONFORMITIES_PROCESSED_FILE)

    audits = parse_datetime_columns(audits, ["date", "publication_date"])
    nonconformities = parse_datetime_columns(
        nonconformities,
        ["date", "publication_date", "resolution_date"],
    )

    render_logout_control()
    run_update_from_sidebar(audits)
    render_page_header()

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
    has_previous_nonconformities = (
        filtered_audits["previous_nonconformity_total"].sum() > 0
    )

    render_kpi_cards(kpis)
    st.divider()
    render_summary_charts(tables, has_previous_nonconformities)
    st.divider()
    render_recurrence_tables(tables, has_previous_nonconformities)
    st.divider()
    render_detail_tables(filtered_audits, filtered_nonconformities)
