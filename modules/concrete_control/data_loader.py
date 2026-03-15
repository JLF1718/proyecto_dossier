"""
Concrete Control — Data Loader
================================
Loads concrete QA records from CSV.
Expected CSV schema:

  MUESTRA_ID, CONTRATISTA, SISTEMA, ELEMENTO, FECHA_VACIADO,
  RESISTENCIA_DISENIO_MPA, RESISTENCIA_7D_MPA, RESISTENCIA_28D_MPA,
  ESTADO (APROBADO/RECHAZADO/PENDIENTE), OBSERVACIONES
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from analytics.data_processing import read_csv
from backend.config import get_settings

_CONCRETE_CSV_TEMPLATE = "ctrl_concreto_{contractor}_normalizado.csv"


def load_concrete(contractor: Optional[str] = None) -> pd.DataFrame:
    """Load concrete QA records for the given contractor (or all)."""
    settings = get_settings()
    data_dir = settings.data_dir

    if contractor:
        path = (
            data_dir / "contratistas" / contractor.upper()
            / _CONCRETE_CSV_TEMPLATE.format(contractor=contractor.upper())
        )
        if not path.exists():
            raise FileNotFoundError(f"No concrete QA file: {path}")
        return _normalise(read_csv(path), contractor.upper())

    frames = []
    for key in settings.csv_paths:
        path = (
            data_dir / "contratistas" / key
            / _CONCRETE_CSV_TEMPLATE.format(contractor=key)
        )
        if path.exists():
            frames.append(_normalise(read_csv(path), key))

    if not frames:
        raise FileNotFoundError("No concrete QA files found.")

    return pd.concat(frames, ignore_index=True)


def _normalise(df: pd.DataFrame, contratista: str) -> pd.DataFrame:
    out = df.copy()
    if "CONTRATISTA" not in out.columns:
        out["CONTRATISTA"] = contratista
    for col in ["RESISTENCIA_7D_MPA", "RESISTENCIA_28D_MPA", "RESISTENCIA_DISENIO_MPA"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if "FECHA_VACIADO" in out.columns:
        out["FECHA_VACIADO"] = pd.to_datetime(out["FECHA_VACIADO"], errors="coerce")
    return out
