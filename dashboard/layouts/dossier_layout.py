"""
Dashboard Layout — Dossier Control Page
=========================================
Renders the Dossier Control view: filters, KPI strip, charts.
"""

from __future__ import annotations

from typing import List

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.charts import loading_graph


def _filter_bar(contractors: List[str], stages: List[str]) -> dbc.Card:
    """Top filter row: contractor + stage + status + delivery week."""
    return dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Contratista", className="form-label small fw-semibold"),
                            dcc.Dropdown(
                                id="filter-contractor",
                                options=[{"label": "Todos", "value": "ALL"}]
                                + [{"label": c, "value": c} for c in contractors],
                                value="ALL",
                                clearable=False,
                                className="qa-dropdown",
                            ),
                        ],
                        xs=12, sm=6, md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Etapa", className="form-label small fw-semibold"),
                            dcc.Dropdown(
                                id="filter-stage",
                                options=[{"label": "Todas", "value": "ALL"}]
                                + [{"label": s, "value": s} for s in stages],
                                value="ALL",
                                clearable=False,
                                className="qa-dropdown",
                            ),
                        ],
                        xs=12, sm=6, md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Estatus", className="form-label small fw-semibold"),
                            dcc.Dropdown(
                                id="filter-status",
                                options=[
                                    {"label": "Todos", "value": "ALL"},
                                    {"label": "Liberado", "value": "LIBERADO"},
                                    {"label": "En Revisión", "value": "EN_REVISIÓN"},
                                    {"label": "Observado", "value": "OBSERVADO"},
                                    {"label": "Planeado", "value": "PLANEADO"},
                                ],
                                value="ALL",
                                clearable=False,
                                className="qa-dropdown",
                            ),
                        ],
                        xs=12, sm=6, md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Semana Entrega", className="form-label small fw-semibold"),
                            dcc.Dropdown(
                                id="filter-delivery",
                                options=[{"label": "Todas", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="qa-dropdown",
                            ),
                        ],
                        xs=12, sm=6, md=3,
                    ),
                ],
                className="g-3",
            )
        ),
        className="shadow-sm mb-3",
    )


def dossier_layout(contractors: List[str], stages: List[str]) -> html.Div:
    """Full Dossier Control page layout."""
    return html.Div(
        [
            # Page header
            dbc.Row(
                dbc.Col(
                    html.H4(
                        [html.I(className="bi bi-folder2-open me-2 text-success"), "Control de Dossieres"],
                        className="mb-3",
                    )
                )
            ),
            # Filter bar
            _filter_bar(contractors, stages),
            # KPI strip (populated by callback)
            html.Div(id="kpi-row", className="mb-3"),
            # Charts row 1 — status bar + stage × status
            dbc.Row(
                [
                    dbc.Col(
                        loading_graph("chart-status-bar", title="Distribución por Estatus"),
                        xs=12, md=5, className="mb-3",
                    ),
                    dbc.Col(
                        loading_graph("chart-stage-status", title="Estatus por Etapa"),
                        xs=12, md=7, className="mb-3",
                    ),
                ]
            ),
            # Charts row 2 — weight by stage + timeline
            dbc.Row(
                [
                    dbc.Col(
                        loading_graph("chart-weight-stage", title="Peso por Etapa (ton)"),
                        xs=12, md=6, className="mb-3",
                    ),
                    dbc.Col(
                        loading_graph("chart-timeline", title="Entregas por Semana"),
                        xs=12, md=6, className="mb-3",
                    ),
                ]
            ),
            # Data table placeholder
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Detalle Dossieres", className="text-muted fw-semibold mb-2"),
                        html.Div(id="dossier-table"),
                    ]
                ),
                className="shadow-sm",
            ),
        ]
    )
