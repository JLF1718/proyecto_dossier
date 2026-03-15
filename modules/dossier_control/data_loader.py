"""
Dossier Control — Data Loader
==============================
Loads and normalises dossier CSV files for each contractor.
Uses the shared analytics data processing pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd

from analytics.data_processing import load_and_normalise, consolidate
from backend.config import get_settings


def load_dossiers(contractor: str) -> pd.DataFrame:
    """
    Load normalised dossier data for a single contractor.

    Args:
        contractor: Contractor key (e.g. 'BAYSA', 'JAMAR').

    Returns:
        Normalised DataFrame.

    Raises:
        FileNotFoundError: if the CSV does not exist.
        ValueError: if contractor is unknown.
    """
    settings = get_settings()
    key = contractor.upper()
    csv_paths = settings.csv_paths

    if key not in csv_paths:
        raise ValueError(f"Unknown contractor: {contractor}. Valid values: {list(csv_paths.keys())}")

    path = csv_paths[key]
    df = load_and_normalise(path, contratista=key)
    return df


def load_consolidated() -> pd.DataFrame:
    """
    Load and concatenate dossier data for ALL configured contractors.
    Only contractors whose CSV file actually exists are included.
    """
    settings = get_settings()
    frames: List[pd.DataFrame] = []

    for key, path in settings.csv_paths.items():
        if not path.exists():
            continue
        df = load_and_normalise(path, contratista=key)
        frames.append(df)

    return consolidate(frames)


def load_dossiers_for_stage(contractor: str, etapa: str) -> pd.DataFrame:
    """Return dossiers filtered to a specific construction stage."""
    df = load_dossiers(contractor)
    if "ETAPA" not in df.columns:
        return df
    return df[df["ETAPA"].str.upper() == etapa.upper()]


def load_released_blocks() -> pd.DataFrame:
    """Return only LIBERADO dossiers across all contractors."""
    df = load_consolidated()
    if df.empty or "ESTATUS" not in df.columns:
        return pd.DataFrame()
    return df[df["ESTATUS"] == "LIBERADO"].copy()
