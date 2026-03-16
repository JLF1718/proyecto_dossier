from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

from backend.config import get_settings

log = logging.getLogger(__name__)

_ALLOWED_ESTIMACION_RE = re.compile(r"^[A-Z0-9 ./_\-]+$")
_DOSSIER_APPROVED = {"approved", "liberado", "aprobado"}


@dataclass(frozen=True)
class PieceSignalPaths:
    raw_excel: Path
    piece_clean: Path
    block_summary: Path
    week_summary: Path
    exceptions: Path


def _paths() -> PieceSignalPaths:
    settings = get_settings()
    processed = settings.data_dir / "processed"
    return PieceSignalPaths(
        raw_excel=settings.data_dir / "raw" / "avance_acumulado_global.xlsm",
        piece_clean=processed / "baysa_piece_index_clean.parquet",
        block_summary=processed / "baysa_piece_block_summary.parquet",
        week_summary=processed / "baysa_piece_week_summary.parquet",
        exceptions=processed / "baysa_piece_exceptions.parquet",
    )


def _dossier_processed_path() -> Path:
    settings = get_settings()
    return settings.data_dir / "processed" / "baysa_dossiers_clean.csv"


def _safe_str(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_block(value: object) -> str:
    return _safe_str(value).upper()


def _derive_family(block: str) -> str:
    if block.startswith("PRO"):
        return "PRO"
    if block.startswith("SUE"):
        return "SUE"
    return "SHARED"


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _coerce_week(series: pd.Series) -> pd.Series:
    cleaned = series.astype("object").map(_safe_str)
    cleaned = cleaned.replace({"": pd.NA, "--": pd.NA, "NONE": pd.NA, "NAN": pd.NA})
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def _normalize_estimacion(value: object) -> tuple[Optional[str], Optional[str], bool]:
    raw = _safe_str(value)
    if not raw:
        return (None, None, False)

    norm = " ".join(raw.upper().split())
    malformed = _ALLOWED_ESTIMACION_RE.fullmatch(norm) is None
    if malformed:
        # Keep a derived normalized value without mutating the raw source field.
        norm = re.sub(r"[^A-Z0-9 ./_\-]", "", norm)
        norm = " ".join(norm.split()) or None
    return (raw, norm, malformed)


def _join_flags(flags: Iterable[str]) -> str:
    items = sorted({flag for flag in flags if flag})
    return "|".join(items)


def _build_block_dim_map(dossier_df: pd.DataFrame) -> tuple[pd.DataFrame, set[str]]:
    work = dossier_df.copy()
    work["block"] = work.get("bloque", pd.Series(index=work.index, dtype="object")).map(_normalize_block)
    work = work[work["block"] != ""].copy()

    if "family" not in work.columns:
        work["family"] = work["block"].map(_derive_family)
    if "building" not in work.columns:
        work["building"] = work["family"]

    work["etapa"] = work.get("etapa", pd.Series(index=work.index, dtype="object"))
    work["fase"] = work.get("fase", pd.Series(index=work.index, dtype="object"))

    ambiguity = (
        work.groupby("block", dropna=False)
        .agg(
            etapa_nunique=("etapa", lambda s: int(s.dropna().nunique())),
            fase_nunique=("fase", lambda s: int(s.dropna().nunique())),
        )
        .reset_index()
    )
    ambiguous_blocks = {
        str(row.block)
        for row in ambiguity.itertuples(index=False)
        if int(row.etapa_nunique) > 1 or int(row.fase_nunique) > 1
    }

    dim_map = (
        work.groupby("block", dropna=False)
        .agg(
            family=("family", "first"),
            building=("building", "first"),
            etapa=("etapa", "first"),
            fase=("fase", "first"),
        )
        .reset_index()
    )
    return (dim_map, ambiguous_blocks)


def _transform_piece_index(piece_raw_df: pd.DataFrame, block_dim_map: pd.DataFrame) -> pd.DataFrame:
    base = pd.DataFrame(index=piece_raw_df.index)
    base["block"] = piece_raw_df.get("BLOQUE", pd.Series(index=piece_raw_df.index, dtype="object")).map(_normalize_block)
    base["marca"] = piece_raw_df.get("Marca", pd.Series(index=piece_raw_df.index, dtype="object")).astype("object")
    base["qty"] = _coerce_numeric(piece_raw_df.get("Cant.", pd.Series(index=piece_raw_df.index, dtype="float64")))
    base["nombre"] = piece_raw_df.get("Nombre", pd.Series(index=piece_raw_df.index, dtype="object")).astype("object")
    base["perfil"] = piece_raw_df.get("Perfil", pd.Series(index=piece_raw_df.index, dtype="object")).astype("object")
    base["largo_mm"] = _coerce_numeric(piece_raw_df.get("Largo (mm)", pd.Series(index=piece_raw_df.index, dtype="float64")))
    base["peso_unit_kg"] = _coerce_numeric(piece_raw_df.get("Peso(kg) un.", pd.Series(index=piece_raw_df.index, dtype="float64")))
    base["peso_total_kg"] = _coerce_numeric(piece_raw_df.get("Peso(kg) tot.", pd.Series(index=piece_raw_df.index, dtype="float64")))
    base["peso_descal_kg"] = _coerce_numeric(piece_raw_df.get("Peso(kg) Descal.", pd.Series(index=piece_raw_df.index, dtype="float64")))

    estimacion_parts = piece_raw_df.get("Estimacion", pd.Series(index=piece_raw_df.index, dtype="object")).map(_normalize_estimacion)
    base["estimacion_raw"] = estimacion_parts.map(lambda item: item[0])
    base["estimacion_norm"] = estimacion_parts.map(lambda item: item[1])
    base["estimacion_malformed"] = estimacion_parts.map(lambda item: bool(item[2]))

    base["semana"] = _coerce_week(piece_raw_df.get("Semana", pd.Series(index=piece_raw_df.index, dtype="object")))
    base["semana_is_blank"] = base["semana"].isna()
    base["nivel"] = piece_raw_df.get("Nivel", pd.Series(index=piece_raw_df.index, dtype="object")).astype("object")
    base["helper_col_1"] = piece_raw_df.get("Columna1", pd.Series(index=piece_raw_df.index, dtype="object")).astype("object")
    base["helper_col_2"] = piece_raw_df.get("Columna2", pd.Series(index=piece_raw_df.index, dtype="object")).astype("object")

    enriched = base.merge(block_dim_map, on="block", how="left")
    enriched["dossier_dim_match_flag"] = enriched["family"].notna()

    flags: list[str] = []
    data_quality: list[str] = []
    for row in enriched.itertuples(index=False):
        flags.clear()
        if row.block == "":
            flags.append("missing_block")
        if bool(row.semana_is_blank):
            flags.append("blank_semana")
        if bool(row.estimacion_malformed):
            flags.append("estimacion_malformed")
        if not bool(row.dossier_dim_match_flag):
            flags.append("dim_enrichment_missing")
        if pd.notna(row.peso_total_kg) and float(row.peso_total_kg) < 0:
            flags.append("negative_peso_total")
        data_quality.append(_join_flags(flags))

    enriched["data_quality_flags"] = data_quality
    enriched = enriched.drop(columns=["estimacion_malformed"])

    expected_columns = [
        "block",
        "marca",
        "qty",
        "nombre",
        "perfil",
        "largo_mm",
        "peso_unit_kg",
        "peso_total_kg",
        "peso_descal_kg",
        "estimacion_raw",
        "estimacion_norm",
        "semana",
        "semana_is_blank",
        "nivel",
        "helper_col_1",
        "helper_col_2",
        "family",
        "building",
        "etapa",
        "fase",
        "dossier_dim_match_flag",
        "data_quality_flags",
    ]
    return enriched[expected_columns]


def _build_piece_block_summary(clean_df: pd.DataFrame) -> pd.DataFrame:
    if clean_df.empty:
        return pd.DataFrame(
            columns=[
                "block",
                "family",
                "building",
                "etapa",
                "fase",
                "total_piece_rows",
                "blank_week_piece_rows",
                "week_tagged_piece_rows",
                "total_indexed_weight",
                "blank_week_weight",
                "week_tagged_weight",
                "week_tagged_piece_pct",
                "week_tagged_weight_pct",
                "first_week",
                "last_week",
                "has_bad_estimacion",
                "has_dim_gap",
                "has_progress_anomaly",
            ]
        )

    work = clean_df.copy()
    work["_weight"] = _coerce_numeric(work.get("peso_total_kg", pd.Series(index=work.index, dtype="float64"))).fillna(0.0)

    grouped = (
        work.groupby("block", dropna=False)
        .agg(
            family=("family", "first"),
            building=("building", "first"),
            etapa=("etapa", "first"),
            fase=("fase", "first"),
            total_piece_rows=("block", "size"),
            blank_week_piece_rows=("semana_is_blank", lambda s: int(s.sum())),
            total_indexed_weight=("_weight", "sum"),
            blank_week_weight=("_weight", lambda s: float(s[work.loc[s.index, "semana_is_blank"]].sum())),
            first_week=("semana", "min"),
            last_week=("semana", "max"),
            has_bad_estimacion=("data_quality_flags", lambda s: bool(s.astype(str).str.contains("estimacion_malformed", na=False).any())),
            has_dim_gap=("dossier_dim_match_flag", lambda s: bool((~s.fillna(False)).any())),
        )
        .reset_index()
    )

    grouped["week_tagged_piece_rows"] = grouped["total_piece_rows"] - grouped["blank_week_piece_rows"]
    grouped["week_tagged_weight"] = grouped["total_indexed_weight"] - grouped["blank_week_weight"]
    grouped["week_tagged_piece_pct"] = (
        grouped["week_tagged_piece_rows"]
        .div(grouped["total_piece_rows"].where(grouped["total_piece_rows"] > 0))
        .fillna(0.0)
    )
    grouped["week_tagged_weight_pct"] = (
        grouped["week_tagged_weight"]
        .div(grouped["total_indexed_weight"].where(grouped["total_indexed_weight"] > 0))
        .fillna(0.0)
    )
    grouped["has_progress_anomaly"] = (
        (grouped["week_tagged_weight"] > grouped["total_indexed_weight"] + 1e-6)
        | (grouped["week_tagged_weight"] < -1e-6)
        | (grouped["total_indexed_weight"] < -1e-6)
    )

    return grouped[
        [
            "block",
            "family",
            "building",
            "etapa",
            "fase",
            "total_piece_rows",
            "blank_week_piece_rows",
            "week_tagged_piece_rows",
            "total_indexed_weight",
            "blank_week_weight",
            "week_tagged_weight",
            "week_tagged_piece_pct",
            "week_tagged_weight_pct",
            "first_week",
            "last_week",
            "has_bad_estimacion",
            "has_dim_gap",
            "has_progress_anomaly",
        ]
    ]


def _build_piece_week_summary(clean_df: pd.DataFrame) -> pd.DataFrame:
    work = clean_df[clean_df["semana"].notna()].copy()
    if work.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "piece_rows",
                "distinct_blocks",
                "indexed_weight",
                "cumulative_piece_rows",
                "cumulative_indexed_weight",
                "cumulative_weight_pct_vs_total_index",
                "cumulative_weight_pct_vs_week_traceable_only",
            ]
        )

    work["_weight"] = _coerce_numeric(work.get("peso_total_kg", pd.Series(index=work.index, dtype="float64"))).fillna(0.0)
    weekly = (
        work.groupby("semana", dropna=True)
        .agg(
            piece_rows=("semana", "size"),
            distinct_blocks=("block", "nunique"),
            indexed_weight=("_weight", "sum"),
        )
        .reset_index()
        .rename(columns={"semana": "week"})
        .sort_values("week")
        .reset_index(drop=True)
    )

    weekly["cumulative_piece_rows"] = weekly["piece_rows"].cumsum()
    weekly["cumulative_indexed_weight"] = weekly["indexed_weight"].cumsum()

    total_index = float(_coerce_numeric(clean_df.get("peso_total_kg", pd.Series(dtype="float64"))).fillna(0.0).sum())
    total_traceable = float(weekly["indexed_weight"].sum())

    weekly["cumulative_weight_pct_vs_total_index"] = (
        weekly["cumulative_indexed_weight"].div(total_index if total_index > 0 else pd.NA).fillna(0.0)
    )
    weekly["cumulative_weight_pct_vs_week_traceable_only"] = (
        weekly["cumulative_indexed_weight"].div(total_traceable if total_traceable > 0 else pd.NA).fillna(0.0)
    )

    return weekly[
        [
            "week",
            "piece_rows",
            "distinct_blocks",
            "indexed_weight",
            "cumulative_piece_rows",
            "cumulative_indexed_weight",
            "cumulative_weight_pct_vs_total_index",
            "cumulative_weight_pct_vs_week_traceable_only",
        ]
    ]


def _build_dossier_block_progress(dossier_df: pd.DataFrame) -> pd.DataFrame:
    work = dossier_df.copy()
    work["block"] = work.get("bloque", pd.Series(index=work.index, dtype="object")).map(_normalize_block)
    work = work[work["block"] != ""].copy()

    work["status_norm"] = work.get("estatus", pd.Series(index=work.index, dtype="object")).map(
        lambda v: _safe_str(v).lower().replace("_", " ")
    )
    work["contractual_weight_kg"] = _coerce_numeric(work.get("peso_bloque_kg", pd.Series(index=work.index, dtype="float64"))).fillna(0.0)
    work["dossier_weight_kg"] = _coerce_numeric(work.get("peso_dossier_kg", pd.Series(index=work.index, dtype="float64"))).fillna(0.0)
    work["approved_weight_kg"] = work["dossier_weight_kg"].where(work["status_norm"].isin(_DOSSIER_APPROVED), 0.0)
    work["family"] = work["block"].map(_derive_family)
    work["building"] = work["family"]

    grouped = (
        work.groupby("block", dropna=False)
        .agg(
            family=("family", "first"),
            building=("building", "first"),
            etapa=("etapa", "first"),
            fase=("fase", "first"),
            contractual_weight_kg=("contractual_weight_kg", "max"),
            documented_weight_kg=("approved_weight_kg", "sum"),
        )
        .reset_index()
    )
    grouped["documented_progress_pct"] = (
        grouped["documented_weight_kg"].div(grouped["contractual_weight_kg"].where(grouped["contractual_weight_kg"] > 0)).fillna(0.0)
    )
    return grouped


def _build_block_comparison(block_summary: pd.DataFrame, dossier_progress: pd.DataFrame) -> pd.DataFrame:
    piece_cols = [
        "block",
        "family",
        "building",
        "etapa",
        "fase",
        "total_indexed_weight",
        "week_tagged_weight",
        "week_tagged_weight_pct",
    ]
    piece = block_summary[piece_cols].copy() if not block_summary.empty else pd.DataFrame(columns=piece_cols)

    merged = piece.merge(
        dossier_progress,
        on="block",
        how="outer",
        suffixes=("_piece", "_dossier"),
    )

    for dim in ("family", "building", "etapa", "fase"):
        merged[dim] = merged.get(f"{dim}_piece").combine_first(merged.get(f"{dim}_dossier"))

    merged["total_indexed_weight"] = _coerce_numeric(merged.get("total_indexed_weight", 0)).fillna(0.0)
    merged["week_tagged_weight"] = _coerce_numeric(merged.get("week_tagged_weight", 0)).fillna(0.0)
    merged["contractual_weight_kg"] = _coerce_numeric(merged.get("contractual_weight_kg", 0)).fillna(0.0)
    merged["documented_weight_kg"] = _coerce_numeric(merged.get("documented_weight_kg", 0)).fillna(0.0)

    merged["documented_progress_pct"] = _coerce_numeric(merged.get("documented_progress_pct", 0)).fillna(0.0)
    merged["physical_signal_pct"] = (
        merged["week_tagged_weight"].div(merged["total_indexed_weight"].where(merged["total_indexed_weight"] > 0)).fillna(0.0)
    )

    merged["physical_signal_present_but_no_dossier_context"] = (
        (merged["total_indexed_weight"] > 0)
        & (merged["contractual_weight_kg"] <= 0)
    )
    merged["dossier_context_present_but_no_piece_signal"] = (
        (merged["contractual_weight_kg"] > 0)
        & (merged["total_indexed_weight"] <= 0)
    )

    diff = merged["physical_signal_pct"] - merged["documented_progress_pct"]
    merged["physical_signal_ahead_of_documentary"] = diff > 0.10
    merged["documentary_ahead_of_physical_signal"] = diff < -0.10
    merged["both_low"] = (merged["physical_signal_pct"] < 0.15) & (merged["documented_progress_pct"] < 0.15)
    merged["both_aligned"] = diff.abs() <= 0.10

    def _status(row: pd.Series) -> str:
        if bool(row["physical_signal_present_but_no_dossier_context"]):
            return "physical_signal_present_but_no_dossier_context"
        if bool(row["dossier_context_present_but_no_piece_signal"]):
            return "dossier_context_present_but_no_piece_signal"
        if bool(row["both_low"]):
            return "both_low"
        if bool(row["physical_signal_ahead_of_documentary"]):
            return "physical_signal_ahead_of_documentary"
        if bool(row["documentary_ahead_of_physical_signal"]):
            return "documentary_ahead_of_physical_signal"
        return "both_aligned"

    merged["alignment_status"] = merged.apply(_status, axis=1)

    return merged[
        [
            "block",
            "family",
            "building",
            "etapa",
            "fase",
            "documented_progress_pct",
            "physical_signal_pct",
            "alignment_status",
            "physical_signal_ahead_of_documentary",
            "documentary_ahead_of_physical_signal",
            "both_low",
            "both_aligned",
            "physical_signal_present_but_no_dossier_context",
            "dossier_context_present_but_no_piece_signal",
        ]
    ]


def _build_piece_exceptions(
    clean_df: pd.DataFrame,
    block_summary: pd.DataFrame,
    comparison_df: pd.DataFrame,
    *,
    ambiguous_blocks: set[str],
) -> pd.DataFrame:
    exceptions: list[dict[str, Any]] = []

    malformed = clean_df[clean_df["data_quality_flags"].astype(str).str.contains("estimacion_malformed", na=False)]
    for row in malformed.itertuples(index=True):
        exceptions.append(
            {
                "exception_type": "malformed estimation value",
                "severity": "medium",
                "block": row.block,
                "week": row.semana,
                "row_index": int(row.Index),
                "details": f"estimacion_raw={row.estimacion_raw}",
            }
        )

    dim_gap_blocks = block_summary[block_summary["has_dim_gap"]]
    for row in dim_gap_blocks.itertuples(index=False):
        exceptions.append(
            {
                "exception_type": "missing dimensional enrichment from dossier source",
                "severity": "high",
                "block": row.block,
                "week": None,
                "row_index": None,
                "details": "No block-level family/building/etapa/fase match found in dossier source.",
            }
        )

    blank_week_blocks = block_summary[block_summary["week_tagged_piece_rows"] == 0]
    for row in blank_week_blocks.itertuples(index=False):
        exceptions.append(
            {
                "exception_type": "block with all rows blank in Semana",
                "severity": "medium",
                "block": row.block,
                "week": None,
                "row_index": None,
                "details": "Block has no week-tagged rows; treated as historic/pre-trace signal.",
            }
        )

    anomaly_blocks = block_summary[block_summary["has_progress_anomaly"]]
    for row in anomaly_blocks.itertuples(index=False):
        exceptions.append(
            {
                "exception_type": "block-level anomalies where weekly tagged weight exceeds indexed total weight",
                "severity": "high",
                "block": row.block,
                "week": None,
                "row_index": None,
                "details": f"week_tagged_weight={row.week_tagged_weight} total_indexed_weight={row.total_indexed_weight}",
            }
        )

    for block in sorted(ambiguous_blocks):
        exceptions.append(
            {
                "exception_type": "ambiguous block mapping issues",
                "severity": "high",
                "block": block,
                "week": None,
                "row_index": None,
                "details": "Dossier block maps to multiple etapa/fase values.",
            }
        )

    if not block_summary.empty:
        q1 = float(block_summary["total_indexed_weight"].quantile(0.25))
        q3 = float(block_summary["total_indexed_weight"].quantile(0.75))
        iqr = max(q3 - q1, 0.0)
        outlier_limit = q3 + (3.0 * iqr)
        outliers = block_summary[block_summary["total_indexed_weight"] > outlier_limit]
        for row in outliers.itertuples(index=False):
            exceptions.append(
                {
                    "exception_type": "suspicious business outliers",
                    "severity": "medium",
                    "block": row.block,
                    "week": None,
                    "row_index": None,
                    "details": f"total_indexed_weight={row.total_indexed_weight:.2f} above_iqr_limit={outlier_limit:.2f}",
                }
            )

    if not comparison_df.empty:
        no_context = comparison_df[comparison_df["physical_signal_present_but_no_dossier_context"]]
        for row in no_context.itertuples(index=False):
            exceptions.append(
                {
                    "exception_type": "physical signal present but no dossier context",
                    "severity": "high",
                    "block": row.block,
                    "week": None,
                    "row_index": None,
                    "details": "Piece signal exists but no dossier contractual baseline found.",
                }
            )

    return pd.DataFrame(
        exceptions,
        columns=["exception_type", "severity", "block", "week", "row_index", "details"],
    )


def build_piece_signal_outputs(
    *,
    piece_raw_df: Optional[pd.DataFrame] = None,
    dossier_df: Optional[pd.DataFrame] = None,
    write_outputs: bool = True,
) -> dict[str, pd.DataFrame]:
    paths = _paths()

    if piece_raw_df is None:
        if not paths.raw_excel.exists():
            raise FileNotFoundError(f"Piece index workbook not found: {paths.raw_excel}")
        piece_raw_df = pd.read_excel(paths.raw_excel, sheet_name="INDICE")

    if dossier_df is None:
        dossier_path = _dossier_processed_path()
        if not dossier_path.exists():
            raise FileNotFoundError(f"Processed dossier CSV not found: {dossier_path}")
        dossier_df = pd.read_csv(dossier_path)

    block_dim_map, ambiguous_blocks = _build_block_dim_map(dossier_df)
    piece_clean = _transform_piece_index(piece_raw_df, block_dim_map)
    block_summary = _build_piece_block_summary(piece_clean)
    week_summary = _build_piece_week_summary(piece_clean)
    dossier_progress = _build_dossier_block_progress(dossier_df)
    comparison = _build_block_comparison(block_summary, dossier_progress)
    exceptions = _build_piece_exceptions(
        piece_clean,
        block_summary,
        comparison,
        ambiguous_blocks=ambiguous_blocks,
    )

    if write_outputs:
        paths.piece_clean.parent.mkdir(parents=True, exist_ok=True)
        piece_clean.to_parquet(paths.piece_clean, index=False)
        block_summary.to_parquet(paths.block_summary, index=False)
        week_summary.to_parquet(paths.week_summary, index=False)
        exceptions.to_parquet(paths.exceptions, index=False)
        log.info("Piece signal outputs written to %s", paths.piece_clean.parent)

    return {
        "piece_clean": piece_clean,
        "block_summary": block_summary,
        "week_summary": week_summary,
        "exceptions": exceptions,
        "comparison": comparison,
    }


def load_piece_signal_payload(*, rebuild_if_missing: bool = True) -> dict[str, Any]:
    paths = _paths()
    if rebuild_if_missing and (
        not paths.piece_clean.exists()
        or not paths.block_summary.exists()
        or not paths.week_summary.exists()
        or not paths.exceptions.exists()
    ):
        build_piece_signal_outputs(write_outputs=True)

    piece_clean = pd.read_parquet(paths.piece_clean) if paths.piece_clean.exists() else pd.DataFrame()
    block_summary = pd.read_parquet(paths.block_summary) if paths.block_summary.exists() else pd.DataFrame()
    week_summary = pd.read_parquet(paths.week_summary) if paths.week_summary.exists() else pd.DataFrame()
    exceptions = pd.read_parquet(paths.exceptions) if paths.exceptions.exists() else pd.DataFrame()

    dossier_path = _dossier_processed_path()
    dossier_df = pd.read_csv(dossier_path) if dossier_path.exists() else pd.DataFrame()
    comparison = _build_block_comparison(block_summary, _build_dossier_block_progress(dossier_df))

    total_indexed_weight = float(block_summary.get("total_indexed_weight", pd.Series(dtype="float64")).sum())
    week_tagged_weight = float(block_summary.get("week_tagged_weight", pd.Series(dtype="float64")).sum())
    blank_week_weight = float(block_summary.get("blank_week_weight", pd.Series(dtype="float64")).sum())
    coverage_pct = week_tagged_weight / total_indexed_weight if total_indexed_weight > 0 else 0.0

    return {
        "kpis": {
            "indexed_weight_total": total_indexed_weight,
            "week_tagged_weight": week_tagged_weight,
            "week_trace_coverage_pct": coverage_pct,
            "blank_week_historic_weight": blank_week_weight,
        },
        "piece_clean": piece_clean,
        "block_summary": block_summary,
        "week_summary": week_summary,
        "exceptions": exceptions,
        "comparison": comparison,
    }
