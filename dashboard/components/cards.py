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

def _fmt_bool(value: Any, lang: str = "en") -> str:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return t(lang, "label.yes")
    if normalized in {"false", "0", "no"}:
        return t(lang, "label.no")
    return "—"


def _fmt_status(value: Any, lang: str = "en") -> str:
    normalized = str(value).strip().lower().replace(" ", "_")
    if normalized in {"approved", "aprobado", "liberado", "aceptado"}:
        return t(lang, "status.approved")
    if normalized in {"in_review", "in review", "en_revision_inpros", "en revision inpros", "en_revisión", "en revisión", "revisión inpros"}:
        return t(lang, "status.in_review")
    if normalized:
        return t(lang, "status.pending")
    return "—"


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


def _tone_for_age(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "secondary"
    if number > 15:
        return "danger"
    if number >= 10:
        return "warning"
    return "success"


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


def stakeholder_overview_cards(
    kpis: Dict[str, Any],
    weekly_payload: Dict[str, Any],
    lang: str = "en",
) -> html.Div:
    total = int(kpis.get("total_dossiers", kpis.get("total", 0)) or 0)
    approved = int(kpis.get("approved_dossiers", kpis.get("approved", 0)) or 0)
    pending = int(kpis.get("pending_dossiers", kpis.get("pending", 0)) or 0)
    in_review = int(kpis.get("in_review_dossiers", 0) or 0)
    open_backlog = pending + in_review
    open_backlog_pct = (open_backlog / total * 100.0) if total else 0.0

    backlog_summary = weekly_payload.get("backlog_aging_summary", {})
    delta = weekly_payload.get("delta_kpis", {})
    analysis_week = delta.get("analysis_week")
    previous_week = delta.get("previous_week")
    week_subtitle = t(lang, "label.week_compare", current=_fmt_week(analysis_week), previous=_fmt_week(previous_week))

    return html.Div(
        dbc.Row(
            [
                _kpi_card(t(lang, "kpi.total_dossiers"), _fmt_int(total), t(lang, "kpi.in_scope"), "primary", lg=4, xl=2),
                _kpi_card(
                    t(lang, "kpi.approved"),
                    _fmt_int(approved),
                    t(lang, "label.of_total", value=f"{(approved / total * 100.0):.1f}") if total else "—",
                    "success",
                    lg=4,
                    xl=2,
                ),
                _kpi_card(
                    t(lang, "kpi.open_backlog"),
                    _fmt_int(open_backlog),
                    t(lang, "label.of_in_scope", value=f"{open_backlog_pct:.1f}"),
                    "warning" if open_backlog > 0 else "success",
                    lg=4,
                    xl=2,
                ),
                _kpi_card(
                    t(lang, "kpi.max_age"),
                    _fmt_int(backlog_summary.get("max_age_weeks", 0)),
                    t(lang, "kpi.weeks_since_planned"),
                    _tone_for_age(backlog_summary.get("max_age_weeks", 0)),
                    lg=4,
                    xl=2,
                ),
                _kpi_card(
                    t(lang, "kpi.released_this_week"),
                    _fmt_int(delta.get("released_this_week", 0)),
                    week_subtitle,
                    "success",
                    lg=4,
                    xl=2,
                ),
                _kpi_card(
                    t(lang, "kpi.released_weight"),
                    _fmt_tons(kpis.get("peso_liberado_ton", 0.0)),
                    t(lang, "kpi.weight_with_approved"),
                    "info",
                    lg=4,
                    xl=2,
                ),
            ]
        )
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


def juntas_kpi_row(totales: Dict[str, Any]) -> html.Div:
    total_juntas = int(totales.get("total_juntas", 0) or 0)
    liberadas = int(totales.get("liberadas", 0) or 0)
    pendientes = int(totales.get("pendientes", 0) or 0)
    pct_avance = float(totales.get("pct_avance_global", 0.0) or 0.0)

    if pct_avance < 30.0:
        avance_tone = "danger"
    elif pct_avance <= 80.0:
        avance_tone = "warning"
    else:
        avance_tone = "success"

    return html.Div(
        dbc.Row(
            [
                _kpi_card(
                    "Juntas liberadas",
                    f"{_fmt_int(liberadas)} / {_fmt_int(total_juntas)}",
                    "Liberadas sobre total",
                    "success",
                    xs=12,
                    md=4,
                    lg=4,
                ),
                _kpi_card(
                    "Juntas pendientes",
                    _fmt_int(pendientes),
                    "Pendientes por inspeccionar",
                    "warning",
                    xs=12,
                    md=4,
                    lg=4,
                ),
                _kpi_card(
                    "% Avance inspección",
                    f"{pct_avance:.1f}%",
                    "Liberadas / total de juntas",
                    avance_tone,
                    xs=12,
                    md=4,
                    lg=4,
                ),
            ]
        )
    )


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
                _kpi_card(t(lang, "kpi.change_vs_prev"), _fmt_signed_int(change_vs_previous_week), week_subtitle, _tone_for_delta(change_vs_previous_week), lg=6, xl=3),
                _kpi_card(t(lang, "kpi.weight_change_vs_prev"), _fmt_signed_tons(weight_change_vs_previous_week), t(lang, "kpi.delta_released_weight"), _tone_for_delta(weight_change_vs_previous_week), lg=6, xl=3),
                _kpi_card(t(lang, "kpi.released_this_week"), _fmt_int(released_this_week), week_subtitle, "success", lg=6, xl=3),
                _kpi_card(t(lang, "kpi.released_weight_this_week"), _fmt_tons(released_weight_this_week), t(lang, "kpi.actual_released_weight"), "info", lg=6, xl=3),
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


def risk_exception_cards(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    """Render risk KPI cards.  Tables live in ``backlog_aging_summary`` /
    ``stagnant_groups_summary`` which are placed in the dedicated mid-page
    section.  This function intentionally returns only the four signal cards
    so they can sit directly beneath the Executive Status header.
    """
    risk = payload.get("risk_exception_summary", {})
    signals = {item.get("key"): item.get("value") for item in risk.get("signals", [])}

    return html.Div(
        dbc.Row(
            [
                _kpi_card(
                    t(lang, "kpi.max_age"),
                    _fmt_int(signals.get("oldest_backlog_age", 0)),
                    t(lang, "kpi.weeks_since_planned"),
                    "danger",
                    lg=3,
                ),
                _kpi_card(
                    t(lang, "kpi.stagnant_groups"),
                    _fmt_int(signals.get("stagnant_groups", 0)),
                    t(lang, "kpi.no_movement_groups"),
                    "danger",
                    lg=3,
                ),
                _kpi_card(
                    t(lang, "kpi.open_backlog"),
                    _fmt_int(signals.get("largest_open_backlog", 0)),
                    t(lang, "kpi.risk_attention_now"),
                    "warning",
                    lg=3,
                ),
                _kpi_card(
                    t(lang, "kpi.largest_approval_gap"),
                    _fmt_int(signals.get("largest_approval_gap", 0)),
                    t(lang, "kpi.top_risk_signals"),
                    "info",
                    lg=3,
                ),
            ]
        )
    )


def high_value_insights_cards(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    insights = payload.get("high_value_insights", [])
    if not insights:
        return html.Div(className="d-none")

    cards = []
    for insight in insights:
        key = str(insight.get("key", "")).strip().lower()
        label = t(lang, f"report.insight.{key}")
        subtitle = ""
        if insight.get("stage_category") and insight.get("building_family"):
            subtitle = f"{insight.get('stage_category')} · {insight.get('building_family')}"
        elif insight.get("building_family"):
            subtitle = str(insight.get("building_family"))
        cards.append(
            _kpi_card(
                label,
                _fmt_tons(insight.get("value")) if "weight" in key else _fmt_int(insight.get("value")),
                subtitle,
                "primary",
                lg=4,
            )
        )

    return html.Div(
        [
            html.H6(t(lang, "report.high_value_insights"), className="qa-section-title mt-1 mb-2"),
            dbc.Row(cards),
        ]
    )


def executive_report_pack(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    meta = payload.get("report_meta", {})
    highlights = payload.get("weekly_highlights", [])
    executive_summary = pd.DataFrame(payload.get("executive_summary_table", []))
    backlog_risks = payload.get("top_backlog_risks", [])
    stagnant_groups = payload.get("top_stagnant_groups", [])
    snapshot_status = meta.get("snapshot_status", {})
    risk_summary = payload.get("risk_exception_summary", {})
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
            html.Div(
                [
                    html.H6(t(lang, "report.weekly_highlights"), className="qa-section-title mt-1 mb-2"),
                    dbc.Row(highlight_cards),
                ],
                className="mb-3",
            ),
            html.Div(
                [
                    html.H6(t(lang, "report.risk_exception_focus"), className="qa-section-title mt-1 mb-2"),
                    risk_exception_cards({"risk_exception_summary": risk_summary}, lang=lang),
                ],
                className="mb-1",
            ),
            dbc.Row(
                [
                    dbc.Col(backlog_table, xs=12, lg=6, className="mb-3"),
                    dbc.Col(stagnant_table, xs=12, lg=6, className="mb-3"),
                ]
            ),
            high_value_insights_cards(payload, lang=lang),
            html.Div(executive_summary_table(executive_summary, lang=lang)),
        ]
    )


def risk_drivers_panel(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    risk = payload.get("risk_exception_summary", {}) or {}
    signals = {item.get("key"): item.get("value") for item in risk.get("signals", [])}
    backlog_groups = payload.get("backlog_aging_summary", {}).get("groups", []) or []
    stagnant_groups = payload.get("stagnant_groups_summary", {}).get("groups", []) or []

    summary_cards = dbc.Row(
        [
            _kpi_card(
                t(lang, "kpi.max_age"),
                _fmt_int(signals.get("oldest_backlog_age", 0)),
                t(lang, "kpi.weeks_since_planned"),
                _tone_for_age(signals.get("oldest_backlog_age", 0)),
                lg=3,
            ),
            _kpi_card(
                t(lang, "kpi.stagnant_groups"),
                _fmt_int(signals.get("stagnant_groups", 0)),
                t(lang, "kpi.no_movement_groups"),
                "danger",
                lg=3,
            ),
            _kpi_card(
                t(lang, "kpi.open_backlog"),
                _fmt_int(payload.get("backlog_aging_summary", {}).get("total_open_backlog", 0)),
                t(lang, "kpi.pending_plus_review"),
                "warning",
                lg=3,
            ),
            _kpi_card(
                t(lang, "kpi.largest_approval_gap"),
                _fmt_int(signals.get("largest_approval_gap", 0)),
                t(lang, "kpi.top_risk_signals"),
                "info",
                lg=3,
            ),
        ],
        className="mb-1",
    )

    backlog_table = _management_table_card(
        backlog_groups,
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

    tabs = dbc.Tabs(
        [
            dbc.Tab(backlog_table, label=t(lang, "report.top_backlog_risks")),
            dbc.Tab(stagnant_table, label=t(lang, "report.top_stagnant_groups")),
        ],
        className="qa-risk-tabs",
    )

    return html.Div([summary_cards, tabs])


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

    # Compute severity for each row: HIGH (≥15 wks), MEDIUM (≥10 wks), else normal
    age_numeric = pd.to_numeric(table_df.get("max_age_weeks", pd.Series(dtype="float")), errors="coerce").fillna(0)

    def _severity_label(age: float) -> str:
        if age >= 15:
            return "HIGH"
        if age >= 10:
            return "MEDIUM"
        return "—"

    severity_col = "Severity"
    display = pd.DataFrame(
        {
            severity_col: age_numeric.apply(_severity_label),
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
                    {"if": {"column_id": severity_col}, "textAlign": "center", "fontWeight": "700", "fontSize": "10px", "minWidth": "70px"},
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
                    {
                        "if": {"filter_query": f"{{{severity_col}}} = 'HIGH'"},
                        "backgroundColor": "#fff5f5",
                        "borderLeft": "3px solid #dc2626",
                    },
                    {
                        "if": {"filter_query": f"{{{severity_col}}} = 'HIGH'", "column_id": severity_col},
                        "color": "#dc2626",
                    },
                    {
                        "if": {"filter_query": f"{{{severity_col}}} = 'MEDIUM'"},
                        "backgroundColor": "#fffbeb",
                        "borderLeft": "3px solid #d97706",
                    },
                    {
                        "if": {"filter_query": f"{{{severity_col}}} = 'MEDIUM'", "column_id": severity_col},
                        "color": "#d97706",
                    },
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


def physical_signal_cards(payload: Dict[str, Any], lang: str = "en") -> html.Div:
    kpis = payload.get("kpis", {})
    indexed = float(kpis.get("indexed_weight_total", 0.0) or 0.0)
    tagged = float(kpis.get("week_tagged_weight", 0.0) or 0.0)
    coverage = float(kpis.get("week_trace_coverage_pct", 0.0) or 0.0) * 100.0
    blank = float(kpis.get("blank_week_historic_weight", 0.0) or 0.0)

    return html.Div(
        dbc.Row(
            [
                _kpi_card(
                    t(lang, "kpi.indexed_weight_total"),
                    _fmt_tons(indexed / 1000.0),
                    t(lang, "kpi.physical_signal_weight"),
                    "primary",
                    lg=3,
                ),
                _kpi_card(
                    t(lang, "kpi.week_tagged_weight"),
                    _fmt_tons(tagged / 1000.0),
                    t(lang, "kpi.week_tagged_weight_desc"),
                    "info",
                    lg=3,
                ),
                _kpi_card(
                    t(lang, "kpi.week_trace_coverage"),
                    _fmt_pct(coverage),
                    t(lang, "kpi.week_trace_coverage_desc"),
                    "success",
                    lg=3,
                ),
                _kpi_card(
                    t(lang, "kpi.blank_week_historic_weight"),
                    _fmt_tons(blank / 1000.0),
                    t(lang, "kpi.blank_week_historic_weight_desc"),
                    "warning",
                    lg=3,
                ),
            ]
        )
    )


def physical_signal_comparison_table(payload: Dict[str, Any], lang: str = "en") -> dbc.Card:
    records = payload.get("comparison", [])
    if not records:
        return dbc.Card(
            dbc.CardBody(html.Div(t(lang, "empty.no_data_selected_filters"), className="text-muted")),
            className="qa-panel qa-table-card",
        )

    frame = pd.DataFrame(records)
    display = pd.DataFrame(
        {
            "block": frame.get("block", pd.Series(dtype="object")).astype(str),
            "family": frame.get("family", pd.Series(dtype="object")).fillna("-"),
            "building": frame.get("building", pd.Series(dtype="object")).fillna("-"),
            "etapa": frame.get("etapa", pd.Series(dtype="object")).fillna("-"),
            "fase": frame.get("fase", pd.Series(dtype="object")).fillna("-"),
            "documented_progress_pct": (pd.to_numeric(frame.get("documented_progress_pct", 0), errors="coerce").fillna(0.0) * 100.0).round(1),
            "physical_signal_pct": (pd.to_numeric(frame.get("physical_signal_pct", 0), errors="coerce").fillna(0.0) * 100.0).round(1),
            "alignment_status": frame.get("alignment_status", pd.Series(dtype="object")).astype(str),
        }
    )

    columns = [
        ("block", "block"),
        ("family", "family"),
        ("building", "building"),
        ("etapa", "etapa"),
        ("fase", "fase"),
        ("documented_progress_pct", "documented_progress_pct"),
        ("physical_signal_pct", "physical_signal_pct"),
        ("alignment_status", "alignment_status"),
    ]

    table = display[[source for _, source in columns]].copy()
    table = table.rename(columns={
        "block": t(lang, "table.block"),
        "family": t(lang, "table.building_family"),
        "building": t(lang, "table.building"),
        "etapa": t(lang, "table.stage"),
        "fase": t(lang, "table.phase"),
        "documented_progress_pct": t(lang, "table.documented_progress_pct"),
        "physical_signal_pct": t(lang, "table.physical_signal_pct"),
        "alignment_status": t(lang, "table.alignment_status"),
    })

    for pct_col in (t(lang, "table.documented_progress_pct"), t(lang, "table.physical_signal_pct")):
        table[pct_col] = table[pct_col].map(lambda v: f"{float(v):.1f}%")

    status_col = t(lang, "table.alignment_status")
    table[status_col] = table[status_col].map(lambda s: t(lang, f"alignment.{s}") if s else "-")

    return dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                data=table.to_dict("records"),
                columns=[{"name": c, "id": c} for c in table.columns],
                page_action="native",
                page_size=10,
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
            )
        ),
        className="qa-panel qa-table-card",
    )


def physical_signal_exceptions_table(payload: Dict[str, Any], lang: str = "en") -> dbc.Card:
    records = payload.get("exceptions", [])
    if not records:
        return dbc.Card(
            dbc.CardBody(html.Div(t(lang, "empty.no_data_selected_filters"), className="text-muted")),
            className="qa-panel qa-table-card",
        )

    frame = pd.DataFrame(records)
    table = pd.DataFrame(
        {
            t(lang, "table.exception_type"): frame.get("exception_type", pd.Series(dtype="object")).astype(str),
            t(lang, "table.severity"): frame.get("severity", pd.Series(dtype="object")).astype(str),
            t(lang, "table.block"): frame.get("block", pd.Series(dtype="object")).astype(str),
            t(lang, "table.week"): frame.get("week", pd.Series(dtype="object")).fillna("-"),
            t(lang, "table.details"): frame.get("details", pd.Series(dtype="object")).astype(str),
        }
    )
    table[t(lang, "table.severity")] = table[t(lang, "table.severity")].str.upper()

    return dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                data=table.to_dict("records"),
                columns=[{"name": c, "id": c} for c in table.columns],
                page_action="native",
                page_size=8,
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
            )
        ),
        className="qa-panel qa-table-card",
    )


def scope_detail_table(detail_df: pd.DataFrame, lang: str = "en") -> dbc.Card:
    if detail_df is None or getattr(detail_df, "empty", True):
        return dbc.Card(
            dbc.CardBody(html.Div(t(lang, "empty.no_data_selected_filters"), className="text-muted")),
            className="qa-panel qa-table-card",
        )

    display = detail_df.copy()

    if "building_family" not in display.columns and "bloque" in display.columns:
        display["building_family"] = display["bloque"].astype(str).str.split("_").str[0]
    if "stage_category" not in display.columns and "etapa" in display.columns:
        display["stage_category"] = pd.to_numeric(display["etapa"], errors="coerce").map(
            lambda value: f"Stage {int(value)}" if pd.notna(value) else "—"
        )

    table = pd.DataFrame(
        {
            t(lang, "table.id"): display.get("numero", pd.Series(dtype="object")).map(_fmt_int),
            t(lang, "table.contractor"): display.get("contractor", pd.Series(dtype="object")).fillna("—").astype(str).str.upper(),
            t(lang, "table.building"): display.get("building_family", pd.Series(dtype="object")).fillna("—").astype(str),
            t(lang, "table.phase"): pd.to_numeric(display.get("fase", pd.Series(dtype="object")), errors="coerce").map(
                lambda value: _fmt_int(value) if pd.notna(value) else "—"
            ),
            t(lang, "table.stage"): display.get("stage_category", pd.Series(dtype="object")).fillna("—").astype(str),
            t(lang, "table.block"): display.get("bloque", pd.Series(dtype="object")).fillna("—").astype(str),
            t(lang, "table.status"): display.get("estatus", pd.Series(dtype="object")).map(lambda value: _fmt_status(value, lang=lang)),
            t(lang, "table.release_week"): pd.to_numeric(display.get("semana_liberacion_dossier", pd.Series(dtype="object")), errors="coerce").map(
                lambda value: _fmt_week(value) if pd.notna(value) else "—"
            ),
            t(lang, "table.weight_t"): pd.to_numeric(display.get("peso_dossier_kg", pd.Series(dtype="object")), errors="coerce").fillna(0.0).map(
                lambda value: _fmt_tons(float(value) / 1000.0)
            ),
            t(lang, "table.scope_group"): display.get("contract_group", pd.Series(dtype="object")).fillna("—").astype(str).str.replace("_", " ").str.title(),
            t(lang, "table.kpi_scope"): display.get("in_contract_scope", pd.Series(dtype="object")).map(lambda value: _fmt_bool(value, lang=lang)),
        }
    )

    return dbc.Card(
        dbc.CardBody(
            dash_table.DataTable(
                data=table.to_dict("records"),
                columns=[{"name": c, "id": c} for c in table.columns],
                page_action="native",
                page_size=15,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={
                    "fontSize": "12px",
                    "padding": "8px 10px",
                    "fontFamily": "IBM Plex Sans, sans-serif",
                    "border": "none",
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "left",
                    "minWidth": "110px",
                },
                style_cell_conditional=[
                    {"if": {"column_id": t(lang, "table.id")}, "textAlign": "right", "minWidth": "72px", "fontWeight": "600"},
                    {"if": {"column_id": t(lang, "table.weight_t")}, "textAlign": "right", "minWidth": "96px"},
                    {"if": {"column_id": t(lang, "table.block")}, "minWidth": "120px", "fontWeight": "600"},
                    {"if": {"column_id": t(lang, "table.contractor")}, "minWidth": "110px", "fontWeight": "600"},
                    {"if": {"column_id": t(lang, "table.release_week")}, "minWidth": "96px", "textAlign": "center"},
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
