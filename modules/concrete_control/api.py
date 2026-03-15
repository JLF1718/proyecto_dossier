"""
Concrete Control - Module API
=============================
Service-level payload builders for backend endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from modules.concrete_control.data_loader import load_concrete
from modules.concrete_control.metrics import compute_concrete_metrics


def list_concrete_records(
    contratista: Optional[str] = None,
    estado: Optional[str] = None,
    elemento: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    df = load_concrete(contratista)

    if estado and "ESTADO" in df.columns:
        df = df[df["ESTADO"].astype(str).str.upper() == estado.upper()]
    if elemento and "ELEMENTO" in df.columns:
        df = df[df["ELEMENTO"].astype(str).str.upper() == elemento.upper()]

    total = len(df)
    items = df.iloc[skip : skip + limit].where(df.notna(), other=None).to_dict(orient="records")
    return {"total": total, "skip": skip, "limit": limit, "items": items}


def concrete_kpis(contratista: Optional[str] = None) -> Dict[str, Any]:
    df = load_concrete(contratista)
    return compute_concrete_metrics(df)
