"""
NC Management — Dashboard Figures
====================================
"""

from __future__ import annotations

from typing import Any, Dict

import plotly.graph_objects as go

_COLORS = {
    "ABIERTA": "#D0021B",
    "EN_PROCESO": "#F5A623",
    "CERRADA": "#0F7C3F",
}


def make_nc_status_bar(metrics: Dict[str, Any]) -> go.Figure:
    categories = ["Abiertas", "En Proceso", "Cerradas"]
    values = [metrics.get("open", 0), metrics.get("in_progress", 0), metrics.get("closed", 0)]
    colors = [_COLORS["ABIERTA"], _COLORS["EN_PROCESO"], _COLORS["CERRADA"]]

    fig = go.Figure(
        go.Bar(
            x=categories, y=values,
            marker_color=colors,
            text=values, textposition="outside",
        )
    )
    fig.update_layout(
        title="Estado de No Conformidades",
        yaxis_title="Cantidad",
        height=320,
        margin=dict(l=60, r=40, t=50, b=50),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    return fig


def make_nc_by_discipline_bar(metrics: Dict[str, Any]) -> go.Figure:
    by_disc = metrics.get("by_discipline", {})
    if not by_disc:
        return _empty("Sin datos por disciplina")

    fig = go.Figure(
        go.Bar(
            x=list(by_disc.keys()),
            y=list(by_disc.values()),
            marker_color="#0F7C3F",
            text=list(by_disc.values()),
            textposition="outside",
        )
    )
    fig.update_layout(
        title="NCs por Disciplina",
        yaxis_title="Cantidad",
        height=320,
        margin=dict(l=60, r=40, t=50, b=60),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    return fig


def _empty(message: str = "Sin datos") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#AAAAAA"),
    )
    fig.update_layout(height=300, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
    return fig
