#!/usr/bin/env python3
"""
Normalize BAYSA dossier dataset
================================
Reads  : data/raw/ctrl_dossieres_baysa.csv
Outputs: data/processed/baysa_dossiers_clean.csv

Column mapping (raw → snake_case):
    N°                               → numero
    FASE                             → fase
    ETAPA                            → etapa
    HITO\\nSEMANA                    → hito_semana
    BLOQUE                           → bloque
    PESO DEL BLOQUE (Kg)             → peso_bloque_kg
    PESO DOSSIER (Kg)                → peso_dossier_kg
    TOTAL DE PIEZAS                  → total_piezas
    ESTATUS                          → estatus
    SEMANA DE LIBERACIÓN DE DOSSIER  → semana_liberacion_dossier

Status normalisation (raw → canonical):
    LIBERADO                  → approved
    OBSERVADO                 → pending
    ATENCIÓN COMENTARIOS      → pending
    EN REVISIÓN INPROS        → in_review
    REVISIÓN INPROS           → in_review

Run from the repository root:
    python scripts/normalize_baysa_dataset.py
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "data" / "raw" / "ctrl_dossieres_baysa.csv"
OUT_PATH = REPO_ROOT / "data" / "processed" / "baysa_dossiers_clean.csv"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONTRACTOR = "BAYSA"

COLUMN_RENAME: dict[str, str] = {
    "N°": "numero",
    "FASE": "fase",
    "ETAPA": "etapa",
    "HITO\nSEMANA": "hito_semana",
    "BLOQUE": "bloque",
    "PESO DEL BLOQUE (Kg)": "peso_bloque_kg",
    "PESO DOSSIER (Kg)": "peso_dossier_kg",
    "TOTAL DE PIEZAS": "total_piezas",
    "ESTATUS": "estatus",
    "SEMANA DE LIBERACIÓN DE DOSSIER": "semana_liberacion_dossier",
}

STATUS_MAP: dict[str, str] = {
    "LIBERADO": "approved",
    "OBSERVADO": "pending",
    "ATENCIÓN COMENTARIOS": "pending",
    "ATENCION COMENTARIOS": "pending",
    "EN REVISIÓN INPROS": "in_review",
    "EN REVISION INPROS": "in_review",
    "REVISIÓN INPROS": "in_review",
    "REVISION INPROS": "in_review",
    # Contract rule: rows marked out of contractual scope stay traceable in the
    # export but must not be classified as rejected by default.
    "FUERA DE ALCANCE": "pending",
}

# Dossier identifier must match PRO_<digits>  (e.g. PRO_01, PRO_123)
# Valid identifier formats:
#   PRO_<digits>      (e.g. PRO_01, PRO_123)
#   SUE_<digits>      (e.g. SUE_01, SUE_71)
#   DOSSIER GENERAL / DOSSIER PINTURA  (special summary dossiers)
BLOQUE_PATTERN = re.compile(r"^(PRO_\d+|SUE_\d+|DOSSIER\s+\w+)$")

# Numeric placeholder used in the dataset when the week is unknown
_PLACEHOLDER_WEEK = "--"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    """Return ASCII-folded version of *text* for robust status matching."""
    replacements = str.maketrans("áéíóúÁÉÍÓÚüÜñÑ", "aeiouAEIOUuUnN")
    return text.translate(replacements)


def _parse_numeric_weight(series: pd.Series) -> pd.Series:
    """Convert comma-formatted weight strings ('309,996.32') to float."""
    return (
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .replace({"nan": pd.NA, "": pd.NA, "None": pd.NA})
        .pipe(pd.to_numeric, errors="coerce")
    )


def _parse_week(series: pd.Series) -> pd.Series:
    """Convert week columns to nullable integer, treating '--' as missing."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({_PLACEHOLDER_WEEK: pd.NA, "nan": pd.NA, "": pd.NA, "None": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def _derive_in_contract_scope(series: pd.Series) -> pd.Series:
    """
    Contract rule:
    - integer N°  -> in scope
    - '--'        -> removed from contractual scope but kept for traceability
    """
    cleaned = series.astype(str).str.strip()
    return cleaned.ne(_PLACEHOLDER_WEEK) & cleaned.str.fullmatch(r"\d+")


def _normalize_status(series: pd.Series) -> pd.Series:
    """Map raw ESTATUS values to canonical (approved / pending / in_review)."""
    stripped = series.astype(str).str.strip()
    # Try direct match first, then accent-stripped match
    result = stripped.map(STATUS_MAP)
    unmapped_mask = result.isna() & stripped.notna() & (stripped != "nan")
    if unmapped_mask.any():
        accent_stripped = stripped[unmapped_mask].apply(_strip_accents).str.upper()
        accent_normalized = accent_stripped.map(
            {_strip_accents(k).upper(): v for k, v in STATUS_MAP.items()}
        )
        result[unmapped_mask] = accent_normalized
        still_unmapped = result.isna() & unmapped_mask
        if still_unmapped.any():
            for raw_val in stripped[still_unmapped].unique():
                log.warning("Unknown status value kept as-is: %r", raw_val)
            result[still_unmapped] = stripped[still_unmapped]
    return result


def _validate_bloque(series: pd.Series) -> pd.Series:
    """
    Validate dossier identifiers against the pattern PRO_<digits>.

    Malformed values are logged. The column is returned unchanged so that
    the full record is still exported, allowing downstream review.
    """
    invalid_mask = series.notna() & ~series.astype(str).str.match(BLOQUE_PATTERN)
    if invalid_mask.any():
        for val in series[invalid_mask].unique():
            log.warning("Malformed dossier identifier: %r — kept for review", val)
    return series


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def normalize() -> None:
    # ------------------------------------------------------------------
    # 1. Read raw CSV
    # ------------------------------------------------------------------
    if not IN_PATH.exists():
        log.error("Input file not found: %s", IN_PATH)
        sys.exit(1)

    df_raw = pd.read_csv(IN_PATH, header=0, dtype=str)
    rows_read = len(df_raw)
    log.info("Rows read           : %d", rows_read)
    log.info("Columns detected    : %s", list(df_raw.columns))

    # ------------------------------------------------------------------
    # 2. Drop fully-empty trailing columns (Unnamed: 10 … 14 – all NaN)
    # ------------------------------------------------------------------
    df = df_raw.loc[:, ~df_raw.columns.str.startswith("Unnamed")]

    # ------------------------------------------------------------------
    # 3. Drop rows where ALL key fields are NaN (trailing empty rows)
    # ------------------------------------------------------------------
    key_cols = [c for c in df.columns if c in COLUMN_RENAME]
    df = df.dropna(subset=key_cols, how="all")

    # ------------------------------------------------------------------
    # 4. Rename columns to snake_case
    # ------------------------------------------------------------------
    df = df.rename(columns=COLUMN_RENAME)

    # ------------------------------------------------------------------
    # 5. Strip whitespace from all string columns
    # ------------------------------------------------------------------
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # ------------------------------------------------------------------
    # 5b. Preserve contractual traceability for N°='--'
    # ------------------------------------------------------------------
    if "numero" in df.columns:
        df["in_contract_scope"] = _derive_in_contract_scope(df["numero"])

    # ------------------------------------------------------------------
    # 6. Add contractor identifier
    # ------------------------------------------------------------------
    df.insert(0, "contractor", CONTRACTOR)

    # ------------------------------------------------------------------
    # 7. Normalize status
    # ------------------------------------------------------------------
    if "estatus" in df.columns:
        df["estatus"] = _normalize_status(df["estatus"])

    # ------------------------------------------------------------------
    # 8. Parse numeric / weight fields
    # ------------------------------------------------------------------
    for col in ("peso_bloque_kg", "peso_dossier_kg"):
        if col in df.columns:
            df[col] = _parse_numeric_weight(df[col])

    for col in ("hito_semana", "semana_liberacion_dossier"):
        if col in df.columns:
            df[col] = _parse_week(df[col])

    for col in ("numero", "fase", "etapa", "total_piezas"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # ------------------------------------------------------------------
    # 9. Validate dossier identifiers (bloque)
    # ------------------------------------------------------------------
    if "bloque" in df.columns:
        _validate_bloque(df["bloque"])

    # ------------------------------------------------------------------
    # 10. Drop duplicates — key is (contractor, bloque, fase, etapa)
    # ------------------------------------------------------------------
    dup_key = [c for c in ("contractor", "bloque", "fase", "etapa") if c in df.columns]
    before_dedup = len(df)
    df = df.drop_duplicates(subset=dup_key, keep="first")
    duplicates_removed = before_dedup - len(df)
    if duplicates_removed:
        log.info("Duplicates removed  : %d", duplicates_removed)

    # ------------------------------------------------------------------
    # 11. Drop rows still missing required identifiers after cleaning
    # ------------------------------------------------------------------
    required = [c for c in ("bloque", "estatus") if c in df.columns]
    rows_before_drop = len(df)
    df = df.dropna(subset=required)
    rows_dropped = rows_before_drop - len(df)
    rows_cleaned = rows_read - len(df)

    rows_in_scope = int(df["in_contract_scope"].sum()) if "in_contract_scope" in df.columns else len(df)
    rows_out_of_scope = int((~df["in_contract_scope"]).sum()) if "in_contract_scope" in df.columns else 0

    log.info("Rows after cleaning : %d (dropped %d incomplete + %d duplicates)",
             len(df), rows_dropped, duplicates_removed)
    log.info("Rows in scope       : %d", rows_in_scope)
    log.info("Rows out of scope   : %d", rows_out_of_scope)
    if "estatus" in df.columns:
        log.info("Status distribution:\n%s", df["estatus"].value_counts(dropna=False).to_string())

    # ------------------------------------------------------------------
    # 12. Export
    # ------------------------------------------------------------------
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")

    rows_exported = len(df)
    log.info("Rows exported       : %d → %s", rows_exported, OUT_PATH)

    # Summary
    log.info("--- Summary ---")
    log.info("  Total rows         : %d", rows_read)
    log.info("  Rows in scope      : %d", rows_in_scope)
    log.info("  Rows out of scope  : %d", rows_out_of_scope)
    log.info("  Rows cleaned       : %d (removed from read)", rows_cleaned)
    log.info("  Rows exported      : %d", rows_exported)


if __name__ == "__main__":
    normalize()
