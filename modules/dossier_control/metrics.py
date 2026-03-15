"""
Dossier Control — Metrics
==========================
Public API for dossier-specific KPI computation.
Delegates all maths to ``analytics.metrics`` which in turn uses
``core.metricas`` (the canonical source of truth).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from analytics.metrics import (
    compute_global_metrics,
    compute_by_contractor,
    compute_by_stage,
    compute_status_distribution,
    compute_individual_metrics,
)


def get_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Top-level KPIs for a dossier DataFrame."""
    return compute_global_metrics(df)


def get_kpis_by_contractor(df: pd.DataFrame) -> Dict[str, Any]:
    return compute_by_contractor(df)


def get_kpis_by_stage(df: pd.DataFrame) -> Dict[str, Any]:
    return compute_by_stage(df)


def get_status_distribution(df: pd.DataFrame) -> Dict[str, int]:
    return compute_status_distribution(df)


def get_individual_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Extended KPIs for single-contractor view (includes brecha analysis)."""
    return compute_individual_metrics(df)


def get_timeline_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare data for a delivery-week timeline chart.
    Returns a DataFrame with columns: ENTREGA, CONTRATISTA, count, peso_ton.
    """
    required = {"ENTREGA", "ESTATUS", "PESO"}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame()

    out = df.copy()
    out["PESO_TON"] = pd.to_numeric(out["PESO"], errors="coerce").fillna(0) / 1000.0
    cols = ["ENTREGA", "CONTRATISTA"] if "CONTRATISTA" in out.columns else ["ENTREGA"]

    agg = (
        out[out["ESTATUS"] == "LIBERADO"]
        .groupby(cols, as_index=False)
        .agg(count=("BLOQUE", "count"), peso_ton=("PESO_TON", "sum"))
        .sort_values("ENTREGA")
    )
    return agg
