"""Card components for KPI sections."""

from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, html


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
            className="qa-panel h-100",
        ),
        **col_kwargs,
    )


def executive_cards(kpis: Dict[str, Any]) -> html.Div:
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

    pct_approved = f"{approved / total * 100:.1f}% of total" if total else "—"

    return html.Div(
        [
            dbc.Row(
                [
                    _kpi_card("Total Dossiers", _fmt_int(total), "In contractual scope", "primary"),
                    _kpi_card("Approved", _fmt_int(approved), pct_approved, "success"),
                    _kpi_card("Pending", _fmt_int(pending), "Awaiting release", "warning"),
                    _kpi_card("In Review", _fmt_int(in_review), "INPROS internal review", "info"),
                ]
            ),
            dbc.Row(
                [
                    _kpi_card("Out Of Scope Rows", _fmt_int(out_of_scope), "Excluded from contractual KPIs", "secondary", lg=4, xl=2),
                    _kpi_card("Released %", f"{float(pct_liberado):.1f}%", "Dossiers released", "success", lg=4, xl=2),
                    _kpi_card("Total In-Scope Weight (t)", _fmt_tons(peso_total_ton), "In-scope contractual weight", "primary", lg=6, xl=3),
                    _kpi_card("Released Weight (t)", _fmt_tons(peso_liberado_ton), "Weight with approved status", "info", lg=6, xl=3),
                    _kpi_card("Released Weight %", f"{float(pct_peso_liberado):.1f}%", "Weight-based progress", "warning", lg=4, xl=2),
                ],
                className="mt-1",
            ),
        ]
    )


def quality_cards(kpis: Dict[str, Any]) -> dbc.Row:
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
            "Open Backlog",
            _fmt_int(open_backlog),
            f"{open_backlog_pct:.1f}% of in-scope dossiers",
            "warning",
            lg=6,
            xl=4,
        ),
        _kpi_card(
            "Approval Delta",
            _fmt_int(approval_delta),
            "Approved minus open backlog",
            "info",
            lg=6,
            xl=4,
        ),
    ]

    if rejected > 0:
        cards.append(
            _kpi_card(
                "Rejected Rate",
                f"{rejection_rate:.1f}%",
                "Rejected dossier ratio",
                "danger",
                lg=6,
                xl=4,
            )
        )

    return dbc.Row(cards)


def weekly_management_cards(payload: Dict[str, Any]) -> html.Div:
    delta = payload.get("delta_kpis", {})
    analysis_week = delta.get("analysis_week")
    previous_week = delta.get("previous_week")
    week_subtitle = f"{_fmt_week(analysis_week)} vs {_fmt_week(previous_week)}"

    released_this_week = delta.get("released_this_week", 0)
    released_weight_this_week = delta.get("released_weight_t_this_week", 0.0)
    change_vs_previous_week = delta.get("change_vs_previous_week", 0)
    weight_change_vs_previous_week = delta.get("weight_change_t_vs_previous_week", 0.0)

    return html.Div(
        dbc.Row(
            [
                _kpi_card("Released This Week", _fmt_int(released_this_week), week_subtitle, "success"),
                _kpi_card("Released Weight This Week", _fmt_tons(released_weight_this_week), "Actual released weight (t)", "info"),
                _kpi_card("Change vs Previous Week", _fmt_signed_int(change_vs_previous_week), week_subtitle, _tone_for_delta(change_vs_previous_week)),
                _kpi_card("Weight Change vs Previous Week", _fmt_signed_tons(weight_change_vs_previous_week), "Delta in released weight (t)", _tone_for_delta(weight_change_vs_previous_week)),
            ]
        )
    )


def backlog_aging_summary(payload: Dict[str, Any]) -> html.Div:
    summary = payload.get("backlog_aging_summary", {})
    groups = summary.get("groups", [])

    header_cards = dbc.Row(
        [
            _kpi_card("Open Backlog", _fmt_int(summary.get("total_open_backlog", 0)), "Pending + In Review dossiers", "warning", lg=4),
            _kpi_card("Oldest Reference Week", _fmt_week(summary.get("oldest_reference_week")), "Earliest planned week still open", "secondary", lg=4),
            _kpi_card("Max Age", _fmt_int(summary.get("max_age_weeks", 0)), "Weeks since planned reference", "danger", lg=4),
        ],
        className="mb-1",
    )

    if not groups:
        table = dbc.Card(
            dbc.CardBody(html.Div("No backlog aging groups for the selected filters.", className="text-muted")),
            className="qa-panel",
        )
        return html.Div([header_cards, table])

    table_df = pd.DataFrame(groups)
    display = pd.DataFrame(
        {
            "Stage / Dossier Type": table_df["stage_category"].astype(str),
            "Building Family": table_df["building_family"].astype(str),
            "Open Backlog": table_df["open_backlog"].apply(_fmt_int),
            "Pending": table_df["pending_dossiers"].apply(_fmt_int),
            "In Review": table_df["in_review_dossiers"].apply(_fmt_int),
            "Missing Ref Week": table_df["rows_without_reference_week"].apply(_fmt_int),
            "Oldest Ref Week": table_df["oldest_reference_week"].apply(_fmt_week),
            "Max Age (w)": table_df["max_age_weeks"].apply(_fmt_int),
            "Avg Age (w)": table_df["avg_age_weeks"].apply(lambda value: f"{float(value):.1f}" if value is not None else "—"),
        }
    )

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
                    {"if": {"column_id": "Stage / Dossier Type"}, "textAlign": "left", "minWidth": "180px"},
                    {"if": {"column_id": "Building Family"}, "textAlign": "left", "fontWeight": "600", "minWidth": "110px"},
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
        className="qa-panel",
    )
    return html.Div([header_cards, table])


def stagnant_groups_summary(payload: Dict[str, Any]) -> html.Div:
    summary = payload.get("stagnant_groups_summary", {})
    groups = summary.get("groups", [])

    header_cards = dbc.Row(
        [
            _kpi_card("Stagnant Groups", _fmt_int(summary.get("stagnant_groups", 0)), "Groups with open backlog and no weekly movement", "danger", lg=6),
            _kpi_card("Backlog in Stagnant Groups", _fmt_int(summary.get("total_open_backlog", 0)), "Open dossiers inside stagnant groups", "warning", lg=6),
        ],
        className="mb-1",
    )

    if not groups:
        table = dbc.Card(
            dbc.CardBody(html.Div("No stagnant groups for the selected filters.", className="text-muted")),
            className="qa-panel",
        )
        return html.Div([header_cards, table])

    table_df = pd.DataFrame(groups)
    display = pd.DataFrame(
        {
            "Stage / Dossier Type": table_df["stage_category"].astype(str),
            "Building Family": table_df["building_family"].astype(str),
            "Open Backlog": table_df["open_backlog"].apply(_fmt_int),
            "Oldest Ref Week": table_df["oldest_reference_week"].apply(_fmt_week),
            "Max Age (w)": table_df["max_age_weeks"].apply(_fmt_int),
            "Released This Week": table_df["released_this_week"].apply(_fmt_int),
            "Prev Week Releases": table_df["released_previous_week"].apply(_fmt_int),
            "Cum Approved Growth": table_df["cumulative_approved_growth"].apply(_fmt_signed_int),
            "Cum Weight Growth (t)": table_df["cumulative_released_weight_t_growth"].apply(_fmt_signed_tons),
        }
    )

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
                    {"if": {"column_id": "Stage / Dossier Type"}, "textAlign": "left", "minWidth": "180px"},
                    {"if": {"column_id": "Building Family"}, "textAlign": "left", "fontWeight": "600", "minWidth": "110px"},
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
        className="qa-panel",
    )
    return html.Div([header_cards, table])


def executive_summary_table(summary_df: Any) -> dbc.Card:
    if summary_df is None or getattr(summary_df, "empty", True):
        return dbc.Card(
            dbc.CardBody(html.Div("No data available for the selected filters.", className="text-muted")),
            className="qa-panel",
        )

    display = summary_df.copy()
    display["Building Family"] = display["building_family"].astype(str)
    display["Stage / Dossier Type"] = display["stage_category"].astype(str)
    display["Total Dossiers"] = display["total_dossiers"].apply(_fmt_int)
    display["Approved"] = display["approved"].apply(_fmt_int)
    display["Pending"] = display["pending"].apply(_fmt_int)
    display["In Review"] = display["in_review"].apply(_fmt_int)
    display["Approval %"] = display["approval_pct"].apply(_fmt_pct)
    display["Released Weight (t)"] = display["released_weight_t"].apply(_fmt_tons)
    display["Out of Scope"] = display["out_of_scope"].apply(_fmt_int)

    table_columns = [
        "Building Family",
        "Stage / Dossier Type",
        "Total Dossiers",
        "Approved",
        "Pending",
        "In Review",
        "Approval %",
        "Released Weight (t)",
        "Out of Scope",
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
                    {"if": {"column_id": "Building Family"}, "textAlign": "left", "fontWeight": "600", "minWidth": "110px"},
                    {"if": {"column_id": "Stage / Dossier Type"}, "textAlign": "left", "minWidth": "200px"},
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
        className="qa-panel",
    )
