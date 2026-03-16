"""Overview page for QA dashboard."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def _filter_dropdown(label: str, dropdown_id: str) -> dbc.Col:
    return dbc.Col(
        [
            html.Label(label, className="qa-subtitle fw-semibold mb-1"),
            dcc.Dropdown(
                id=dropdown_id,
                options=[],
                placeholder=f"All {label.lower()}",
                clearable=True,
            ),
        ],
        xs=12,
        md=6,
        lg=3,
        className="mb-2",
    )


def overview_page() -> dbc.Container:
    return dbc.Container(
        fluid=True,
        children=[
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div("INPROS QA PLATFORM", className="qa-hero-kicker mb-1"),
                                html.H2("Executive QA Dossier Control Board", className="qa-page-title mb-1"),
                                html.Div("BAYSA Dossier Monitoring", className="qa-hero-subtitle"),
                            ]
                        ),
                        className="qa-panel qa-hero mb-3",
                    )
                )
            ),
            dbc.Row(
                [
                    _filter_dropdown("Contractor", "filter-contractor"),
                    _filter_dropdown("Stage / Dossier Type", "filter-discipline"),
                    _filter_dropdown("Building Family", "filter-system"),
                    _filter_dropdown("Week", "filter-week"),
                ],
                className="mb-3 qa-filter-row",
            ),
            html.H5("Executive Overview", className="qa-section-title mt-1 mb-2"),
            html.Div(id="executive-kpis", className="mb-4 qa-kpi-zone"),
            html.H5("Weekly Management", className="qa-section-title mt-1 mb-2"),
            html.Div(id="weekly-management-kpis", className="mb-3 qa-kpi-zone"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="weekly-release-count-graph", config={"displaylogo": False}, style={"height": "340px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=6,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="weekly-release-weight-graph", config={"displaylogo": False}, style={"height": "340px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=6,
                        className="mb-3",
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="cumulative-approved-growth-graph", config={"displaylogo": False}, style={"height": "340px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=6,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="cumulative-release-weight-graph", config={"displaylogo": False}, style={"height": "340px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=6,
                        className="mb-3",
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(html.Div(id="backlog-aging-summary", className="mb-3"), xs=12, lg=6),
                    dbc.Col(html.Div(id="stagnant-groups-summary", className="mb-3"), xs=12, lg=6),
                ]
            ),
            html.H5("Dossier Analysis", className="qa-section-title mt-1 mb-2"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="weekly-progress-graph", config={"displaylogo": False}, style={"height": "430px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=7,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="weekly-accum-graph", config={"displaylogo": False}, style={"height": "430px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=5,
                        className="mb-3",
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="stage-status-graph", config={"displaylogo": False}, style={"height": "350px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=7,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="block-status-graph", config={"displaylogo": False}, style={"height": "350px"})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=5,
                        className="mb-3",
                    ),
                ]
            ),
            html.H5("Executive Summary by Business Group", className="qa-section-title mt-2 mb-2"),
            html.Div(id="executive-summary-table", className="mb-4"),
            html.H5("Secondary Quality Signals", className="qa-section-title qa-section-title-muted mt-2 mb-1"),
            html.Div(id="quality-kpis", className="mb-1 qa-secondary-kpis"),
        ],
    )
