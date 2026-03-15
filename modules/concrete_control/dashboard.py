"""
Concrete Control — Dashboard Figures
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def make_resistance_scatter(df: pd.DataFrame) -> go.Figure:
    """Scatter: 28-day resistance vs design resistance."""
    if df.empty or not {"RESISTENCIA_28D_MPA", "RESISTENCIA_DISENIO_MPA"}.issubset(df.columns):
        return _empty()

    label = df["ELEMENTO"] if "ELEMENTO" in df.columns else None

    fig = go.Figure(
        go.Scatter(
            x=pd.to_numeric(df["RESISTENCIA_DISENIO_MPA"], errors="coerce"),
            y=pd.to_numeric(df["RESISTENCIA_28D_MPA"], errors="coerce"),
            mode="markers",
            text=label,
            marker=dict(color="#0F7C3F", size=8, opacity=0.7),
        )
    )
    # Reference line y=x
    max_val = max(
        pd.to_numeric(df["RESISTENCIA_DISENIO_MPA"], errors="coerce").max(),
        pd.to_numeric(df["RESISTENCIA_28D_MPA"], errors="coerce").max(),
    )
    fig.add_trace(
        go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines",
            name="f'c Diseño",
            line=dict(color="#D0021B", dash="dash"),
        )
    )
    fig.update_layout(
        title="Resistencia Real vs Resistencia de Diseño (28 días)",
        xaxis_title="f'c Diseño (MPa)",
        yaxis_title="f'c Real 28d (MPa)",
        height=380,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    return fig


def _empty() -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="Sin datos", xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#AAAAAA"),
    )
    fig.update_layout(height=350, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
    return fig
