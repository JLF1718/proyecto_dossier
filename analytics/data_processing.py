"""
Analytics — Data Processing Utilities
======================================
Central CSV loading and normalisation helpers.
Delegates heavy logic to ``generators/utils_generator.py`` (existing module)
and adds cross-cutting helpers needed by the new platform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Re-use the existing robust CSV reader
from generators.utils_generator import leer_csv_robusto

_STATUS_CANONICAL: Dict[str, str] = {
    "NO_INICIADO": "PLANEADO",
    "POR_ASIGNAR": "PLANEADO",
    "PLANEADO": "PLANEADO",
    "OBSERVADO": "OBSERVADO",
    "EN_REVISION": "EN_REVISIÓN",
    "EN_REVISIÓN": "EN_REVISIÓN",
    "LIBERADO": "LIBERADO",
    "INPROS_REVISANDO": "EN_REVISIÓN",
    "BAYSA_ATENDIENDO_COMENTARIOS": "OBSERVADO",
}


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with automatic encoding detection."""
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return leer_csv_robusto(path)


def normalise_status(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw status values to the canonical set in-place (returns copy)."""
    if "ESTATUS" not in df.columns:
        return df
    out = df.copy()
    raw = out["ESTATUS"].astype(str).str.strip().str.upper()
    out["ESTATUS"] = raw.map(_STATUS_CANONICAL).fillna(raw)
    return out


def normalise_weight(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure PESO column is numeric (kg); fill NaN with 0."""
    if "PESO" not in df.columns:
        return df
    out = df.copy()
    out["PESO"] = pd.to_numeric(out["PESO"], errors="coerce").fillna(0.0)
    return out


def load_and_normalise(path: Path, contratista: Optional[str] = None) -> pd.DataFrame:
    """
    Full pipeline: read → normalise status → normalise weight → tag contractor.
    """
    df = read_csv(path)
    df = normalise_status(df)
    df = normalise_weight(df)
    if contratista and "CONTRATISTA" not in df.columns:
        df["CONTRATISTA"] = contratista
    return df


def consolidate(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate multiple DataFrames into a consolidated frame."""
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def filter_by_status(df: pd.DataFrame, statuses: List[str]) -> pd.DataFrame:
    if "ESTATUS" not in df.columns:
        return df
    return df[df["ESTATUS"].isin([s.upper() for s in statuses])]


def pivot_status_by_stage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a pivot table: rows=ETAPA, columns=ESTATUS, values=count.
    Useful for grouped bar charts.
    """
    if df.empty or not {"ETAPA", "ESTATUS"}.issubset(df.columns):
        return pd.DataFrame()
    return (
        df.groupby(["ETAPA", "ESTATUS"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )


def pivot_weight_by_stage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a pivot table: rows=ETAPA, ESTATUS, values=PESO_TON.
    """
    if df.empty or not {"ETAPA", "ESTATUS", "PESO"}.issubset(df.columns):
        return pd.DataFrame()
    out = df.copy()
    out["PESO_TON"] = out["PESO"] / 1000.0
    return (
        out.groupby(["ETAPA", "ESTATUS"])["PESO_TON"]
        .sum()
        .reset_index()
    )
