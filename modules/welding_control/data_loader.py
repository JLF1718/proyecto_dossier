"""
Welding Control — Data Loader
==============================
Loads weld inspection records from CSV / SQLite.
The expected CSV schema:

  JUNTA_ID, CONTRATISTA, SISTEMA, PROCESO (SMAW/GTAW/FCAW…),
  MATERIAL, DIAMETRO_PULG, ESPESOR_MM, SOLDADOR_ID,
  FECHA_SOLDADURA, FECHA_INSPECCION, ESTADO (ACEPTADO/RECHAZADO/PENDIENTE),
  TIPO_END (VT/RT/UT/PT/MT), RESULTADO_END, OBSERVACIONES
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from analytics.data_processing import read_csv, normalise_status
from backend.config import get_settings


_WELD_CSV_TEMPLATE = "ctrl_soldaduras_{contractor}_normalizado.csv"


def load_welds(contractor: Optional[str] = None) -> pd.DataFrame:
    """
    Load weld inspection records.

    Args:
        contractor: if given, load only that contractor's file.
                    If None, load and concatenate all available files.

    Raises:
        FileNotFoundError: if no weld CSV file is found.
    """
    settings = get_settings()
    data_dir = settings.data_dir

    if contractor:
        path = data_dir / "contratistas" / contractor.upper() / _WELD_CSV_TEMPLATE.format(contractor=contractor.upper())
        if not path.exists():
            raise FileNotFoundError(f"No welding data file: {path}")
        df = read_csv(path)
        df = _normalise(df, contractor.upper())
        return df

    frames = []
    for key in settings.csv_paths:
        path = data_dir / "contratistas" / key / _WELD_CSV_TEMPLATE.format(contractor=key)
        if path.exists():
            df = read_csv(path)
            df = _normalise(df, key)
            frames.append(df)

    if not frames:
        raise FileNotFoundError("No welding data files found.")

    return pd.concat(frames, ignore_index=True)


def _normalise(df: pd.DataFrame, contratista: str) -> pd.DataFrame:
    out = df.copy()
    if "CONTRATISTA" not in out.columns:
        out["CONTRATISTA"] = contratista
    if "ESTADO" in out.columns:
        out["ESTADO"] = out["ESTADO"].astype(str).str.strip().str.upper()
    if "FECHA_SOLDADURA" in out.columns:
        out["FECHA_SOLDADURA"] = pd.to_datetime(out["FECHA_SOLDADURA"], errors="coerce")
    if "FECHA_INSPECCION" in out.columns:
        out["FECHA_INSPECCION"] = pd.to_datetime(out["FECHA_INSPECCION"], errors="coerce")
    return out
