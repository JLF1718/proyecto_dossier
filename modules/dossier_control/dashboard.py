"""
Dossier Control — Dashboard Figures
=====================================
Plotly figure factories for the Dossier Control module.
These functions return ``go.Figure`` objects consumed by Dash callbacks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics.data_processing import pivot_status_by_stage, pivot_weight_by_stage

# ── Colour palette (mirrors config.yaml) ────────────────────────────────────

COLORS: Dict[str, str] = {
    "LIBERADO": "#0F7C3F",
    "EN_REVISIÓN": "#F5A623",
    "OBSERVADO": "#D0021B",
    "PLANEADO": "#808080",
}

STATUS_ORDER = ["LIBERADO", "EN_REVISIÓN", "OBSERVADO", "PLANEADO"]


# ── KPI indicator strip ───────────────────────────────────────────────────────

def make_kpi_indicators(kpis: Dict[str, Any]) -> go.Figure:
    """Return a row of 3 indicator gauges for the main KPIs."""
    fig = go.Figure()

    indicators = [
        ("Dossieres Liberados", kpis.get("dossiers_liberados", 0), kpis.get("total_dossiers", 0), ""),
        ("% Liberado (unidades)", kpis.get("pct_liberado", 0), 100, "%"),
        ("% Peso Liberado (ton)", kpis.get("pct_peso_liberado", 0), 100, "%"),
    ]

    for i, (title, value, reference, suffix) in enumerate(indicators):
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=value,
                number={"suffix": suffix, "font": {"size": 36}},
                title={"text": title, "font": {"size": 14}},
                delta={"reference": reference, "relative": False},
                domain={"x": [i / 3, (i + 1) / 3], "y": [0, 1]},
            )
        )

    fig.update_layout(
        height=160,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="#FFFFFF",
    )
    return fig


# ── Status distribution bar chart ─────────────────────────────────────────────

def make_status_bar(df: pd.DataFrame, title: str = "Estado Dossieres") -> go.Figure:
    """Horizontal bar chart of dossier counts by ESTATUS."""
    if df.empty or "ESTATUS" not in df.columns:
        return _empty_figure("Sin datos")

    counts = df["ESTATUS"].value_counts()
    statuses = [s for s in STATUS_ORDER if s in counts.index]
    values = [counts[s] for s in statuses]
    colors = [COLORS.get(s, "#AAAAAA") for s in statuses]

    fig = go.Figure(
        go.Bar(
            y=statuses,
            x=values,
            orientation="h",
            marker_color=colors,
            text=values,
            textposition="outside",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Cantidad",
        height=300,
        margin=dict(l=120, r=40, t=50, b=40),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis=dict(gridcolor="#E5E5E5"),
    )
    return fig


# ── Stage × Status grouped bar ────────────────────────────────────────────────

def make_stage_status_bar(df: pd.DataFrame, mode: str = "count") -> go.Figure:
    """
    Grouped bar chart: each group is a construction stage (ETAPA),
    each bar is a status.

    Args:
        df: Dossier DataFrame.
        mode: 'count' for dossier counts, 'weight' for tonnes.
    """
    if df.empty:
        return _empty_figure("Sin datos")

    if mode == "weight":
        pivot = pivot_weight_by_stage(df)
        if pivot.empty:
            return _empty_figure("Sin datos de peso")
        value_col = "PESO_TON"
        y_label = "Peso (ton)"
    else:
        pivot = pivot_status_by_stage(df)
        if pivot.empty:
            return _empty_figure("Sin datos")
        value_col = None  # columns are the statuses
        y_label = "Cantidad"

    fig = go.Figure()

    if mode == "count":
        for status in STATUS_ORDER:
            if status not in pivot.columns:
                continue
            fig.add_trace(
                go.Bar(
                    name=status,
                    x=pivot["ETAPA"],
                    y=pivot[status],
                    marker_color=COLORS.get(status, "#AAAAAA"),
                    text=pivot[status],
                    textposition="auto",
                )
            )
    else:
        for status in STATUS_ORDER:
            sub = pivot[pivot["ESTATUS"] == status]
            if sub.empty:
                continue
            fig.add_trace(
                go.Bar(
                    name=status,
                    x=sub["ETAPA"],
                    y=sub["PESO_TON"].round(1),
                    marker_color=COLORS.get(status, "#AAAAAA"),
                )
            )

    fig.update_layout(
        barmode="group",
        xaxis_title="Etapa",
        yaxis_title=y_label,
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=40, t=60, b=60),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        yaxis=dict(gridcolor="#E5E5E5"),
    )
    return fig


# ── Delivery timeline ─────────────────────────────────────────────────────────

def make_timeline(timeline_df: pd.DataFrame) -> go.Figure:
    """Line chart of released dossiers per delivery week."""
    if timeline_df.empty:
        return _empty_figure("Sin datos de entregas")

    fig = go.Figure()

    if "CONTRATISTA" in timeline_df.columns:
        for contr in timeline_df["CONTRATISTA"].unique():
            sub = timeline_df[timeline_df["CONTRATISTA"] == contr]
            fig.add_trace(
                go.Scatter(
                    x=sub["ENTREGA"],
                    y=sub["peso_ton"],
                    mode="lines+markers",
                    name=contr,
                    line=dict(width=2),
                )
            )
    else:
        fig.add_trace(
            go.Scatter(
                x=timeline_df["ENTREGA"],
                y=timeline_df["peso_ton"],
                mode="lines+markers",
                name="Liberado",
                line=dict(color=COLORS["LIBERADO"], width=2),
            )
        )

    fig.update_layout(
        title="Peso Liberado por Semana de Entrega",
        xaxis_title="Semana",
        yaxis_title="Peso (ton)",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=40, t=60, b=60),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        yaxis=dict(gridcolor="#E5E5E5"),
    )
    return fig


# ── helpers ──────────────────────────────────────────────────────────────────

def _empty_figure(message: str = "Sin datos") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=18, color="#AAAAAA"),
    )
    fig.update_layout(
        height=300,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    return fig
