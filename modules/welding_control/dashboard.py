"""
Welding Control — Dashboard Figures
=====================================
Plotly figure factories for the Welding Control module.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

_COLORS = {
    "ACEPTADO": "#0F7C3F",
    "RECHAZADO": "#D0021B",
    "PENDIENTE": "#808080",
}


def make_acceptance_pie(metrics: Dict[str, Any]) -> go.Figure:
    """Pie chart: accepted vs rejected joints."""
    labels = ["Aceptado", "Rechazado", "Pendiente"]
    values = [
        metrics.get("accepted", 0),
        metrics.get("rejected", 0),
        metrics.get("pending", 0),
    ]
    colors = [_COLORS["ACEPTADO"], _COLORS["RECHAZADO"], _COLORS["PENDIENTE"]]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            hole=0.4,
            textinfo="label+percent+value",
        )
    )
    fig.update_layout(
        title="Resultados Inspección Soldadura",
        height=350,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor="#FFFFFF",
    )
    return fig


def make_process_bar(df: pd.DataFrame) -> go.Figure:
    """Bar chart of weld counts grouped by welding process."""
    if df.empty or "PROCESO" not in df.columns:
        return _empty_figure("Sin datos de proceso")

    counts = df["PROCESO"].value_counts().reset_index()
    counts.columns = ["PROCESO", "COUNT"]

    fig = go.Figure(
        go.Bar(
            x=counts["PROCESO"],
            y=counts["COUNT"],
            marker_color="#0F7C3F",
            text=counts["COUNT"],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Juntas por Proceso de Soldadura",
        xaxis_title="Proceso",
        yaxis_title="Cantidad",
        height=320,
        margin=dict(l=60, r=40, t=50, b=60),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    return fig


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#AAAAAA"),
    )
    fig.update_layout(height=300, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
    return fig
