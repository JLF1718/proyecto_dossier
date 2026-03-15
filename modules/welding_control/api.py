"""
Welding Control - Module API
============================
Service-level payload builders for backend endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from modules.welding_control.data_loader import load_welds
from modules.welding_control.metrics import compute_weld_metrics


def list_weld_records(
    contratista: Optional[str] = None,
    estado: Optional[str] = None,
    proceso: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    df = load_welds(contratista)

    if estado and "ESTADO" in df.columns:
        df = df[df["ESTADO"].str.upper() == estado.upper()]
    if proceso and "PROCESO" in df.columns:
        df = df[df["PROCESO"].str.upper() == proceso.upper()]

    total = len(df)
    items = df.iloc[skip : skip + limit].where(df.notna(), other=None).to_dict(orient="records")
    return {"total": total, "skip": skip, "limit": limit, "items": items}


def weld_kpis(contratista: Optional[str] = None) -> Dict[str, Any]:
    df = load_welds(contratista)
    return compute_weld_metrics(df)
