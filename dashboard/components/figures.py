"""Plotly figure factories for the starter dashboard."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

from dashboard.i18n import stage_label, t

# ── shared style constants ───────────────────────────────────────────────────

_STATUS_COLORS: Dict[str, str] = {
    "approved": "#2e8540",
    "pending": "#d99000",
    "in_review": "#2d6fb7",
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


def executive_summary_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize dossier counts and released weight by family and stage."""
    columns = [
        "building_family",
        "stage_category",
        "total_dossiers",
        "approved",
        "pending",
        "in_review",
        "approval_pct",
        "released_weight_t",
        "out_of_scope",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    work = df.copy()
    work["status"] = _classify_status(work.get("estatus", pd.Series(index=work.index, dtype=object)))
    work["stage_category"] = derive_stage_category(work)
    work["building_family"] = derive_building_family(work)
    work = work[
        work["stage_category"].isin(_STAGE_ORDER)
        & work["building_family"].isin(_FAMILY_ORDER)
    ].copy()
    if work.empty:
        return pd.DataFrame(columns=columns)

    in_scope = work.get("in_contract_scope", pd.Series(True, index=work.index)).astype(str).str.lower().isin(["true", "1", "yes"])
    weight_t = pd.to_numeric(work.get("peso_dossier_kg", 0), errors="coerce").fillna(0.0) / 1000.0

    work["total_dossiers"] = in_scope.astype(int)
    work["approved"] = (in_scope & work["status"].eq("approved")).astype(int)
    work["pending"] = (in_scope & work["status"].eq("pending")).astype(int)
    work["in_review"] = (in_scope & work["status"].eq("in_review")).astype(int)
    work["released_weight_t"] = weight_t.where(in_scope & work["status"].eq("approved"), 0.0)
    work["out_of_scope"] = (~in_scope).astype(int)

    work["building_family"] = pd.Categorical(work["building_family"], categories=_FAMILY_ORDER, ordered=True)
    work["stage_category"] = pd.Categorical(work["stage_category"], categories=_STAGE_ORDER, ordered=True)

    summary = (
        work.groupby(["building_family", "stage_category"], observed=True)
        .agg(
            total_dossiers=("total_dossiers", "sum"),
            approved=("approved", "sum"),
            pending=("pending", "sum"),
            in_review=("in_review", "sum"),
            released_weight_t=("released_weight_t", "sum"),
            out_of_scope=("out_of_scope", "sum"),
        )
        .reset_index()
    )
    summary["approval_pct"] = summary["approved"].div(summary["total_dossiers"].where(summary["total_dossiers"] > 0)).fillna(0.0) * 100.0

    return summary[columns]


def _status_label(lang: str, status: str) -> str:
    return t(lang, f"status.{status}")


def _stacked_bar_layout(title_text: str, legend_title: str) -> Dict[str, Any]:
    """Shared layout for stacked bar charts with safe title/legend spacing."""
    return {
        "template": "plotly_white",
        "barmode": "stack",
        "title": {
            "text": title_text,
            "x": 0.01,
            "y": 0.97,
            "yanchor": "top",
        },
        "legend_title": legend_title,
        "margin": {"l": 12, "r": 12, "t": 92, "b": 26},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0.0,
        },
        # Keep chart responsive in the Dash grid; PNG size is controlled by toImage config.
        "autosize": True,
    }


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


def _weekly_payload_frame(payload: Dict[str, Any], key: str) -> pd.DataFrame:
    comparison = payload.get("weekly_comparison", {}) if payload else {}
    records = comparison.get(key, [])
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def _week_labels(series: pd.Series) -> list[str]:
    return [f"W{int(value)}" for value in series.tolist()]


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

def status_by_stage_figure(df: pd.DataFrame, lang: str = "en") -> go.Figure:
    """Stacked bar: dossier counts by business stage / dossier type."""
    if df.empty or "etapa" not in df.columns or "estatus" not in df.columns:
        return empty_figure(t(lang, "figure.status_by_stage.title"), t(lang, "figure.no_data"))

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
    stage_labels = [stage_label(stage, lang) for stage in grouped.index.tolist()]

    fig = go.Figure()
    for status in ("approved", "pending", "in_review"):
        fig.add_trace(
            go.Bar(
                name=_status_label(lang, status),
                x=stage_labels,
                y=grouped[status],
                marker_color=_STATUS_COLORS[status],
                text=grouped[status].where(grouped[status] > 0).astype("Int64").astype(str).replace("<NA>", ""),
                textposition="inside",
            )
        )
    fig.update_layout(
        **_stacked_bar_layout(
            title_text=t(lang, "figure.status_by_stage.title"),
            legend_title=t(lang, "figure.status_by_stage.legend"),
        ),
        xaxis_title=t(lang, "figure.status_by_stage.x"),
        yaxis_title=t(lang, "figure.status_by_stage.y"),
    )
    return fig


def status_by_block_figure(df: pd.DataFrame, lang: str = "en") -> go.Figure:
    """Stacked bar: dossier counts by building family (PRO / SUE / SHARED)."""
    if df.empty or "bloque" not in df.columns or "estatus" not in df.columns:
        return empty_figure(t(lang, "figure.status_by_family.title"), t(lang, "figure.no_data"))

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
                name=_status_label(lang, status),
                x=grouped.index.tolist(),
                y=grouped[status],
                marker_color=_STATUS_COLORS[status],
                text=grouped[status].where(grouped[status] > 0).astype("Int64").astype(str).replace("<NA>", ""),
                textposition="inside",
            )
        )
    fig.update_layout(
        **_stacked_bar_layout(
            title_text=t(lang, "figure.status_by_family.title"),
            legend_title=t(lang, "figure.status_by_family.legend"),
        ),
        xaxis_title=t(lang, "figure.status_by_family.x"),
        yaxis_title=t(lang, "figure.status_by_family.y"),
    )
    return fig


def weekly_progress_figure(df: pd.DataFrame, lang: str = "en") -> go.Figure:
    """Grouped bar: dossier status counts per target delivery week (hito_semana)."""
    if df.empty or "hito_semana" not in df.columns or "estatus" not in df.columns:
        return empty_figure(t(lang, "figure.weekly_status.title"), t(lang, "figure.no_data"))

    work = df.copy()
    work["status"] = _classify_status(work["estatus"])
    work["semana_num"] = pd.to_numeric(work["hito_semana"], errors="coerce")
    work = work.dropna(subset=["semana_num"])
    work["semana_label"] = "W" + work["semana_num"].astype(int).astype(str)

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
                name=_status_label(lang, status),
                x=grouped.index.astype(str),
                y=grouped[status],
                marker_color=_STATUS_COLORS[status],
                text=grouped[status].where(grouped[status] > 0).astype("Int64").astype(str).replace("<NA>", ""),
                textposition="auto",
                insidetextfont={"size": 12, "color": "#ffffff"},
                outsidetextfont={"size": 12, "color": "#1f2937"},
                cliponaxis=False,
            )
        )
    fig.update_layout(
        template="plotly_white",
        barmode="group",
        title={
            "text": t(lang, "figure.weekly_status.title"),
            "x": 0.01,
            "y": 0.97,
            "yanchor": "top",
        },
        xaxis_title=t(lang, "figure.weekly_status.x"),
        yaxis_title=t(lang, "figure.weekly_status.y"),
        margin={"l": 12, "r": 12, "t": 92, "b": 124},
        legend={"orientation": "h", "yanchor": "top", "y": -0.26, "xanchor": "center", "x": 0.5},
        uniformtext_minsize=11,
        uniformtext_mode="hide",
        xaxis={"tickangle": -45, "tickfont": {"size": 11}},
        yaxis={"tickfont": {"size": 11}},
    )
    return fig


def weekly_accumulated_progress_figure(df: pd.DataFrame, lang: str = "en") -> go.Figure:
    """Mini S-curve for cumulative released progress vs cumulative total."""
    if df.empty or "hito_semana" not in df.columns or "estatus" not in df.columns:
        return empty_figure(t(lang, "figure.weekly_accum.title"), t(lang, "figure.no_data"))

    work = df.copy()
    work["status"] = _classify_status(work["estatus"])
    work["semana_num"] = pd.to_numeric(work["hito_semana"], errors="coerce")
    work = work.dropna(subset=["semana_num"])
    if work.empty:
        return empty_figure(t(lang, "figure.weekly_accum.title"), t(lang, "figure.no_week_data"))

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
            name=t(lang, "figure.series.cum_total"),
            x=weeks,
            y=grouped["cum_total_pct"],
            mode="lines+markers",
            line={"width": 2, "color": "#7a7a7a"},
            marker={"size": 6},
        )
    )
    fig.add_trace(
        go.Scatter(
            name=t(lang, "figure.series.cum_approved"),
            x=weeks,
            y=grouped["cum_approved_pct"],
            mode="lines+markers",
            line={"width": 3, "color": _STATUS_COLORS["approved"]},
            marker={"size": 7},
        )
    )
    fig.update_layout(
        template="plotly_white",
        title={
            "text": t(lang, "figure.weekly_accum.title"),
            "x": 0.01,
            "y": 0.97,
            "yanchor": "top",
        },
        xaxis_title=t(lang, "figure.weekly_accum.x"),
        yaxis_title=t(lang, "figure.weekly_accum.y"),
        yaxis_range=[0, 105],
        margin={"l": 12, "r": 12, "t": 92, "b": 94},
        legend={"orientation": "h", "yanchor": "top", "y": -0.2, "xanchor": "center", "x": 0.5},
        xaxis={"tickfont": {"size": 11}},
        yaxis={"range": [0, 105], "tickfont": {"size": 11}},
    )
    return fig


def weekly_released_dossiers_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    release_series = _weekly_payload_frame(payload, "release_series")
    if release_series.empty:
        return empty_figure(t(lang, "figure.weekly_released_dossiers.title"), t(lang, "figure.no_weekly_release"))

    fig = go.Figure(
        go.Bar(
            x=_week_labels(release_series["week"]),
            y=release_series["released_dossiers"],
            marker_color=_STATUS_COLORS["approved"],
            text=release_series["released_dossiers"].where(release_series["released_dossiers"] > 0).astype("Int64").astype(str).replace("<NA>", ""),
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=t(lang, "figure.weekly_released_dossiers.title"),
        xaxis_title=t(lang, "figure.weekly_released_dossiers.x"),
        yaxis_title=t(lang, "figure.weekly_released_dossiers.y"),
        margin={"l": 12, "r": 12, "t": 64, "b": 48},
        title_x=0.01,
    )
    return fig


def weekly_released_weight_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    release_series = _weekly_payload_frame(payload, "release_series")
    if release_series.empty:
        return empty_figure(t(lang, "figure.weekly_released_weight.title"), t(lang, "figure.no_weekly_release"))

    fig = go.Figure(
        go.Bar(
            x=_week_labels(release_series["week"]),
            y=release_series["released_weight_t"],
            marker_color="#0f6cbd",
            text=release_series["released_weight_t"].apply(lambda value: f"{float(value):.1f}" if float(value) > 0 else ""),
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=t(lang, "figure.weekly_released_weight.title"),
        xaxis_title=t(lang, "figure.weekly_released_weight.x"),
        yaxis_title=t(lang, "figure.weekly_released_weight.y"),
        margin={"l": 12, "r": 12, "t": 64, "b": 48},
        title_x=0.01,
    )
    return fig


def cumulative_approved_growth_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    cumulative_series = _weekly_payload_frame(payload, "cumulative_series")
    if cumulative_series.empty:
        return empty_figure(t(lang, "figure.cum_approved.title"), t(lang, "figure.no_cumulative_release"))

    fig = go.Figure(
        go.Scatter(
            x=_week_labels(cumulative_series["week"]),
            y=cumulative_series["cumulative_approved_dossiers"],
            mode="lines+markers",
            line={"width": 3, "color": _STATUS_COLORS["approved"]},
            marker={"size": 7},
            name=t(lang, "figure.series.cum_approved"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=t(lang, "figure.cum_approved.title"),
        xaxis_title=t(lang, "figure.cum_approved.x"),
        yaxis_title=t(lang, "figure.cum_approved.y"),
        margin={"l": 12, "r": 12, "t": 64, "b": 48},
        title_x=0.01,
    )
    return fig


def cumulative_released_weight_growth_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    cumulative_series = _weekly_payload_frame(payload, "cumulative_series")
    if cumulative_series.empty:
        return empty_figure(t(lang, "figure.cum_weight.title"), t(lang, "figure.no_cumulative_release"))

    fig = go.Figure(
        go.Scatter(
            x=_week_labels(cumulative_series["week"]),
            y=cumulative_series["cumulative_released_weight_t"],
            mode="lines+markers",
            line={"width": 3, "color": "#0f6cbd"},
            marker={"size": 7},
            name=t(lang, "figure.series.cum_weight"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=t(lang, "figure.cum_weight.title"),
        xaxis_title=t(lang, "figure.cum_weight.x"),
        yaxis_title=t(lang, "figure.cum_weight.y"),
        margin={"l": 12, "r": 12, "t": 64, "b": 48},
        title_x=0.01,
    )
    return fig


def _historical_frame(payload: Dict[str, Any]) -> pd.DataFrame:
    records = payload.get("history_series", []) if payload else []
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records).sort_values("analysis_week").reset_index(drop=True)
    if "source" not in frame.columns:
        frame["source"] = "snapshot"
    return frame


def _historical_trend_figure(
    payload: Dict[str, Any],
    *,
    metric: str,
    title_key: str,
    x_key: str,
    y_key: str,
    color: str,
    lang: str = "en",
) -> go.Figure:
    history = _historical_frame(payload)
    if history.empty or metric not in history.columns:
        return empty_figure(t(lang, title_key), t(lang, "figure.no_data"))

    x_values = [f"W{int(value)}" for value in history["analysis_week"]]
    marker_symbols = ["diamond" if source == "live" else "circle" for source in history["source"]]
    hover = [
        f"W{int(week)}<br>{t(lang, 'figure.series.snapshot_live') if source == 'live' else 'Snapshot'}"
        for week, source in zip(history["analysis_week"], history["source"])
    ]

    fig = go.Figure(
        go.Scatter(
            x=x_values,
            y=history[metric],
            mode="lines+markers",
            line={"width": 3, "color": color},
            marker={"size": 8, "symbol": marker_symbols, "color": color},
            hovertext=hover,
            hovertemplate="%{hovertext}<br>%{y}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=t(lang, title_key),
        xaxis_title=t(lang, x_key),
        yaxis_title=t(lang, y_key),
        margin={"l": 12, "r": 12, "t": 64, "b": 48},
        title_x=0.01,
    )
    return fig


def snapshot_released_trend_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    return _historical_trend_figure(
        payload,
        metric="released_this_week",
        title_key="figure.snapshot_released.title",
        x_key="figure.snapshot_released.x",
        y_key="figure.snapshot_released.y",
        color=_STATUS_COLORS["approved"],
        lang=lang,
    )


def snapshot_backlog_trend_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    return _historical_trend_figure(
        payload,
        metric="backlog_dossiers",
        title_key="figure.snapshot_backlog.title",
        x_key="figure.snapshot_backlog.x",
        y_key="figure.snapshot_backlog.y",
        color="#d99000",
        lang=lang,
    )


def snapshot_approval_trend_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    return _historical_trend_figure(
        payload,
        metric="approved_dossiers",
        title_key="figure.snapshot_approval.title",
        x_key="figure.snapshot_approval.x",
        y_key="figure.snapshot_approval.y",
        color="#2d6fb7",
        lang=lang,
    )


def snapshot_released_weight_trend_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    return _historical_trend_figure(
        payload,
        metric="released_weight_t_this_week",
        title_key="figure.snapshot_weight.title",
        x_key="figure.snapshot_weight.x",
        y_key="figure.snapshot_weight.y",
        color="#0f6cbd",
        lang=lang,
    )


# ── New Contract milestone figures ───────────────────────────────────────────
# Physical progress data from Excel "Avances Semanales" at Semana 184.
# Week reference: Semana 196 closes Friday April 3, 2026.
# Commitment weeks derived from Excel "Cuadro de Alcances Nuevos":
#   4 abr  → W197 | 18 abr (S2) → W199 | 30 abr → W200 | 23/25 may → W204
_NEW_CONTRACT_BLOCKS: list[Dict[str, Any]] = [
    {"block": "SUE_74", "montaje": 93.7, "soldadura": 84.6, "liberacion": 30.9,
     "commitment_week": 197, "commitment_date": "4 abr",    "in_budget": True},
    {"block": "SUE_75", "montaje": 99.8, "soldadura": 79.2, "liberacion":  5.8,
     "commitment_week": 200, "commitment_date": "30 abr",   "in_budget": True},
    {"block": "SUE_84", "montaje": 78.9, "soldadura": 72.6, "liberacion": 53.7,
     "commitment_week": None, "commitment_date": "—",       "in_budget": False},
    {"block": "SUE_85", "montaje": 80.3, "soldadura": 69.9, "liberacion":  0.0,
     "commitment_week": None, "commitment_date": "—",       "in_budget": False},
    {"block": "SUE_88", "montaje": 96.7, "soldadura": 95.8, "liberacion": 52.6,
     "commitment_week": 197, "commitment_date": "4 abr",    "in_budget": True},
    {"block": "SUE_94", "montaje": 94.5, "soldadura": 63.4, "liberacion": 41.0,
     "commitment_week": 204, "commitment_date": "25 may",   "in_budget": True},
    {"block": "SUE_95", "montaje": 91.3, "soldadura": 59.3, "liberacion": 36.0,
     "commitment_week": 204, "commitment_date": "23 may",   "in_budget": True},
    {"block": "SUE_96", "montaje": 65.5, "soldadura": 32.7, "liberacion":  0.0,
     "commitment_week": 204, "commitment_date": "25 may·S1 / 18 abr·S2", "in_budget": True,
     "milestone2_week": 199, "milestone2_date": "18 abr·S2"},
]


def new_contract_progress_figure(lang: str = "en") -> go.Figure:
    """Stacked horizontal bars: liberación / soldadura gap / montaje gap / pending.

    Shows physical progress at Semana 184 reference for the 8 new-contract SUE Stage-4 blocks.
    Commitment dates are annotated on the right; SUE_84/85 are flagged as outside budget.
    """
    blocks = sorted(_NEW_CONTRACT_BLOCKS, key=lambda d: d["liberacion"])

    names = [d["block"] for d in blocks]
    lib   = [d["liberacion"] for d in blocks]
    sold  = [max(0.0, d["soldadura"] - d["liberacion"]) for d in blocks]
    mont  = [max(0.0, d["montaje"]   - d["soldadura"])  for d in blocks]
    pend  = [max(0.0, 100.0 - d["montaje"])             for d in blocks]

    fig = go.Figure()

    # 1. Liberado (green)
    fig.add_trace(go.Bar(
        name=t(lang, "nc.legend.liberado"),
        y=names, x=lib, orientation="h",
        marker_color="#2e8540",
        text=[f"{v:.1f}%" if v > 5 else "" for v in lib],
        textposition="inside",
        insidetextfont={"color": "#fff", "size": 11},
        hovertemplate="%{y}: %{x:.1f}% liberado<extra></extra>",
    ))
    # 2. Soldado but not released (blue)
    fig.add_trace(go.Bar(
        name=t(lang, "nc.legend.soldado"),
        y=names, x=sold, orientation="h",
        marker_color="#2d6fb7",
        text=[f"{v:.1f}%" if v > 5 else "" for v in sold],
        textposition="inside",
        insidetextfont={"color": "#fff", "size": 11},
        hovertemplate="%{y}: %{x:.1f}% soldado (no liberado)<extra></extra>",
    ))
    # 3. Assembled but not welded (light blue-gray)
    fig.add_trace(go.Bar(
        name=t(lang, "nc.legend.montado"),
        y=names, x=mont, orientation="h",
        marker_color="#9db4c7",
        text=[f"{v:.1f}%" if v > 5 else "" for v in mont],
        textposition="inside",
        insidetextfont={"color": "#333", "size": 11},
        hovertemplate="%{y}: %{x:.1f}% montado (no soldado)<extra></extra>",
    ))
    # 4. Assembly pending (very light gray)
    fig.add_trace(go.Bar(
        name=t(lang, "nc.legend.pendiente"),
        y=names, x=pend, orientation="h",
        marker_color="#e8edf2",
        marker_line={"color": "#c8d4de", "width": 0.5},
        text=[f"{v:.1f}%" if v > 5 else "" for v in pend],
        textposition="inside",
        insidetextfont={"color": "#999", "size": 10},
        hovertemplate="%{y}: %{x:.1f}% pendiente montaje<extra></extra>",
    ))

    # Commitment date annotations (right of 100% bar)
    for d in blocks:
        label = d["commitment_date"]
        color = "#b83227" if not d["in_budget"] else "#0b2a4a"
        suffix = " *" if not d["in_budget"] else ""
        fig.add_annotation(
            x=102, y=d["block"],
            text=f"{label}{suffix}",
            showarrow=False,
            xanchor="left",
            font={"size": 9, "color": color},
        )

    fig.update_layout(
        barmode="stack",
        template="plotly_white",
        title={
            "text": t(lang, "figure.nc_progress.title"),
            "x": 0.01, "y": 0.98, "yanchor": "top",
        },
        xaxis={
            "title": t(lang, "figure.nc_progress.x"),
            "range": [0, 135],
            "ticksuffix": "%",
            "tickvals": [0, 25, 50, 75, 100],
            "showgrid": True, "gridcolor": "#eef3f8",
        },
        yaxis={"title": ""},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0.0,
            "font": {"size": 10},
        },
        margin={"l": 12, "r": 12, "t": 90, "b": 36},
    )
    # Add footnote AFTER update_layout so it appends rather than replaces
    # the commitment-date annotations already added in the loop above.
    fig.add_annotation(
        x=1.0, y=-0.06,
        xref="paper", yref="paper",
        text=t(lang, "figure.nc_progress.note"),
        showarrow=False, xanchor="right",
        font={"size": 9, "color": "#888"},
    )
    return fig


def new_contract_timeline_figure(lang: str = "en") -> go.Figure:
    """Gantt-style timeline for new-contract SUE blocks.

    X axis = project week. Each block shows a bar from Week 196 (current) to the
    commitment week.  Diamond markers flag the commitment milestone; a second
    marker is drawn for SUE_96 S2 (intermediate date). SUE_84 / SUE_85 (outside
    budget) extend to the chart edge with a different style.
    """
    CURRENT_WEEK = 196
    CHART_MIN    = 193
    CHART_MAX    = 208

    # Sort by commitment week ascending (no-date blocks last)
    blocks = sorted(
        _NEW_CONTRACT_BLOCKS,
        key=lambda d: (d["commitment_week"] is None, d["commitment_week"] or 999),
    )

    fig = go.Figure()

    for d in blocks:
        cw = d["commitment_week"] if d["commitment_week"] else CHART_MAX - 1
        bar_color  = "#e8edf2" if not d["in_budget"] else (
            "#c6e6c8" if d["liberacion"] >= 50 else
            "#fde7a0" if d["liberacion"] >= 20 else
            "#f9c8c4"
        )
        border_col = "#aaa" if not d["in_budget"] else "#666"

        # Background bar: span current → commitment
        fig.add_trace(go.Bar(
            y=[d["block"]],
            x=[cw - CURRENT_WEEK],
            base=[CURRENT_WEEK],
            orientation="h",
            marker_color=bar_color,
            marker_line={"color": border_col, "width": 0.8},
            showlegend=False,
            hovertemplate=(
                f"<b>{d['block']}</b><br>"
                f"Liberación: {d['liberacion']:.1f}%  ·  "
                f"Soldadura: {d['soldadura']:.1f}%  ·  "
                f"Montaje: {d['montaje']:.1f}%<br>"
                f"Compromiso: {d['commitment_date']}<extra></extra>"
            ),
        ))

        # Progress fill inside bar: liberacion% of remaining window
        if d["liberacion"] > 0 and d["commitment_week"]:
            window = cw - CURRENT_WEEK
            fill_width = max(0.2, window * d["liberacion"] / 100.0)
            fig.add_trace(go.Bar(
                y=[d["block"]],
                x=[fill_width],
                base=[CURRENT_WEEK],
                orientation="h",
                marker_color="#2e8540",
                marker_opacity=0.55,
                showlegend=False,
                hoverinfo="skip",
            ))

        # Primary commitment diamond
        if d["commitment_week"]:
            fig.add_trace(go.Scatter(
                x=[d["commitment_week"]],
                y=[d["block"]],
                mode="markers+text",
                marker={"symbol": "diamond", "size": 11, "color": "#0b2a4a", "line": {"width": 1, "color": "#fff"}},
                text=[f"S{d['commitment_week']}"],
                textposition="top center",
                textfont={"size": 8, "color": "#0b2a4a"},
                showlegend=False,
                hovertemplate=f"{d['block']}: S{d['commitment_week']} ({d['commitment_date']})<extra></extra>",
            ))

        # Secondary milestone for SUE_96 S2
        if d.get("milestone2_week"):
            fig.add_trace(go.Scatter(
                x=[d["milestone2_week"]],
                y=[d["block"]],
                mode="markers+text",
                marker={"symbol": "diamond-open", "size": 9, "color": "#b83227", "line": {"width": 1.5, "color": "#b83227"}},
                text=[f"S{d['milestone2_week']}·S2"],
                textposition="bottom center",
                textfont={"size": 7, "color": "#b83227"},
                showlegend=False,
                hovertemplate=f"{d['block']} S2: S{d['milestone2_week']} ({d['milestone2_date']})<extra></extra>",
            ))

    # Current week vertical dashed line
    fig.add_shape(
        type="line",
        x0=CURRENT_WEEK, x1=CURRENT_WEEK,
        y0=-0.5, y1=len(blocks) - 0.5,
        line={"color": "#b83227", "width": 2, "dash": "dash"},
    )
    fig.add_annotation(
        x=CURRENT_WEEK, y=len(blocks) - 0.5,
        text=t(lang, "figure.nc_timeline.current_week"),
        showarrow=False, yanchor="bottom",
        font={"size": 9, "color": "#b83227"},
        bgcolor="rgba(255,255,255,0.7)",
    )

    tick_weeks = list(range(CHART_MIN, CHART_MAX + 1))
    fig.update_layout(
        barmode="overlay",
        template="plotly_white",
        title={
            "text": t(lang, "figure.nc_timeline.title"),
            "x": 0.01, "y": 0.98, "yanchor": "top",
        },
        xaxis={
            "title": t(lang, "figure.nc_timeline.x"),
            "range": [CHART_MIN - 0.5, CHART_MAX + 1.5],
            "tickmode": "array",
            "tickvals": tick_weeks,
            "ticktext": [f"S{w}" for w in tick_weeks],
            "tickangle": -45,
            "tickfont": {"size": 9},
            "showgrid": True, "gridcolor": "#eef3f8",
        },
        yaxis={"title": ""},
        showlegend=False,
        margin={"l": 12, "r": 12, "t": 88, "b": 52},
    )
    return fig


def physical_signal_weekly_trend_figure(payload: Dict[str, Any], lang: str = "en") -> go.Figure:
    records = payload.get("week_summary", []) if payload else []
    if not records:
        return empty_figure(t(lang, "figure.physical_signal_weekly.title"), t(lang, "figure.no_data"))

    week_df = pd.DataFrame(records)
    if week_df.empty or "week" not in week_df.columns:
        return empty_figure(t(lang, "figure.physical_signal_weekly.title"), t(lang, "figure.no_data"))

    week_df = week_df.sort_values("week").reset_index(drop=True)
    x_labels = [f"W{int(w)}" for w in week_df["week"].tolist()]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=week_df.get("indexed_weight", pd.Series([0] * len(week_df))).astype(float) / 1000.0,
            marker_color="#2d6fb7",
            name=t(lang, "figure.physical_signal_weekly.indexed_weight"),
            opacity=0.82,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=week_df.get("cumulative_weight_pct_vs_week_traceable_only", pd.Series([0] * len(week_df))).astype(float) * 100.0,
            mode="lines+markers",
            yaxis="y2",
            line={"width": 3, "color": "#2e8540"},
            marker={"size": 7},
            name=t(lang, "figure.physical_signal_weekly.cumulative_pct"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        title=t(lang, "figure.physical_signal_weekly.title"),
        xaxis_title=t(lang, "figure.physical_signal_weekly.x"),
        yaxis={"title": t(lang, "figure.physical_signal_weekly.y_left")},
        yaxis2={
            "title": t(lang, "figure.physical_signal_weekly.y_right"),
            "overlaying": "y",
            "side": "right",
            "range": [0, 105],
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
        margin={"l": 12, "r": 12, "t": 64, "b": 42},
        title_x=0.01,
    )
    return fig
