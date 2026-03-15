"""Plotly figure factories for the starter dashboard."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

# ── shared style constants ───────────────────────────────────────────────────

_STATUS_COLORS: Dict[str, str] = {
    "approved": "#2e8540",
    "pending": "#d99000",
    "in_review": "#2d6fb7",
}

_STATUS_LABELS: Dict[str, str] = {
    "approved": "Approved",
    "pending": "Pending",
    "in_review": "In Review",
}

_STAGE_ORDER = [
    "Stage 1",
    "Stage 2",
    "Stage 3",
    "Stage 4",
    "General Information",
    "Protective Coatings",
]

_FAMILY_ORDER = ["PRO", "SUE", "SHARED"]


def _classify_status(series: pd.Series) -> pd.Series:
    """Map raw estatus values to the canonical three-way classification."""
    _APPROVED = {"approved", "liberado", "aprobado", "aceptado"}
    _IN_REVIEW = {"in_review", "in review", "en_revisión", "en revisión",
                  "revisión inpros", "en revision inpros", "en_revision_inpros"}

    def _map(v: str) -> str:
        v = str(v).strip().lower().replace("_", " ")
        if v in _APPROVED:
            return "approved"
        if v in _IN_REVIEW:
            return "in_review"
        return "pending"

    return series.fillna("pending").astype(str).apply(_map)


def _normalize_bloque(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.upper()


def derive_stage_category(df: pd.DataFrame) -> pd.Series:
    """Return business stage labels, replacing old Stage 0 cases explicitly."""
    bloque = _normalize_bloque(df.get("bloque", pd.Series(index=df.index, dtype=object)))
    etapa_num = pd.to_numeric(df.get("etapa", pd.Series(index=df.index, dtype=object)), errors="coerce")

    stage = pd.Series("", index=df.index, dtype="object")

    # Deterministic remap for cross-building dossier groups.
    stage.loc[bloque.eq("DOSSIER GENERAL") | bloque.str.contains("GENERAL", na=False)] = "General Information"
    stage.loc[bloque.eq("DOSSIER PINTURA") | bloque.str.contains("PINTURA|COAT|PAINT", na=False)] = "Protective Coatings"

    numeric_mask = etapa_num.notna() & stage.eq("")
    stage.loc[numeric_mask] = "Stage " + etapa_num.loc[numeric_mask].astype(int).astype(str)

    return stage


def derive_building_family(df: pd.DataFrame) -> pd.Series:
    """Return PRO/SUE/SHARED family values, never exposing DOSSIER."""
    bloque = _normalize_bloque(df.get("bloque", pd.Series(index=df.index, dtype=object)))

    family = pd.Series("SHARED", index=df.index, dtype="object")
    family.loc[bloque.str.startswith("PRO")] = "PRO"
    family.loc[bloque.str.startswith("SUE")] = "SUE"
    family.loc[bloque.str.startswith("DOSSIER")] = "SHARED"
    return family


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
        return empty_figure("Contractor delivery progress", "No data available")

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
        return empty_figure("Welding inspection metrics", "No welding data available")

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


# ── new dataset-driven figures ────────────────────────────────────────────────

def status_by_stage_figure(df: pd.DataFrame) -> go.Figure:
    """Stacked bar: dossier counts by business stage / dossier type."""
    if df.empty or "etapa" not in df.columns or "estatus" not in df.columns:
        return empty_figure("Status by stage / dossier type", "No data available")

    work = df.copy()
    work["status"] = _classify_status(work["estatus"])
    work["stage_category"] = derive_stage_category(work)
    work = work[work["stage_category"].isin(_STAGE_ORDER)]

    grouped = (
        work.groupby(["stage_category", "status"])
        .size()
        .unstack(fill_value=0)
    )
    for s in ("approved", "pending", "in_review"):
        if s not in grouped.columns:
            grouped[s] = 0
    grouped = grouped.reindex(_STAGE_ORDER, fill_value=0)

    fig = go.Figure()
    for status in ("approved", "pending", "in_review"):
        fig.add_trace(
            go.Bar(
                name=_STATUS_LABELS[status],
                x=grouped.index.tolist(),
                y=grouped[status],
                marker_color=_STATUS_COLORS[status],
                text=grouped[status].where(grouped[status] > 0).astype("Int64").astype(str).replace("<NA>", ""),
                textposition="inside",
            )
        )
    fig.update_layout(
        template="plotly_white",
        barmode="stack",
        title="Status by stage / dossier type",
        xaxis_title="Stage / Dossier Type",
        yaxis_title="Dossiers",
        legend_title="Status",
        margin={"l": 12, "r": 12, "t": 64, "b": 26},
        title_x=0.01,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    return fig


def status_by_block_figure(df: pd.DataFrame) -> go.Figure:
    """Stacked bar: dossier counts by building family (PRO / SUE / SHARED)."""
    if df.empty or "bloque" not in df.columns or "estatus" not in df.columns:
        return empty_figure("Status by building family", "No data available")

    work = df.copy()
    work["status"] = _classify_status(work["estatus"])
    work["family"] = derive_building_family(work)

    grouped = (
        work.groupby(["family", "status"])
        .size()
        .unstack(fill_value=0)
    )
    for s in ("approved", "pending", "in_review"):
        if s not in grouped.columns:
            grouped[s] = 0
    grouped = grouped.reindex(_FAMILY_ORDER, fill_value=0)

    fig = go.Figure()
    for status in ("approved", "pending", "in_review"):
        fig.add_trace(
            go.Bar(
                name=_STATUS_LABELS[status],
                x=grouped.index.tolist(),
                y=grouped[status],
                marker_color=_STATUS_COLORS[status],
                text=grouped[status].where(grouped[status] > 0).astype("Int64").astype(str).replace("<NA>", ""),
                textposition="inside",
            )
        )
    fig.update_layout(
        template="plotly_white",
        barmode="stack",
        title="Status by building family",
        xaxis_title="Building Family",
        yaxis_title="Dossiers",
        legend_title="Status",
        margin={"l": 12, "r": 12, "t": 64, "b": 26},
        title_x=0.01,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    return fig


def weekly_progress_figure(df: pd.DataFrame) -> go.Figure:
    """Grouped bar: dossier status counts per target delivery week (hito_semana)."""
    if df.empty or "hito_semana" not in df.columns or "estatus" not in df.columns:
        return empty_figure("Weekly delivery status", "No data available")

    work = df.copy()
    work["status"] = _classify_status(work["estatus"])
    work["semana_num"] = pd.to_numeric(work["hito_semana"], errors="coerce")
    work = work.dropna(subset=["semana_num"])
    work["semana_label"] = "S" + work["semana_num"].astype(int).astype(str)

    grouped = (
        work.groupby(["semana_label", "status"])
        .size()
        .unstack(fill_value=0)
    )
    for s in ("approved", "pending", "in_review"):
        if s not in grouped.columns:
            grouped[s] = 0
    # Sort chronologically by the numeric part of the label.
    grouped = grouped.loc[sorted(grouped.index, key=lambda x: int(x[1:]))]

    fig = go.Figure()
    for status in ("approved", "pending", "in_review"):
        fig.add_trace(
            go.Bar(
                name=_STATUS_LABELS[status],
                x=grouped.index.astype(str),
                y=grouped[status],
                marker_color=_STATUS_COLORS[status],
                text=grouped[status].where(grouped[status] > 0).astype("Int64").astype(str).replace("<NA>", ""),
                textposition="inside",
            )
        )
    fig.update_layout(
        template="plotly_white",
        barmode="group",
        title="Weekly delivery status",
        xaxis_title="Target Week",
        yaxis_title="Dossiers",
        legend_title="Status",
        margin={"l": 12, "r": 12, "t": 64, "b": 56},
        title_x=0.01,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
        xaxis_tickangle=-45,
    )
    return fig


def weekly_accumulated_progress_figure(df: pd.DataFrame) -> go.Figure:
    """Mini S-curve for cumulative released progress vs cumulative total."""
    if df.empty or "hito_semana" not in df.columns or "estatus" not in df.columns:
        return empty_figure("Cumulative weekly progress", "No data available")

    work = df.copy()
    work["status"] = _classify_status(work["estatus"])
    work["semana_num"] = pd.to_numeric(work["hito_semana"], errors="coerce")
    work = work.dropna(subset=["semana_num"])
    if work.empty:
        return empty_figure("Cumulative weekly progress", "No valid week data")

    grouped = (
        work.groupby("semana_num")
        .agg(
            total=("estatus", "size"),
            approved=("status", lambda s: int((s == "approved").sum())),
        )
        .sort_index()
    )
    grouped["cum_total"] = grouped["total"].cumsum()
    grouped["cum_approved"] = grouped["approved"].cumsum()

    final_total = max(int(grouped["cum_total"].iloc[-1]), 1)
    grouped["cum_total_pct"] = grouped["cum_total"] / final_total * 100.0
    grouped["cum_approved_pct"] = grouped["cum_approved"] / final_total * 100.0
    weeks = [f"W{int(v)}" for v in grouped.index]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            name="Cumulative total",
            x=weeks,
            y=grouped["cum_total_pct"],
            mode="lines+markers",
            line={"width": 2, "color": "#7a7a7a"},
            marker={"size": 6},
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Cumulative approved",
            x=weeks,
            y=grouped["cum_approved_pct"],
            mode="lines+markers",
            line={"width": 3, "color": _STATUS_COLORS["approved"]},
            marker={"size": 7},
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Cumulative weekly progress",
        xaxis_title="Target Week",
        yaxis_title="Cumulative progress (%)",
        yaxis_range=[0, 105],
        margin={"l": 12, "r": 12, "t": 64, "b": 40},
        legend_title="Series",
        title_x=0.01,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    return fig
