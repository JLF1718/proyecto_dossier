"""
Analytics — Metrics Layer
==========================
Thin adapter that wraps ``core.metricas`` (the canonical source of truth)
and exposes JSON-serialisable outputs suitable for FastAPI responses and
Dash callbacks.

Do NOT duplicate logic here.  All calculation rules live in core/metricas.py.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

# Re-use the SINGLE source of truth from core/
from core.metricas import (
    calcular_metricas_basicas,
    calcular_metricas_por_contratista,
    calcular_metricas_consolidadas,
    calcular_metricas_individuales,
)


def _round_dict(d: Dict[str, Any], decimals: int = 2) -> Dict[str, Any]:
    """Round all float values in a flat dict."""
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, float):
            out[k] = round(v, decimals)
        elif isinstance(v, dict):
            out[k] = _round_dict(v, decimals)
        else:
            out[k] = v
    return out


def compute_global_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Return global KPIs for *df* (any number of contractors)."""
    if df.empty:
        return _empty_metrics()
    raw = calcular_metricas_basicas(df)
    return _round_dict({
        "total_dossiers": int(raw["total_dossiers"]),
        "dossiers_liberados": int(raw["dossiers_liberados"]),
        "pct_liberado": float(raw["pct_liberado"]),
        "peso_total_ton": float(raw["peso_total"]),
        "peso_liberado_ton": float(raw["peso_liberado"]),
        "pct_peso_liberado": float(raw["pct_peso_liberado"]),
    })


def compute_by_contractor(df: pd.DataFrame) -> Dict[str, Any]:
    """Return {contractor: KPIs} for each contractor present in *df*."""
    if df.empty or "CONTRATISTA" not in df.columns:
        return {}

    raw_by_contr = calcular_metricas_por_contratista(df)
    result: Dict[str, Any] = {}
    for contratista, raw in raw_by_contr.items():
        result[contratista] = _round_dict({
            "total_dossiers": int(raw["total_dossiers"]),
            "dossiers_liberados": int(raw["dossiers_liberados"]),
            "pct_liberado": float(raw["pct_liberado"]),
            "peso_total_ton": float(raw["peso_total"]),
            "peso_liberado_ton": float(raw["peso_liberado"]),
            "pct_peso_liberado": float(raw["pct_peso_liberado"]),
        })
    return result


def compute_by_stage(df: pd.DataFrame) -> Dict[str, Any]:
    """Return KPIs broken down by ETAPA (construction stage)."""
    if df.empty or "ETAPA" not in df.columns:
        return {}

    result: Dict[str, Any] = {}
    for etapa in sorted(df["ETAPA"].dropna().unique()):
        df_etapa = df[df["ETAPA"] == etapa]
        raw = calcular_metricas_basicas(df_etapa)
        result[str(etapa)] = _round_dict({
            "total_dossiers": int(raw["total_dossiers"]),
            "dossiers_liberados": int(raw["dossiers_liberados"]),
            "pct_liberado": float(raw["pct_liberado"]),
            "peso_total_ton": float(raw["peso_total"]),
            "peso_liberado_ton": float(raw["peso_liberado"]),
            "pct_peso_liberado": float(raw["pct_peso_liberado"]),
        })
    return result


def compute_status_distribution(df: pd.DataFrame) -> Dict[str, int]:
    """Return count per ESTATUS value."""
    if df.empty or "ESTATUS" not in df.columns:
        return {}
    return df["ESTATUS"].value_counts().to_dict()


def compute_individual_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Extended metrics for single-contractor dashboards (includes brecha analysis)."""
    if df.empty:
        return _empty_metrics()
    raw = calcular_metricas_individuales(df)
    return _round_dict({k: (int(v) if isinstance(v, (int,)) else v) for k, v in raw.items()})


def _empty_metrics() -> Dict[str, Any]:
    return {
        "total_dossiers": 0,
        "dossiers_liberados": 0,
        "pct_liberado": 0.0,
        "peso_total_ton": 0.0,
        "peso_liberado_ton": 0.0,
        "pct_peso_liberado": 0.0,
    }
