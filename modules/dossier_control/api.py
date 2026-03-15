"""
Dossier Control - Module API
============================
Service-level helpers consumed by FastAPI routers and dashboard adapters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from backend.config import get_settings
from modules.dossier_control.data_loader import load_consolidated, load_dossiers


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return df.where(pd.notna(df), other=None).to_dict(orient="records")


def _filter_df(
    df: pd.DataFrame,
    contratista: Optional[str],
    estatus: Optional[str],
    etapa: Optional[str],
    entrega: Optional[str],
) -> pd.DataFrame:
    if contratista and "CONTRATISTA" in df.columns:
        df = df[df["CONTRATISTA"].str.upper() == contratista.upper()]
    if estatus and "ESTATUS" in df.columns:
        df = df[df["ESTATUS"].str.upper() == estatus.upper()]
    if etapa and "ETAPA" in df.columns:
        df = df[df["ETAPA"].str.upper() == etapa.upper()]
    if entrega and "ENTREGA" in df.columns:
        df = df[df["ENTREGA"].str.upper() == entrega.upper()]
    return df


def list_dossiers_data(
    contratista: Optional[str] = None,
    estatus: Optional[str] = None,
    etapa: Optional[str] = None,
    entrega: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    df = load_consolidated()
    df = _filter_df(df, contratista, estatus, etapa, entrega)
    total = len(df)
    page_df = df.iloc[skip : skip + limit]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": _df_to_records(page_df),
    }


def list_contractors() -> List[str]:
    settings = get_settings()
    return [k for k, v in settings.csv_paths.items() if v.exists()]


def list_statuses() -> List[str]:
    return ["PLANEADO", "OBSERVADO", "EN_REVISIÓN", "LIBERADO"]


def contractor_dossiers_data(
    contractor: str,
    estatus: Optional[str] = None,
    etapa: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    key = contractor.upper()
    settings = get_settings()
    csv_path = settings.csv_paths.get(key)

    if csv_path is None:
        raise ValueError(f"Unknown contractor: {contractor}")
    if not csv_path.exists():
        raise FileNotFoundError(f"No data file found for {contractor}")

    df = load_dossiers(key)
    df = _filter_df(df, None, estatus, etapa, None)
    total = len(df)
    page_df = df.iloc[skip : skip + limit]
    return {
        "contractor": key,
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": _df_to_records(page_df),
    }
