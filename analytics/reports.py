"""
Analytics — Report Generators
================================
Wrappers around ``generators/`` to produce HTML report artifacts from
within the new architecture, while preserving the original logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

# Re-use existing generator modules
from generators.utils_generator import (
    obtener_estructura_directorios,
    crear_directorios,
    guardar_archivos_consolidados,
    guardar_archivos_individuales,
)


def generate_individual_dashboard(
    df: pd.DataFrame,
    contratista: str,
    semana: str,
    output_dir: Path,
    config: dict,
) -> Optional[Path]:
    """
    Thin wrapper: build and save a single-contractor HTML dashboard.
    Delegates to the existing plotly generator pipeline.
    """
    from generators.dashboard_generator import generar_dashboard  # noqa: PLC0415

    dirs = obtener_estructura_directorios(output_dir)
    crear_directorios(dirs)

    from datetime import datetime  # noqa: PLC0415

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fig = generar_dashboard(df, config, contratista=contratista)
    if fig is None:
        return None

    html_path, _ = guardar_archivos_individuales(
        fig, contratista, timestamp, semana, dirs, config, df_data=df
    )
    return html_path


def generate_consolidated_dashboard(
    df: pd.DataFrame,
    semana: str,
    output_dir: Path,
    config: dict,
) -> Optional[Path]:
    """
    Thin wrapper: build and save the multi-contractor consolidated dashboard.
    """
    from generators.consolidado_generator import generar_dashboard_consolidado  # noqa: PLC0415
    from datetime import datetime  # noqa: PLC0415

    dirs = obtener_estructura_directorios(output_dir)
    crear_directorios(dirs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    fig = generar_dashboard_consolidado(df, config)
    if fig is None:
        return None

    html_path, _ = guardar_archivos_consolidados(fig, timestamp, semana, dirs, config)
    return html_path
