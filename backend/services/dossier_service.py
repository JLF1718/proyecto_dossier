"""
Dossier KPI service
===================
Public API:

    load_dossiers() -> pd.DataFrame
        Read data/processed/baysa_dossiers_clean.csv, standardise columns,
        log rows_loaded / rows_in_scope.  Returns the FULL dataset (including
        out-of-scope rows) so callers can inspect traceability data.

    compute_kpis(df) -> dict
        Filter rows where in_contract_scope == True, then return:
            total_dossiers, approved_dossiers, pending_dossiers, in_review_dossiers
        plus status_distribution and backward-compatible legacy keys.

Contractual rules implemented here:
- Rows with N° == "--" mean the block was removed from the contractual scope.
  They stay in the exported dataset for traceability but must NOT be counted
  in KPI metrics (in_contract_scope == False).
- "REVISIÓN INPROS" is NOT a rejection — it is a temporary internal review stage
  (canonical status: in_review).
- Rejected dossiers should only appear if a true rejection is present in the data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from backend.config import get_settings

log = logging.getLogger(__name__)

_STATUS_MAP: dict[str, str] = {
    "approved": "approved",
    "liberado": "approved",
    "aprobado": "approved",
    "pending": "pending",
    "observado": "pending",
    "atencion comentarios": "pending",
    "atención comentarios": "pending",
    "in_review": "in_review",
    "in review": "in_review",
    "en revision inpros": "in_review",
    "en revisión inpros": "in_review",
    "revision inpros": "in_review",
    "revisión inpros": "in_review",
    "rejected": "rejected",
    "rechazado": "rejected",
    # Not a rejection under the contract. These rows are retained for traceability
    # and excluded from KPIs via ``in_contract_scope == False``.
    "fuera de alcance": "out_of_scope",
}


def _processed_baysa_path() -> Path:
    settings = get_settings()
    return settings.data_dir / "processed" / "baysa_dossiers_clean.csv"


def _normalise_status(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    raw = str(value).strip().lower().replace("_", " ")
    return _STATUS_MAP.get(raw, raw.replace(" ", "_"))


def _normalise_bool(value: object, default: bool = True) -> bool:
    if pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def _normalise_stage(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.upper().startswith("ETAPA_"):
        return text.upper()
    if text.isdigit():
        return f"ETAPA_{text}"
    return text.upper().replace(" ", "_")


def _normalise_weight(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _standardize_baysa_processed(df: pd.DataFrame) -> pd.DataFrame:

    out = pd.DataFrame()

    contractor_col = df.get("contractor", pd.Series("BAYSA", index=df.index, dtype="object"))
    out["contractor"] = contractor_col.fillna("BAYSA").astype(str).str.upper()

    out["stage"] = df.get("etapa", pd.Series(index=df.index, dtype="object")).apply(_normalise_stage)

    out["status"] = df.get("estatus", pd.Series(index=df.index, dtype="object")).apply(_normalise_status)

    # Prefer normalized scope column when present in processed CSV.
    if "in_contract_scope" in df.columns:
        out["in_contract_scope"] = df["in_contract_scope"].apply(_normalise_bool)
    else:
        # Compatibility fallback for transitional exports.
        numero = df.get("N°", df.get("numero", pd.Series(index=df.index, dtype="object")))
        out["in_contract_scope"] = numero.astype(str).str.strip() != "--"

    out["weight_kg"] = _normalise_weight(
        df.get("peso_dossier_kg", df.get("peso_bloque_kg", pd.Series(index=df.index, dtype="float64")))
    )

    return out


def _standardize_legacy_frame(df: pd.DataFrame, contractor: str) -> pd.DataFrame:
    out = pd.DataFrame()
    contractor_col = df.get("CONTRATISTA", pd.Series(contractor, index=df.index, dtype="object"))
    out["contractor"] = contractor_col.fillna(contractor).astype(str).str.upper()
    out["stage"] = df.get("ETAPA", pd.Series(index=df.index, dtype="object")).apply(_normalise_stage)
    out["status"] = df.get("ESTATUS", pd.Series(index=df.index, dtype="object")).apply(_normalise_status)
    out["in_contract_scope"] = df.get(
        "in_contract_scope", pd.Series(True, index=df.index, dtype="bool")
    ).apply(lambda value: _normalise_bool(value, default=True))
    out["weight_kg"] = _normalise_weight(df.get("PESO", pd.Series(index=df.index, dtype="float64")))
    return out


def _load_baysa_processed() -> pd.DataFrame:
    path = _processed_baysa_path()
    if not path.exists():
        raise FileNotFoundError(f"Processed BAYSA dataset not found: {path}")
    df = pd.read_csv(path)
    return _standardize_baysa_processed(df)


def _load_standardized_contractor(contractor: str) -> pd.DataFrame:
    key = contractor.upper()
    if key != "BAYSA":
        raise ValueError(
            f"Unsupported contractor '{contractor}'. This deployment serves only BAYSA processed data."
        )
    return _load_baysa_processed()


def _load_standardized_consolidated() -> pd.DataFrame:
    # Single-source-of-truth dataset for this deployment.
    return _load_baysa_processed()


def _filter_kpi_scope(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the contractual KPI filter.

    Rows outside contractual scope remain in the exported dataset for audit and
    traceability, but they must not contribute to dashboard metrics.
    """
    if df.empty or "in_contract_scope" not in df.columns:
        return df
    mask = df["in_contract_scope"].fillna(True).astype(bool)
    return df[mask].copy()


def _status_distribution(df: pd.DataFrame) -> Dict[str, int]:
    allowed = ["approved", "pending", "in_review", "rejected"]
    if df.empty or "status" not in df.columns:
        return {status: 0 for status in allowed}
    counts = df["status"].value_counts().to_dict()
    return {status: int(counts.get(status, 0)) for status in allowed}


def _build_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    total_rows = int(len(df))
    rows_in_scope = int(df.get("in_contract_scope", pd.Series(dtype="bool")).fillna(True).astype(bool).sum()) if total_rows else 0
    rows_out_of_scope = total_rows - rows_in_scope

    scoped = _filter_kpi_scope(df)
    distribution = _status_distribution(scoped)
    total_dossiers = int(len(scoped))
    approved = distribution["approved"]
    pending = distribution["pending"]
    in_review = distribution["in_review"]
    rejected = distribution["rejected"]
    peso_total_ton = round(float(scoped.get("weight_kg", pd.Series(dtype="float64")).sum() / 1000.0), 2)
    peso_aprobado_ton = round(
        float(scoped.loc[scoped.get("status") == "approved", "weight_kg"].sum() / 1000.0), 2
    ) if not scoped.empty and "status" in scoped.columns and "weight_kg" in scoped.columns else 0.0
    pct_approved = round((approved / total_dossiers * 100.0), 2) if total_dossiers else 0.0
    pct_peso_approved = round((peso_aprobado_ton / peso_total_ton * 100.0), 2) if peso_total_ton else 0.0

    return {
        "total_rows": total_rows,
        "rows_in_contract_scope": rows_in_scope,
        "rows_out_of_scope": rows_out_of_scope,
        "total_dossiers": total_dossiers,
        "approved_dossiers": approved,
        "pending_dossiers": pending,
        "in_review_dossiers": in_review,
        "rejected_dossiers": rejected,
        "status_distribution": distribution,
        # Backward-compatible keys still used by existing dashboard widgets.
        "dossiers_liberados": approved,
        "pct_liberado": pct_approved,
        "peso_total_ton": peso_total_ton,
        "peso_liberado_ton": peso_aprobado_ton,
        "pct_peso_liberado": pct_peso_approved,
    }


def global_dossier_kpis() -> Dict[str, Any]:
    return _build_kpis(_load_standardized_consolidated())


def dossier_kpis_by_contractor() -> Dict[str, Any]:
    df = _load_standardized_consolidated()
    if df.empty:
        return {}
    result: Dict[str, Any] = {}
    for contractor in sorted(df["contractor"].dropna().unique()):
        result[str(contractor)] = _build_kpis(df[df["contractor"] == contractor])
    return result


def dossier_kpis_by_stage(contractor: Optional[str] = None) -> Dict[str, Any]:
    df = _load_standardized_consolidated()
    if contractor:
        df = df[df["contractor"] == contractor.upper()]
    if df.empty or "stage" not in df.columns:
        return {}
    result: Dict[str, Any] = {}
    for stage in sorted(value for value in df["stage"].dropna().unique()):
        result[str(stage)] = _build_kpis(df[df["stage"] == stage])
    return result


def contractor_dossier_kpis(contractor: str) -> Dict[str, Any]:
    return _build_kpis(_load_standardized_contractor(contractor))


# ── Clean public API ──────────────────────────────────────────────────────────

def load_dossiers(contractor: str = "BAYSA") -> pd.DataFrame:
    """Load the standardised dossier dataset for *contractor*.

    Reads only ``data/processed/baysa_dossiers_clean.csv`` (produced by
    ``scripts/normalize_baysa_dataset.py``).

    The returned DataFrame always contains at minimum:
        contractor, stage, status, in_contract_scope, weight_kg

    Rows where ``in_contract_scope == False`` are kept so callers have full
    traceability of out-of-scope blocks.  Use ``compute_kpis()`` to obtain KPI
    counts filtered to the contractual scope only.

    Logs:
        rows_loaded       – total rows read
        rows_in_scope     – rows where in_contract_scope == True
        rows_out_of_scope – rows excluded by contractual scope
        status_distribution (in-scope) – {approved, pending, in_review, …}
    """
    if contractor.upper() != "BAYSA":
        raise ValueError(
            f"Unsupported contractor '{contractor}'. Only BAYSA is available in this environment."
        )

    df = _load_baysa_processed()

    rows_loaded = len(df)
    rows_in_scope = (
        int(df["in_contract_scope"].fillna(True).astype(bool).sum()) if rows_loaded else 0
    )
    log.info(
        "[load_dossiers] contractor=%s  rows_loaded=%d  rows_in_scope=%d  rows_out_of_scope=%d",
        contractor.upper(), rows_loaded, rows_in_scope, rows_loaded - rows_in_scope,
    )
    if rows_loaded:
        dist = _status_distribution(_filter_kpi_scope(df))
        log.info("[load_dossiers] status_distribution (in-scope): %s", dist)

    return df


def compute_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute contractual KPI metrics from a standardised dossier DataFrame.

    Only rows where ``in_contract_scope == True`` contribute to the KPI counts.
    Rows outside scope are tracked separately for reporting purposes.

    Args:
        df: DataFrame as returned by :func:`load_dossiers`.

    Returns a dict with keys:
        - ``total_dossiers``        – count of in-scope rows
        - ``approved_dossiers``     – status == "approved"
        - ``pending_dossiers``      – status == "pending"
        - ``in_review_dossiers``    – status == "in_review" (e.g. REVISIÓN INPROS)
        - ``rejected_dossiers``     – status == "rejected" (0 in current BAYSA data)
        - ``rows_in_contract_scope``– same as total_dossiers
        - ``rows_out_of_scope``     – rows excluded from KPIs (N° == "--")
        - ``total_rows``            – all rows before scope filter
        - ``status_distribution``   – {approved, pending, in_review, rejected}
        - Legacy backward-compat keys: ``dossiers_liberados``, ``pct_liberado``,
          ``peso_total_ton``, ``peso_liberado_ton``, ``pct_peso_liberado``

    Logs:
        status_distribution with approved/pending/in_review/rejected counts
    """
    kpis = _build_kpis(df)
    log.info(
        "[compute_kpis] total_rows=%d  in_scope=%d  out_of_scope=%d",
        kpis["total_rows"], kpis["rows_in_contract_scope"], kpis["rows_out_of_scope"],
    )
    log.info(
        "[compute_kpis] status_distribution: approved=%d  pending=%d  in_review=%d  rejected=%d",
        kpis["approved_dossiers"], kpis["pending_dossiers"],
        kpis["in_review_dossiers"], kpis["rejected_dossiers"],
    )
    return kpis
