"""
Concrete Control — Metrics
============================
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def compute_concrete_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return _empty()

    total = len(df)
    estado_counts = df["ESTADO"].value_counts() if "ESTADO" in df.columns else pd.Series(dtype=int)
    approved = int(estado_counts.get("APROBADO", 0))
    rejected = int(estado_counts.get("RECHAZADO", 0))
    pending = int(estado_counts.get("PENDIENTE", 0))

    approval_rate = round(approved / (approved + rejected) * 100, 2) if (approved + rejected) > 0 else 0.0

    avg_28d = 0.0
    if "RESISTENCIA_28D_MPA" in df.columns:
        series = pd.to_numeric(df["RESISTENCIA_28D_MPA"], errors="coerce").dropna()
        avg_28d = round(float(series.mean()), 2) if not series.empty else 0.0

    design_compliance = 0.0
    if "RESISTENCIA_28D_MPA" in df.columns and "RESISTENCIA_DISENIO_MPA" in df.columns:
        sub = df[["RESISTENCIA_28D_MPA", "RESISTENCIA_DISENIO_MPA"]].dropna()
        if not sub.empty:
            compliant = (pd.to_numeric(sub["RESISTENCIA_28D_MPA"], errors="coerce")
                         >= pd.to_numeric(sub["RESISTENCIA_DISENIO_MPA"], errors="coerce")).sum()
            design_compliance = round(compliant / len(sub) * 100, 2)

    return {
        "total_samples": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "approval_rate_pct": approval_rate,
        "avg_resistance_28d_mpa": avg_28d,
        "design_compliance_pct": design_compliance,
    }


def _empty() -> Dict[str, Any]:
    return {
        "total_samples": 0,
        "approved": 0,
        "rejected": 0,
        "pending": 0,
        "approval_rate_pct": 0.0,
        "avg_resistance_28d_mpa": 0.0,
        "design_compliance_pct": 0.0,
    }
