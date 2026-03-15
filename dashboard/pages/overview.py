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
                                html.H2("QA Platform Dashboard", className="mb-1"),
                                html.Div(
                                    "Executive overview, contractor performance, and quality KPIs from FastAPI.",
                                    className="qa-subtitle",
                                ),
                            ]
                        ),
                        className="qa-panel mb-3",
                    )
                )
            ),
            dbc.Row(
                [
                    _filter_dropdown("Contractor", "filter-contractor"),
                    _filter_dropdown("Discipline", "filter-discipline"),
                    _filter_dropdown("System", "filter-system"),
                    _filter_dropdown("Week", "filter-week"),
                ],
                className="mb-2",
            ),
            html.H5("Executive Overview", className="mt-1"),
            html.Div(id="executive-kpis", className="mb-3"),
            html.H5("Contractor Performance"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="progress-graph", config={"displaylogo": False})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=7,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(dcc.Graph(id="welding-graph", config={"displaylogo": False})),
                            className="qa-panel h-100",
                        ),
                        xs=12,
                        lg=5,
                        className="mb-3",
                    ),
                ]
            ),
            html.H5("Quality KPIs"),
            html.Div(id="quality-kpis", className="mb-2"),
        ],
    )
