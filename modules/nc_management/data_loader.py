"""
NC Management — Data Loader
=============================
Loads Non-Conformance records from CSV or SQLite.
Expected CSV schema:

  NUMERO_NC, CONTRATISTA, DESCRIPCION, DISCIPLINA, SISTEMA,
  RESPONSABLE, FECHA_EMISION, FECHA_CIERRE,
  ESTADO (ABIERTA/EN_PROCESO/CERRADA), ACCION_CORRECTIVA
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from analytics.data_processing import read_csv
from backend.config import get_settings

_NC_CSV = "nc_forms.csv"
_NC_COLUMNS = [
    "NUMERO_NC", "CONTRATISTA", "DESCRIPCION", "DISCIPLINA",
    "SISTEMA", "RESPONSABLE", "FECHA_EMISION", "FECHA_CIERRE",
    "ESTADO", "ACCION_CORRECTIVA",
]


def _nc_path() -> Path:
    settings = get_settings()
    return settings.data_dir / _NC_CSV


def load_nc_records() -> pd.DataFrame:
    """Load all NC records from the shared CSV file."""
    path = _nc_path()
    if not path.exists():
        raise FileNotFoundError(f"NC records file not found: {path}")

    df = read_csv(path)
    df = _normalise(df)
    return df


def save_nc_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a new NC record to the CSV file.
    Creates the file if it does not exist.
    """
    path = _nc_path()
    now_iso = datetime.utcnow().isoformat()

    row: Dict[str, Any] = {col: None for col in _NC_COLUMNS}
    row.update({
        "NUMERO_NC": data.get("numero_nc", ""),
        "CONTRATISTA": str(data.get("contratista", "")).upper(),
        "DESCRIPCION": data.get("descripcion", ""),
        "DISCIPLINA": data.get("disciplina", ""),
        "SISTEMA": data.get("sistema", ""),
        "RESPONSABLE": data.get("responsable", ""),
        "FECHA_EMISION": data.get("fecha_emision", now_iso),
        "FECHA_CIERRE": None,
        "ESTADO": "ABIERTA",
        "ACCION_CORRECTIVA": "",
    })

    new_row_df = pd.DataFrame([row])

    if path.exists():
        existing = read_csv(path)
        df = pd.concat([existing, new_row_df], ignore_index=True)
    else:
        df = new_row_df

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return row


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "ESTADO" in out.columns:
        out["ESTADO"] = out["ESTADO"].astype(str).str.strip().str.upper()
    for col in ["FECHA_EMISION", "FECHA_CIERRE"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out
