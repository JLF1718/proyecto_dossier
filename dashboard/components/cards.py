"""Card components for KPI sections."""

from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
from dash import html


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
                    _kpi_card("Total Weight (t)", _fmt_tons(peso_total_ton), "In-scope dossier weight", "primary", lg=6, xl=3),
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
