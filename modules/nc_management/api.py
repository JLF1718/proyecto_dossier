"""
NC Management - Module API
==========================
Service-level payload builders for backend endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from modules.nc_management.data_loader import load_nc_records, save_nc_record
from modules.nc_management.metrics import compute_nc_metrics


def list_nc_records_data(
    contratista: Optional[str] = None,
    estado: Optional[str] = None,
    disciplina: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    df = load_nc_records()

    if contratista and "CONTRATISTA" in df.columns:
        df = df[df["CONTRATISTA"].astype(str).str.upper() == contratista.upper()]
    if estado and "ESTADO" in df.columns:
        df = df[df["ESTADO"].astype(str).str.upper() == estado.upper()]
    if disciplina and "DISCIPLINA" in df.columns:
        df = df[df["DISCIPLINA"].astype(str).str.upper() == disciplina.upper()]

    total = len(df)
    items = df.iloc[skip : skip + limit].where(df.notna(), other=None).to_dict(orient="records")
    return {"total": total, "skip": skip, "limit": limit, "items": items}


def nc_kpis(contratista: Optional[str] = None) -> Dict[str, Any]:
    df = load_nc_records()
    if contratista and "CONTRATISTA" in df.columns:
        df = df[df["CONTRATISTA"].astype(str).str.upper() == contratista.upper()]
    return compute_nc_metrics(df)


def create_nc_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    return save_nc_record(payload)
