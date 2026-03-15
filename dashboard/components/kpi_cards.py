"""
Dashboard Components — KPI Cards
==================================
Reusable Dash HTML/Bootstrap KPI card components.
Requires dash-bootstrap-components.
"""

from __future__ import annotations

from typing import Any, Optional, Union

import dash_bootstrap_components as dbc
from dash import html


def kpi_card(
    title: str,
    value: Union[str, int, float],
    subtitle: Optional[str] = None,
    color: str = "primary",
    icon: Optional[str] = None,
) -> dbc.Card:
    """
    Render a single KPI metric card.

    Args:
        title: Card label shown above the number.
        value: Main metric value.
        subtitle: Optional secondary text (target, unit).
        color: Bootstrap colour name (success, danger, warning, primary …).
        icon: Optional Bootstrap icon class (e.g. 'bi bi-check-circle').
    """
    header_content = [html.Span(title, className="kpi-title")]
    if icon:
        header_content.insert(0, html.I(className=f"{icon} me-2"))

    value_str = (
        f"{value:.1f}%" if isinstance(value, float) and value <= 100
        else f"{value:,}" if isinstance(value, (int, float))
        else str(value)
    )

    return dbc.Card(
        dbc.CardBody([
            html.P(header_content, className="text-muted mb-1 small fw-semibold"),
            html.H3(value_str, className=f"text-{color} mb-0 fw-bold"),
            html.Small(subtitle, className="text-muted") if subtitle else None,
        ]),
        className="shadow-sm h-100",
    )


def kpi_row(kpis: dict[str, Any]) -> dbc.Row:
    """
    Render the standard 3-column KPI strip for the Dossier module.

    Args:
        kpis: dict returned by ``analytics.metrics.compute_global_metrics()``.
    """
    pct_lib = kpis.get("pct_liberado", 0)
    pct_peso = kpis.get("pct_peso_liberado", 0)

    # colour thresholds
    def _color(pct: float) -> str:
        if pct >= 80:
            return "success"
        if pct >= 50:
            return "warning"
        return "danger"

    cards = [
        dbc.Col(
            kpi_card(
                "Dossieres Totales",
                kpis.get("total_dossiers", 0),
                subtitle="registros",
                color="primary",
                icon="bi bi-folder2-open",
            ),
            xs=12, sm=6, md=4, lg=2, className="mb-3",
        ),
        dbc.Col(
            kpi_card(
                "Dossieres Liberados",
                kpis.get("dossiers_liberados", 0),
                subtitle=f"{pct_lib:.1f}% del total",
                color=_color(pct_lib),
                icon="bi bi-check-circle",
            ),
            xs=12, sm=6, md=4, lg=2, className="mb-3",
        ),
        dbc.Col(
            kpi_card(
                "% Liberado",
                pct_lib,
                subtitle="por unidades",
                color=_color(pct_lib),
                icon="bi bi-bar-chart",
            ),
            xs=12, sm=6, md=4, lg=2, className="mb-3",
        ),
        dbc.Col(
            kpi_card(
                "Peso Total (ton)",
                round(kpis.get("peso_total_ton", 0), 1),
                subtitle="kg / 1000",
                color="primary",
                icon="bi bi-boxes",
            ),
            xs=12, sm=6, md=4, lg=2, className="mb-3",
        ),
        dbc.Col(
            kpi_card(
                "Peso Liberado (ton)",
                round(kpis.get("peso_liberado_ton", 0), 1),
                subtitle=f"{pct_peso:.1f}% del peso total",
                color=_color(pct_peso),
                icon="bi bi-truck",
            ),
            xs=12, sm=6, md=4, lg=2, className="mb-3",
        ),
        dbc.Col(
            kpi_card(
                "% Peso Liberado",
                pct_peso,
                subtitle="por tonelaje",
                color=_color(pct_peso),
                icon="bi bi-speedometer2",
            ),
            xs=12, sm=6, md=4, lg=2, className="mb-3",
        ),
    ]
    return dbc.Row(cards, className="g-2")
