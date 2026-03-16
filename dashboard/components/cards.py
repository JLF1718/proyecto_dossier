"""Card components for KPI sections."""

from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, html

from dashboard.i18n import t


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _fmt_tons(value: Any) -> str:
    try:
        return f"{float(value):,.1f}"
    except (TypeError, ValueError):
        return "0.0"


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):,.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _fmt_week(value: Any) -> str:
    try:
        return f"W{int(value)}"
    except (TypeError, ValueError):
        return "—"


def _fmt_signed_int(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "0"
    return f"{number:+,}"


def _fmt_signed_tons(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0.0"
    return f"{number:+,.1f}"


def _tone_for_delta(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "secondary"
    if number > 0:
        return "success"
    if number < 0:
        return "danger"
    return "secondary"


def _tone_for_backlog_delta(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "secondary"
    if number < 0:
        return "success"
    if number > 0:
        return "danger"
    return "secondary"


def _kpi_card(
    title: str,
    value: Any,
    subtitle: str,
    tone: str,
    *,
    xs: int = 12,
    md: int = 6,
    lg: int = 3,
    xl: int | None = None,
) -> dbc.Col:
    col_kwargs: Dict[str, Any] = {
        "xs": xs,
        "md": md,
        "lg": lg,
        "className": "mb-3",
    }
    if xl is not None:
        col_kwargs["xl"] = xl

    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(title, className="text-uppercase qa-subtitle"),
                    html.Div(str(value), className=f"qa-kpi-value text-{tone}"),
                    html.Div(subtitle, className="qa-subtitle"),
                ]
            ),
            className="qa-panel qa-kpi-card h-100",
        ),
        **col_kwargs,
    )


def executive_cards(kpis: Dict[str, Any], lang: str = "en") -> html.Div:
    """Render Executive Overview KPI cards in two rows.

    Accepts the payload returned by ``/api/dossiers/kpis``
    or the legacy ``{total, pending, rejected, approved}`` dict for backward
    compatibility.
    """
    total = int(kpis.get("total_dossiers", kpis.get("total", 0)) or 0)
    approved = int(kpis.get("approved_dossiers", kpis.get("approved", 0)) or 0)
    pending = int(kpis.get("pending_dossiers", kpis.get("pending", 0)) or 0)
    in_review = int(kpis.get("in_review_dossiers", 0) or 0)

    out_of_scope = int(kpis.get("rows_out_of_scope", 0) or 0)
    pct_liberado = kpis.get("pct_liberado", 0)
    peso_total_ton = kpis.get("peso_total_ton", 0)
    peso_liberado_ton = kpis.get("peso_liberado_ton", 0)
    pct_peso_liberado = kpis.get("pct_peso_liberado", 0)

    pct_approved = t(lang, "label.of_total", value=f"{approved / total * 100:.1f}") if total else "—"

    return html.Div(
        [
            dbc.Row(
                [
                    _kpi_card(t(lang, "kpi.total_dossiers"), _fmt_int(total), t(lang, "kpi.in_scope"), "primary"),
                    _kpi_card(t(lang, "kpi.approved"), _fmt_int(approved), pct_approved, "success"),
                    _kpi_card(t(lang, "kpi.pending"), _fmt_int(pending), t(lang, "kpi.awaiting_release"), "warning"),
                    _kpi_card(t(lang, "kpi.in_review"), _fmt_int(in_review), t(lang, "kpi.internal_review"), "info"),
                ]
            ),
            dbc.Row(
                [
                    _kpi_card(t(lang, "kpi.out_of_scope_rows"), _fmt_int(out_of_scope), t(lang, "kpi.excluded_kpis"), "secondary", lg=4, xl=2),
                    _kpi_card(t(lang, "kpi.released_pct"), f"{float(pct_liberado):.1f}%", t(lang, "kpi.dossiers_released"), "success", lg=4, xl=2),
                    _kpi_card(t(lang, "kpi.total_weight"), _fmt_tons(peso_total_ton), t(lang, "kpi.in_scope_weight"), "primary", lg=6, xl=3),
                    _kpi_card(t(lang, "kpi.released_weight"), _fmt_tons(peso_liberado_ton), t(lang, "kpi.weight_with_approved"), "info", lg=6, xl=3),
                    _kpi_card(t(lang, "kpi.released_weight_pct"), f"{float(pct_peso_liberado):.1f}%", t(lang, "kpi.weight_based_progress"), "warning", lg=4, xl=2),
                ],
                className="mt-1",
            ),
        ]
    )


def quality_cards(kpis: Dict[str, Any], lang: str = "en") -> dbc.Row:
    total = max(int(kpis.get("total_dossiers", kpis.get("total", 0))), 1)
    rejected = int(kpis.get("rejected_dossiers", kpis.get("rejected", 0)))
    pending = int(kpis.get("pending_dossiers", kpis.get("pending", 0)))
    in_review = int(kpis.get("in_review_dossiers", 0))
    approved = int(kpis.get("approved_dossiers", kpis.get("approved", 0)))
    rejection_rate = rejected / total * 100
    open_backlog = pending + in_review
    open_backlog_pct = open_backlog / total * 100
    approval_delta = approved - open_backlog

    cards = [
        _kpi_card(
            t(lang, "kpi.open_backlog"),
            _fmt_int(open_backlog),
            t(lang, "label.of_in_scope", value=f"{open_backlog_pct:.1f}"),
            "warning",
            lg=6,
            xl=4,
        ),
        _kpi_card(
            t(lang, "kpi.approval_delta"),
            _fmt_int(approval_delta),
            t(lang, "kpi.approved_minus_backlog"),
            "info",
            lg=6,
            xl=4,
        ),
    ]

    if rejected > 0:
        cards.append(
            _kpi_card(
                t(lang, "kpi.rejected_rate"),
                f"{rejection_rate:.1f}%",
                t(lang, "kpi.rejected_ratio"),
                "danger",
                lg=6,
                xl=4,
            )
        )

    return dbc.Row(cards)


def weekly_management_cards(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    delta = payload.get("delta_kpis", {})
    analysis_week = delta.get("analysis_week")
    previous_week = delta.get("previous_week")
    week_subtitle = t(lang, "label.week_compare", current=_fmt_week(analysis_week), previous=_fmt_week(previous_week))

    released_this_week = delta.get("released_this_week", 0)
    released_weight_this_week = delta.get("released_weight_t_this_week", 0.0)
    change_vs_previous_week = delta.get("change_vs_previous_week", 0)
    weight_change_vs_previous_week = delta.get("weight_change_t_vs_previous_week", 0.0)

    return html.Div(
        dbc.Row(
            [
                _kpi_card(t(lang, "kpi.released_this_week"), _fmt_int(released_this_week), week_subtitle, "success"),
                _kpi_card(t(lang, "kpi.released_weight_this_week"), _fmt_tons(released_weight_this_week), t(lang, "kpi.actual_released_weight"), "info"),
                _kpi_card(t(lang, "kpi.change_vs_prev"), _fmt_signed_int(change_vs_previous_week), week_subtitle, _tone_for_delta(change_vs_previous_week)),
                _kpi_card(t(lang, "kpi.weight_change_vs_prev"), _fmt_signed_tons(weight_change_vs_previous_week), t(lang, "kpi.delta_released_weight"), _tone_for_delta(weight_change_vs_previous_week)),
            ]
        )
    )


def historical_comparison_cards(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    current_vs_selected = payload.get("current_vs_selected", {})
    current_vs_previous = payload.get("current_vs_previous", {})
    comparison = current_vs_selected if current_vs_selected.get("available") else current_vs_previous
    comparison_label = (
        t(lang, "report.current_vs_selected")
        if current_vs_selected.get("available")
        else t(lang, "report.current_vs_previous")
    )
    comparison_week = comparison.get("comparison_week")
    snapshot_status = payload.get("snapshot_status", {})
    subtitle = f"{comparison_label}: {_fmt_week(payload.get('analysis_week'))} vs {_fmt_week(comparison_week)}"
    coverage = t(lang, "report.snapshot_coverage_value", count=snapshot_status.get("snapshot_count", 0))

    return html.Div(
        [
            html.Div(f"{subtitle} • {coverage}", className="qa-subtitle mb-2"),
            dbc.Row(
                [
                    _kpi_card(
                        t(lang, "kpi.released_delta_vs_snapshot"),
                        _fmt_signed_int(comparison.get("released_dossiers_delta", 0)),
                        comparison_label,
                        _tone_for_delta(comparison.get("released_dossiers_delta", 0)),
                    ),
                    _kpi_card(
                        t(lang, "kpi.weight_delta_vs_snapshot"),
                        _fmt_signed_tons(comparison.get("released_weight_t_delta", 0.0)),
                        comparison_label,
                        _tone_for_delta(comparison.get("released_weight_t_delta", 0.0)),
                    ),
                    _kpi_card(
                        t(lang, "kpi.backlog_delta_vs_snapshot"),
                        _fmt_signed_int(comparison.get("backlog_delta", 0)),
                        comparison_label,
                        _tone_for_backlog_delta(comparison.get("backlog_delta", 0)),
                    ),
                    _kpi_card(
                        t(lang, "kpi.approval_delta_vs_snapshot"),
                        _fmt_signed_int(comparison.get("approval_delta", 0)),
                        comparison_label,
                        _tone_for_delta(comparison.get("approval_delta", 0)),
                    ),
                ]
            ),
        ]
    )


def _management_table_card(
    records: list[dict[str, Any]],
    *,
    columns: list[tuple[str, str]],
    title: str,
    empty_message: str,
) -> dbc.Card:
    if not records:
        return dbc.Card(
            dbc.CardBody(
                [
                    html.Div(title, className="qa-section-title mb-2"),
                    html.Div(empty_message, className="text-muted"),
                ]
            ),
            className="qa-panel qa-table-card h-100",
        )

    frame = pd.DataFrame(records)
    display = pd.DataFrame()
    for label, source in columns:
        if source in frame.columns:
            display[label] = frame[source]
        else:
            display[label] = ""

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(title, className="qa-section-title mb-2"),
                dash_table.DataTable(
                    data=display.to_dict("records"),
                    columns=[{"name": column, "id": column} for column in display.columns],
                    page_action="none",
                    style_table={"overflowX": "auto"},
                    style_cell={
                        "fontSize": "12px",
                        "padding": "8px 10px",
                        "fontFamily": "IBM Plex Sans, sans-serif",
                        "border": "none",
                        "whiteSpace": "normal",
                        "height": "auto",
                        "textAlign": "left",
                    },
                    style_header={
                        "backgroundColor": "#eef3f8",
                        "color": "#10222f",
                        "fontWeight": "700",
                        "borderBottom": "1px solid #9db4c7",
                        "textTransform": "uppercase",
                        "fontSize": "11px",
                        "letterSpacing": "0.03em",
                    },
                    style_data={
                        "backgroundColor": "#ffffff",
                        "color": "#10222f",
                        "borderBottom": "1px solid #d8e2eb",
                    },
                    style_data_conditional=[
                        {"if": {"row_index": "odd"}, "backgroundColor": "#f8fbfd"},
                    ],
                ),
            ]
        ),
        className="qa-panel qa-table-card h-100",
    )


def executive_report_pack(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    meta = payload.get("report_meta", {})
    highlights = payload.get("weekly_highlights", [])
    executive_summary = pd.DataFrame(payload.get("executive_summary_table", []))
    backlog_risks = payload.get("top_backlog_risks", [])
    stagnant_groups = payload.get("top_stagnant_groups", [])
    snapshot_status = meta.get("snapshot_status", {})
    highlight_label_map = {
        "released_this_week": t(lang, "kpi.released_this_week"),
        "released_weight_t_this_week": t(lang, "kpi.released_weight_this_week"),
        "open_backlog": t(lang, "kpi.open_backlog"),
        "approved_dossiers": t(lang, "kpi.approved"),
    }

    highlight_cards = []
    for item in highlights:
        label = item.get("label", "")
        value = item.get("value", 0)
        delta = item.get("delta", 0)
        if "weight" in label:
            display_value = _fmt_tons(value)
            display_delta = _fmt_signed_tons(delta)
        else:
            display_value = _fmt_int(value)
            display_delta = _fmt_signed_int(delta)
        highlight_cards.append(
            _kpi_card(
                highlight_label_map.get(label, label.replace("_", " ").title()),
                display_value,
                display_delta,
                _tone_for_backlog_delta(delta) if label == "open_backlog" else _tone_for_delta(delta),
                lg=3,
                xl=3,
            )
        )

    header = dbc.Card(
        dbc.CardBody(
            [
                html.Div(t(lang, "report.title"), className="qa-export-banner-kicker"),
                html.H3(t(lang, "report.subtitle"), className="qa-page-title mb-2", style={"fontSize": "1.35rem", "color": "#10222f", "textTransform": "none"}),
                dbc.Row(
                    [
                        dbc.Col(html.Div(f"{t(lang, 'report.language')}: {str(meta.get('language', lang)).upper()}", className="qa-subtitle"), md=3),
                        dbc.Col(html.Div(f"{t(lang, 'report.analysis_week')}: {_fmt_week(meta.get('analysis_week'))}", className="qa-subtitle"), md=3),
                        dbc.Col(html.Div(f"{t(lang, 'report.comparison_week')}: {_fmt_week(meta.get('comparison_week'))}", className="qa-subtitle"), md=3),
                        dbc.Col(
                            html.Div(
                                f"{t(lang, 'report.snapshot_coverage')}: {t(lang, 'report.snapshot_coverage_value', count=snapshot_status.get('snapshot_count', 0))}",
                                className="qa-subtitle",
                            ),
                            md=3,
                        ),
                    ],
                    className="gy-2",
                ),
            ]
        ),
        className="qa-panel qa-table-card mb-3 qa-report-header",
    )

    backlog_table = _management_table_card(
        backlog_risks,
        columns=[
            (t(lang, "table.stage_type"), "stage_category"),
            (t(lang, "table.building_family"), "building_family"),
            (t(lang, "table.open_backlog"), "open_backlog"),
            (t(lang, "table.oldest_ref_week"), "oldest_reference_week"),
            (t(lang, "table.max_age_w"), "max_age_weeks"),
        ],
        title=t(lang, "report.top_backlog_risks"),
        empty_message=t(lang, "empty.no_backlog_groups"),
    )
    stagnant_table = _management_table_card(
        stagnant_groups,
        columns=[
            (t(lang, "table.stage_type"), "stage_category"),
            (t(lang, "table.building_family"), "building_family"),
            (t(lang, "table.open_backlog"), "open_backlog"),
            (t(lang, "table.released_this_week"), "released_this_week"),
            (t(lang, "table.cum_approved_growth"), "cumulative_approved_growth"),
        ],
        title=t(lang, "report.top_stagnant_groups"),
        empty_message=t(lang, "empty.no_stagnant_groups"),
    )

    return html.Div(
        [
            header,
            html.Div(executive_cards(payload.get("executive_kpis", {}), lang=lang), className="mb-3"),
            html.Div(
                [
                    html.H6(t(lang, "report.weekly_highlights"), className="qa-section-title mt-1 mb-2"),
                    dbc.Row(highlight_cards),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(backlog_table, xs=12, lg=6, className="mb-3"),
                    dbc.Col(stagnant_table, xs=12, lg=6, className="mb-3"),
                ]
            ),
            html.Div(executive_summary_table(executive_summary, lang=lang)),
        ]
    )


def backlog_aging_summary(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    summary = payload.get("backlog_aging_summary", {})
    groups = summary.get("groups", [])

    header_cards = dbc.Row(
        [
            _kpi_card(t(lang, "kpi.open_backlog"), _fmt_int(summary.get("total_open_backlog", 0)), t(lang, "kpi.pending_plus_review"), "warning", lg=4),
            _kpi_card(t(lang, "kpi.oldest_ref_week"), _fmt_week(summary.get("oldest_reference_week")), t(lang, "kpi.earliest_open_week"), "secondary", lg=4),
            _kpi_card(t(lang, "kpi.max_age"), _fmt_int(summary.get("max_age_weeks", 0)), t(lang, "kpi.weeks_since_planned"), "danger", lg=4),
        ],
        className="mb-1",
    )

    if not groups:
        table = dbc.Card(
            dbc.CardBody(html.Div(t(lang, "empty.no_backlog_groups"), className="text-muted")),
            className="qa-panel qa-table-card",
        )
        return html.Div([header_cards, table])

    table_df = pd.DataFrame(groups)
    display = pd.DataFrame(
        {
            t(lang, "table.stage_type"): table_df["stage_category"].astype(str),
            t(lang, "table.building_family"): table_df["building_family"].astype(str),
            t(lang, "table.open_backlog"): table_df["open_backlog"].apply(_fmt_int),
            t(lang, "table.pending"): table_df["pending_dossiers"].apply(_fmt_int),
            t(lang, "table.in_review"): table_df["in_review_dossiers"].apply(_fmt_int),
            t(lang, "table.missing_ref_week"): table_df["rows_without_reference_week"].apply(_fmt_int),
            t(lang, "table.oldest_ref_week"): table_df["oldest_reference_week"].apply(_fmt_week),
            t(lang, "table.max_age_w"): table_df["max_age_weeks"].apply(_fmt_int),
            t(lang, "table.avg_age_w"): table_df["avg_age_weeks"].apply(lambda value: f"{float(value):.1f}" if value is not None else "—"),
        }
    )

    stage_col = t(lang, "table.stage_type")
    family_col = t(lang, "table.building_family")

    table = dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                data=display.to_dict("records"),
                columns=[{"name": column, "id": column} for column in display.columns],
                page_action="none",
                style_table={"overflowX": "auto"},
                style_cell={
                    "fontSize": "12px",
                    "padding": "8px 10px",
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "border": "none",
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "right",
                },
                style_cell_conditional=[
                    {"if": {"column_id": stage_col}, "textAlign": "left", "minWidth": "180px"},
                    {"if": {"column_id": family_col}, "textAlign": "left", "fontWeight": "600", "minWidth": "110px"},
                ],
                style_header={
                    "backgroundColor": "#eef3f8",
                    "color": "#10222f",
                    "fontWeight": "700",
                    "borderBottom": "1px solid #9db4c7",
                    "textTransform": "uppercase",
                    "fontSize": "11px",
                    "letterSpacing": "0.03em",
                },
                style_data={
                    "backgroundColor": "#ffffff",
                    "color": "#10222f",
                    "borderBottom": "1px solid #d8e2eb",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8fbfd"},
                ],
            )
        ),
        className="qa-panel qa-table-card",
    )
    return html.Div([header_cards, table])


def stagnant_groups_summary(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    summary = payload.get("stagnant_groups_summary", {})
    groups = summary.get("groups", [])

    header_cards = dbc.Row(
        [
            _kpi_card(t(lang, "kpi.stagnant_groups"), _fmt_int(summary.get("stagnant_groups", 0)), t(lang, "kpi.no_movement_groups"), "danger", lg=6),
            _kpi_card(t(lang, "kpi.backlog_in_stagnant"), _fmt_int(summary.get("total_open_backlog", 0)), t(lang, "kpi.open_in_stagnant"), "warning", lg=6),
        ],
        className="mb-1",
    )

    if not groups:
        table = dbc.Card(
            dbc.CardBody(html.Div(t(lang, "empty.no_stagnant_groups"), className="text-muted")),
            className="qa-panel qa-table-card",
        )
        return html.Div([header_cards, table])

    table_df = pd.DataFrame(groups)
    display = pd.DataFrame(
        {
            t(lang, "table.stage_type"): table_df["stage_category"].astype(str),
            t(lang, "table.building_family"): table_df["building_family"].astype(str),
            t(lang, "table.open_backlog"): table_df["open_backlog"].apply(_fmt_int),
            t(lang, "table.oldest_ref_week"): table_df["oldest_reference_week"].apply(_fmt_week),
            t(lang, "table.max_age_w"): table_df["max_age_weeks"].apply(_fmt_int),
            t(lang, "table.released_this_week"): table_df["released_this_week"].apply(_fmt_int),
            t(lang, "table.prev_week_releases"): table_df["released_previous_week"].apply(_fmt_int),
            t(lang, "table.cum_approved_growth"): table_df["cumulative_approved_growth"].apply(_fmt_signed_int),
            t(lang, "table.cum_weight_growth"): table_df["cumulative_released_weight_t_growth"].apply(_fmt_signed_tons),
        }
    )

    stage_col = t(lang, "table.stage_type")
    family_col = t(lang, "table.building_family")

    table = dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                data=display.to_dict("records"),
                columns=[{"name": column, "id": column} for column in display.columns],
                page_action="none",
                style_table={"overflowX": "auto"},
                style_cell={
                    "fontSize": "12px",
                    "padding": "8px 10px",
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "border": "none",
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "right",
                },
                style_cell_conditional=[
                    {"if": {"column_id": stage_col}, "textAlign": "left", "minWidth": "180px"},
                    {"if": {"column_id": family_col}, "textAlign": "left", "fontWeight": "600", "minWidth": "110px"},
                ],
                style_header={
                    "backgroundColor": "#eef3f8",
                    "color": "#10222f",
                    "fontWeight": "700",
                    "borderBottom": "1px solid #9db4c7",
                    "textTransform": "uppercase",
                    "fontSize": "11px",
                    "letterSpacing": "0.03em",
                },
                style_data={
                    "backgroundColor": "#ffffff",
                    "color": "#10222f",
                    "borderBottom": "1px solid #d8e2eb",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8fbfd"},
                ],
            )
        ),
        className="qa-panel qa-table-card",
    )
    return html.Div([header_cards, table])


def executive_summary_table(summary_df: Any, lang: str = "en") -> dbc.Card:
    if summary_df is None or getattr(summary_df, "empty", True):
        return dbc.Card(
            dbc.CardBody(html.Div(t(lang, "empty.no_data_selected_filters"), className="text-muted")),
            className="qa-panel qa-table-card",
        )

    display = summary_df.copy()
    family_col = t(lang, "table.building_family")
    stage_col = t(lang, "table.stage_type")
    total_col = t(lang, "table.total_dossiers")
    approved_col = t(lang, "table.approved")
    pending_col = t(lang, "table.pending")
    review_col = t(lang, "table.in_review")
    approval_pct_col = t(lang, "table.approval_pct")
    released_weight_col = t(lang, "table.released_weight")
    out_scope_col = t(lang, "table.out_of_scope")

    display[family_col] = display["building_family"].astype(str)
    display[stage_col] = display["stage_category"].astype(str)
    display[total_col] = display["total_dossiers"].apply(_fmt_int)
    display[approved_col] = display["approved"].apply(_fmt_int)
    display[pending_col] = display["pending"].apply(_fmt_int)
    display[review_col] = display["in_review"].apply(_fmt_int)
    display[approval_pct_col] = display["approval_pct"].apply(_fmt_pct)
    display[released_weight_col] = display["released_weight_t"].apply(_fmt_tons)
    display[out_scope_col] = display["out_of_scope"].apply(_fmt_int)

    table_columns = [
        family_col,
        stage_col,
        total_col,
        approved_col,
        pending_col,
        review_col,
        approval_pct_col,
        released_weight_col,
        out_scope_col,
    ]

    return dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                data=display[table_columns].to_dict("records"),
                columns=[{"name": column, "id": column} for column in table_columns],
                page_action="none",
                style_table={"overflowX": "auto"},
                style_cell={
                    "fontSize": "12px",
                    "padding": "8px 10px",
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "border": "none",
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "right",
                },
                style_cell_conditional=[
                    {"if": {"column_id": family_col}, "textAlign": "left", "fontWeight": "600", "minWidth": "110px"},
                    {"if": {"column_id": stage_col}, "textAlign": "left", "minWidth": "200px"},
                ],
                style_header={
                    "backgroundColor": "#eef3f8",
                    "color": "#10222f",
                    "fontWeight": "700",
                    "borderBottom": "1px solid #9db4c7",
                    "textTransform": "uppercase",
                    "fontSize": "11px",
                    "letterSpacing": "0.03em",
                },
                style_data={
                    "backgroundColor": "#ffffff",
                    "color": "#10222f",
                    "borderBottom": "1px solid #d8e2eb",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8fbfd"},
                ],
            )
        ),
        className="qa-panel qa-table-card",
    )
