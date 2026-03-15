"""
Dashboard Components — Reusable Chart Wrappers
===============================================
Wraps module-level figure factories in dcc.Graph components
with consistent config and styling.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html
import plotly.graph_objects as go

# Default Plotly config for interactive charts
_GRAPH_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToAdd": ["toImage"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "qa_chart",
        "height": 900,
        "width": 1600,
        "scale": 2,
    },
}


def graph(
    fig: go.Figure,
    graph_id: str,
    title: Optional[str] = None,
    className: str = "",
) -> dbc.Card:
    """Wrap a Plotly figure in a Card with an optional title."""
    body_children = []
    if title:
        body_children.append(html.H6(title, className="text-muted fw-semibold mb-2"))
    body_children.append(
        dcc.Graph(
            id=graph_id,
            figure=fig,
            config=_GRAPH_CONFIG,
            className="qa-chart",
        )
    )
    return dbc.Card(
        dbc.CardBody(body_children),
        className=f"shadow-sm {className}",
    )


def loading_graph(graph_id: str, title: Optional[str] = None) -> dbc.Card:
    """Placeholder card with a dcc.Graph that will be populated by a callback."""
    body_children = []
    if title:
        body_children.append(html.H6(title, className="text-muted fw-semibold mb-2"))
    body_children.append(
        dcc.Loading(
            dcc.Graph(id=graph_id, config=_GRAPH_CONFIG, className="qa-chart"),
            type="circle",
            color="#0F7C3F",
        )
    )
    return dbc.Card(
        dbc.CardBody(body_children),
        className="shadow-sm",
    )
