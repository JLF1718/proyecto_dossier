"""Plotly figure factories for the starter dashboard."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go


def empty_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 14},
            }
        ],
    )
    return fig


def progress_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "CONTRATISTA" not in df.columns or "ESTATUS" not in df.columns:
        return empty_figure("Contractor delivery progress", "No hay datos para graficar")

    work = df.copy()
    work["APPROVED"] = work["ESTATUS"].astype(str).str.upper().isin(["LIBERADO", "APROBADO", "ACEPTADO"])

    grouped = work.groupby("CONTRATISTA", dropna=True).agg(
        total=("ESTATUS", "count"),
        approved=("APPROVED", "sum"),
    )
    grouped["progress_pct"] = grouped["approved"] / grouped["total"] * 100
    grouped = grouped.sort_values("progress_pct", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=grouped["progress_pct"],
            y=grouped.index.astype(str),
            orientation="h",
            marker={
                "color": grouped["progress_pct"],
                "colorscale": [[0.0, "#f3a712"], [1.0, "#0f7c3f"]],
            },
            text=[f"{v:.1f}%" for v in grouped["progress_pct"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Contractor delivery progress",
        xaxis_title="Approved dossiers (%)",
        yaxis_title="Contractor",
        margin={"l": 10, "r": 30, "t": 60, "b": 20},
    )
    return fig


def welding_figure(metrics: Dict[str, Any]) -> go.Figure:
    if not metrics:
        return empty_figure("Welding inspection metrics", "Sin data de soldadura")

    accepted = int(metrics.get("accepted", 0))
    rejected = int(metrics.get("rejected", 0))
    pending = int(metrics.get("pending", 0))

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Accepted", "Rejected", "Pending"],
                values=[accepted, rejected, pending],
                hole=0.55,
                marker={"colors": ["#0f7c3f", "#b83227", "#f3a712"]},
                sort=False,
            )
        ]
    )
    fig.update_layout(
        template="plotly_white",
        title="Welding inspection metrics",
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        showlegend=True,
    )
    return fig
