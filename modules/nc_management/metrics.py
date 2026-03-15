"""
NC Management — Metrics
========================
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def compute_nc_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return _empty()

    total = len(df)
    estado_counts = df["ESTADO"].value_counts() if "ESTADO" in df.columns else pd.Series(dtype=int)
    open_nc = int(estado_counts.get("ABIERTA", 0))
    in_progress = int(estado_counts.get("EN_PROCESO", 0))
    closed = int(estado_counts.get("CERRADA", 0))
    closure_rate = round(closed / total * 100, 2) if total > 0 else 0.0

    # Average days to close
    avg_days_to_close = 0.0
    if "FECHA_EMISION" in df.columns and "FECHA_CIERRE" in df.columns:
        sub = df.dropna(subset=["FECHA_EMISION", "FECHA_CIERRE"]).copy()
        if not sub.empty:
            delta = (
                pd.to_datetime(sub["FECHA_CIERRE"], errors="coerce")
                - pd.to_datetime(sub["FECHA_EMISION"], errors="coerce")
            ).dt.days.dropna()
            if not delta.empty:
                avg_days_to_close = round(float(delta.mean()), 1)

    by_discipline: Dict[str, int] = {}
    if "DISCIPLINA" in df.columns:
        by_discipline = df["DISCIPLINA"].value_counts().to_dict()

    by_contractor: Dict[str, int] = {}
    if "CONTRATISTA" in df.columns:
        by_contractor = df["CONTRATISTA"].value_counts().to_dict()

    return {
        "total_nc": total,
        "open": open_nc,
        "in_progress": in_progress,
        "closed": closed,
        "closure_rate_pct": closure_rate,
        "avg_days_to_close": avg_days_to_close,
        "by_discipline": by_discipline,
        "by_contractor": by_contractor,
    }


def _empty() -> Dict[str, Any]:
    return {
        "total_nc": 0,
        "open": 0,
        "in_progress": 0,
        "closed": 0,
        "closure_rate_pct": 0.0,
        "avg_days_to_close": 0.0,
        "by_discipline": {},
        "by_contractor": {},
    }
