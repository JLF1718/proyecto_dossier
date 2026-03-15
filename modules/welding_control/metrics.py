"""
Welding Control — Metrics
==========================
KPIs for weld inspection records.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def compute_weld_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute welding inspection KPIs.

    Returns:
        total_joints: total number of weld joints
        accepted: count with ESTADO='ACEPTADO'
        rejected: count with ESTADO='RECHAZADO'
        pending: count with ESTADO='PENDIENTE'
        acceptance_rate_pct: accepted / (accepted + rejected) * 100
        rejection_rate_pct: rejected / (accepted + rejected) * 100
        by_process: count breakdown by PROCESO
        by_inspector_type: count by TIPO_END
    """
    if df.empty:
        return _empty()

    total = len(df)
    estado_counts = df["ESTADO"].value_counts() if "ESTADO" in df.columns else pd.Series(dtype=int)
    accepted = int(estado_counts.get("ACEPTADO", 0))
    rejected = int(estado_counts.get("RECHAZADO", 0))
    pending = int(estado_counts.get("PENDIENTE", 0))
    inspected = accepted + rejected

    acceptance_rate = round(accepted / inspected * 100, 2) if inspected > 0 else 0.0
    rejection_rate = round(rejected / inspected * 100, 2) if inspected > 0 else 0.0

    by_process: Dict[str, int] = {}
    if "PROCESO" in df.columns:
        by_process = df["PROCESO"].value_counts().to_dict()

    by_end_type: Dict[str, int] = {}
    if "TIPO_END" in df.columns:
        by_end_type = df["TIPO_END"].value_counts().to_dict()

    return {
        "total_joints": total,
        "accepted": accepted,
        "rejected": rejected,
        "pending": pending,
        "acceptance_rate_pct": acceptance_rate,
        "rejection_rate_pct": rejection_rate,
        "by_process": by_process,
        "by_end_type": by_end_type,
    }


def _empty() -> Dict[str, Any]:
    return {
        "total_joints": 0,
        "accepted": 0,
        "rejected": 0,
        "pending": 0,
        "acceptance_rate_pct": 0.0,
        "rejection_rate_pct": 0.0,
        "by_process": {},
        "by_end_type": {},
    }
