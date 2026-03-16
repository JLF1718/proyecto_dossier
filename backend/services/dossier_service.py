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

_OPEN_BACKLOG_STATUSES = {"pending", "in_review"}

_STAGE_ORDER = [
    "Stage 1",
    "Stage 2",
    "Stage 3",
    "Stage 4",
    "General Information",
    "Protective Coatings",
]

_FAMILY_ORDER = ["PRO", "SUE", "SHARED"]

_WEIGHT_AUDIT_DELTA_WARNING_KG = 100000.0


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


def _normalise_week_value(value: object) -> Optional[int]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>", "--"}:
        return None
    numeric = pd.to_numeric(text, errors="coerce")
    if pd.isna(numeric):
        return None
    return int(numeric)


def _normalise_week_series(series: pd.Series) -> pd.Series:
    return series.apply(_normalise_week_value).astype("Int64")


def _normalise_bloque(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.upper()


def _derive_stage_category(df: pd.DataFrame) -> pd.Series:
    bloque = _normalise_bloque(df.get("bloque", pd.Series(index=df.index, dtype="object")))
    stage_text = df.get("stage", pd.Series(index=df.index, dtype="object")).astype(str)
    stage_num = pd.to_numeric(stage_text.str.extract(r"(\d+)")[0], errors="coerce")

    stage = pd.Series("", index=df.index, dtype="object")
    stage.loc[bloque.eq("DOSSIER GENERAL") | bloque.str.contains("GENERAL", na=False)] = "General Information"
    stage.loc[bloque.eq("DOSSIER PINTURA") | bloque.str.contains("PINTURA|COAT|PAINT", na=False)] = "Protective Coatings"

    numeric_mask = stage.eq("") & stage_num.notna()
    stage.loc[numeric_mask] = "Stage " + stage_num.loc[numeric_mask].astype(int).astype(str)
    return stage


def _derive_building_family(df: pd.DataFrame) -> pd.Series:
    bloque = _normalise_bloque(df.get("bloque", pd.Series(index=df.index, dtype="object")))

    family = pd.Series("SHARED", index=df.index, dtype="object")
    family.loc[bloque.str.startswith("PRO")] = "PRO"
    family.loc[bloque.str.startswith("SUE")] = "SUE"
    family.loc[bloque.str.startswith("DOSSIER")] = "SHARED"
    return family


def _enrich_management_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["stage_category"] = pd.Series(dtype="object")
        out["building_family"] = pd.Series(dtype="object")
        return out

    out = df.copy()
    out["stage_category"] = _derive_stage_category(out)
    out["building_family"] = _derive_building_family(out)
    return out


def _resolve_analysis_week(df: pd.DataFrame, selected_week: object = None) -> Optional[int]:
    selected = _normalise_week_value(selected_week)
    if selected is not None:
        return selected

    candidates: list[int] = []
    for column in ("release_week", "reference_week"):
        if column not in df.columns:
            continue
        weeks = _normalise_week_series(df[column]).dropna()
        if not weeks.empty:
            candidates.append(int(weeks.max()))
    return max(candidates) if candidates else None


def _build_weekly_release_series(df: pd.DataFrame, analysis_week: Optional[int] = None) -> pd.DataFrame:
    columns = ["week", "released_dossiers", "released_weight_t"]
    scoped = _filter_kpi_scope(df)
    if scoped.empty or "status" not in scoped.columns:
        return pd.DataFrame(columns=columns)

    approved = scoped[scoped["status"] == "approved"].copy()
    if approved.empty:
        start_week = analysis_week - 1 if analysis_week is not None else None
        end_week = analysis_week
        if start_week is None or end_week is None:
            return pd.DataFrame(columns=columns)
        weeks = list(range(start_week, end_week + 1))
        return pd.DataFrame(
            {
                "week": weeks,
                "released_dossiers": [0] * len(weeks),
                "released_weight_t": [0.0] * len(weeks),
            }
        )

    approved["release_week"] = _normalise_week_series(
        approved.get("release_week", pd.Series(index=approved.index, dtype="object"))
    )
    approved = approved.dropna(subset=["release_week"])
    if approved.empty:
        start_week = analysis_week - 1 if analysis_week is not None else None
        end_week = analysis_week
        if start_week is None or end_week is None:
            return pd.DataFrame(columns=columns)
        weeks = list(range(start_week, end_week + 1))
        return pd.DataFrame(
            {
                "week": weeks,
                "released_dossiers": [0] * len(weeks),
                "released_weight_t": [0.0] * len(weeks),
            }
        )

    grouped = (
        approved.groupby("release_week", dropna=True)
        .agg(
            released_dossiers=("status", "size"),
            released_weight_t=("weight_kg", lambda s: float(s.sum() / 1000.0)),
        )
        .sort_index()
    )
    grouped.index = grouped.index.astype(int)

    start_week = int(grouped.index.min())
    if analysis_week is not None:
        start_week = min(start_week, analysis_week - 1)
        end_week = max(int(grouped.index.max()), analysis_week)
    else:
        end_week = int(grouped.index.max())

    complete_index = pd.Index(range(start_week, end_week + 1), name="week")
    grouped = grouped.reindex(complete_index, fill_value=0).reset_index()
    grouped["released_dossiers"] = grouped["released_dossiers"].astype(int)
    grouped["released_weight_t"] = grouped["released_weight_t"].astype(float).round(2)
    return grouped[columns]


def _build_cumulative_weekly_growth(release_series: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "week",
        "released_dossiers",
        "released_weight_t",
        "cumulative_approved_dossiers",
        "cumulative_released_weight_t",
    ]
    if release_series.empty:
        return pd.DataFrame(columns=columns)

    out = release_series.copy().sort_values("week").reset_index(drop=True)
    out["cumulative_approved_dossiers"] = out["released_dossiers"].cumsum().astype(int)
    out["cumulative_released_weight_t"] = out["released_weight_t"].cumsum().round(2)
    return out[columns]


def _build_backlog_aging_frame(df: pd.DataFrame, analysis_week: Optional[int]) -> pd.DataFrame:
    columns = [
        "stage_category",
        "building_family",
        "open_backlog",
        "pending_dossiers",
        "in_review_dossiers",
        "rows_without_reference_week",
        "oldest_reference_week",
        "max_age_weeks",
        "avg_age_weeks",
    ]
    scoped = _filter_kpi_scope(_enrich_management_dimensions(df))
    if scoped.empty or analysis_week is None:
        return pd.DataFrame(columns=columns)

    backlog = scoped[scoped.get("status").isin(_OPEN_BACKLOG_STATUSES)].copy()
    if backlog.empty:
        return pd.DataFrame(columns=columns)

    backlog["reference_week"] = _normalise_week_series(
        backlog.get("reference_week", pd.Series(index=backlog.index, dtype="object"))
    )
    backlog["age_weeks"] = (analysis_week - backlog["reference_week"]).where(backlog["reference_week"].notna())

    grouped = (
        backlog.groupby(["stage_category", "building_family"], dropna=False)
        .agg(
            open_backlog=("status", "size"),
            pending_dossiers=("status", lambda s: int((s == "pending").sum())),
            in_review_dossiers=("status", lambda s: int((s == "in_review").sum())),
            rows_without_reference_week=("reference_week", lambda s: int(s.isna().sum())),
            oldest_reference_week=("reference_week", "min"),
            max_age_weeks=("age_weeks", "max"),
            avg_age_weeks=("age_weeks", "mean"),
        )
        .reset_index()
    )
    grouped["oldest_reference_week"] = grouped["oldest_reference_week"].astype("Int64")
    grouped["max_age_weeks"] = grouped["max_age_weeks"].round(0).astype("Int64")
    grouped["avg_age_weeks"] = grouped["avg_age_weeks"].round(1)
    grouped = grouped.sort_values(
        ["max_age_weeks", "open_backlog", "stage_category", "building_family"],
        ascending=[False, False, True, True],
        na_position="last",
    ).reset_index(drop=True)
    return grouped[columns]


def _detect_stagnant_groups(df: pd.DataFrame, analysis_week: Optional[int]) -> pd.DataFrame:
    columns = [
        "stage_category",
        "building_family",
        "open_backlog",
        "oldest_reference_week",
        "max_age_weeks",
        "released_this_week",
        "released_previous_week",
        "cumulative_approved_current",
        "cumulative_approved_previous",
        "cumulative_approved_growth",
        "cumulative_released_weight_t_current",
        "cumulative_released_weight_t_previous",
        "cumulative_released_weight_t_growth",
    ]
    backlog_groups = _build_backlog_aging_frame(df, analysis_week)
    if backlog_groups.empty or analysis_week is None:
        return pd.DataFrame(columns=columns)

    previous_week = analysis_week - 1
    scoped = _filter_kpi_scope(_enrich_management_dimensions(df))
    approved = scoped[scoped.get("status") == "approved"].copy()

    if approved.empty:
        out = backlog_groups[["stage_category", "building_family", "open_backlog", "oldest_reference_week", "max_age_weeks"]].copy()
        out["released_this_week"] = 0
        out["released_previous_week"] = 0
        out["cumulative_approved_current"] = 0
        out["cumulative_approved_previous"] = 0
        out["cumulative_approved_growth"] = 0
        out["cumulative_released_weight_t_current"] = 0.0
        out["cumulative_released_weight_t_previous"] = 0.0
        out["cumulative_released_weight_t_growth"] = 0.0
        return out[columns]

    approved["release_week"] = _normalise_week_series(
        approved.get("release_week", pd.Series(index=approved.index, dtype="object"))
    )
    approved = approved.dropna(subset=["release_week"])

    group_keys = ["stage_category", "building_family"]
    if approved.empty:
        metrics = pd.DataFrame(columns=group_keys)
    else:
        weekly_grouped = (
            approved.groupby(group_keys + ["release_week"], dropna=False)
            .agg(
                released_dossiers=("status", "size"),
                released_weight_t=("weight_kg", lambda s: float(s.sum() / 1000.0)),
            )
            .reset_index()
        )

        current = (
            weekly_grouped[weekly_grouped["release_week"] == analysis_week]
            .groupby(group_keys, dropna=False)
            .agg(
                released_this_week=("released_dossiers", "sum"),
            )
        )
        previous = (
            weekly_grouped[weekly_grouped["release_week"] == previous_week]
            .groupby(group_keys, dropna=False)
            .agg(
                released_previous_week=("released_dossiers", "sum"),
            )
        )
        current_cumulative = (
            weekly_grouped[weekly_grouped["release_week"] <= analysis_week]
            .groupby(group_keys, dropna=False)
            .agg(
                cumulative_approved_current=("released_dossiers", "sum"),
                cumulative_released_weight_t_current=("released_weight_t", "sum"),
            )
        )
        previous_cumulative = (
            weekly_grouped[weekly_grouped["release_week"] <= previous_week]
            .groupby(group_keys, dropna=False)
            .agg(
                cumulative_approved_previous=("released_dossiers", "sum"),
                cumulative_released_weight_t_previous=("released_weight_t", "sum"),
            )
        )
        metrics = current.join(previous, how="outer").join(current_cumulative, how="outer").join(previous_cumulative, how="outer")
        metrics = metrics.reset_index()

    out = backlog_groups[["stage_category", "building_family", "open_backlog", "oldest_reference_week", "max_age_weeks"]].merge(
        metrics,
        on=["stage_category", "building_family"],
        how="left",
    )
    for column in [
        "released_this_week",
        "released_previous_week",
        "cumulative_approved_current",
        "cumulative_approved_previous",
    ]:
        out[column] = out[column].fillna(0).astype(int)

    for column in [
        "cumulative_released_weight_t_current",
        "cumulative_released_weight_t_previous",
    ]:
        out[column] = out[column].fillna(0.0).astype(float).round(2)

    out["cumulative_approved_growth"] = out["cumulative_approved_current"] - out["cumulative_approved_previous"]
    out["cumulative_released_weight_t_growth"] = (
        out["cumulative_released_weight_t_current"] - out["cumulative_released_weight_t_previous"]
    ).round(2)
    out = out[
        (out["open_backlog"] > 0)
        & (out["released_this_week"] == 0)
        & (out["cumulative_approved_growth"] == 0)
        & (out["cumulative_released_weight_t_growth"] == 0)
    ].copy()
    out = out.sort_values(
        ["max_age_weeks", "open_backlog", "stage_category", "building_family"],
        ascending=[False, False, True, True],
        na_position="last",
    ).reset_index(drop=True)
    return out[columns]


def _serialise_weekly_records(df: pd.DataFrame) -> list[Dict[str, Any]]:
    if df.empty:
        return []
    clean = df.where(pd.notna(df), None).copy()
    return clean.to_dict(orient="records")


def _ensure_standardized_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    required_columns = {"status", "in_contract_scope", "weight_kg", "reference_week", "release_week", "bloque"}
    if required_columns.issubset(df.columns):
        return df.copy()

    raw_columns = {"estatus", "in_contract_scope", "peso_dossier_kg", "hito_semana", "semana_liberacion_dossier", "bloque"}
    if raw_columns.intersection(df.columns):
        return _standardize_baysa_processed(df)

    return df.copy()


def build_weekly_management_payload(df: pd.DataFrame, selected_week: object = None) -> Dict[str, Any]:
    df = _ensure_standardized_frame(df)
    analysis_week = _resolve_analysis_week(df, selected_week=selected_week)
    previous_week = analysis_week - 1 if analysis_week is not None else None

    release_series = _build_weekly_release_series(df, analysis_week=analysis_week)
    cumulative_series = _build_cumulative_weekly_growth(release_series)
    backlog_aging = _build_backlog_aging_frame(df, analysis_week)
    stagnant_groups = _detect_stagnant_groups(df, analysis_week)

    release_lookup = release_series.set_index("week") if not release_series.empty else pd.DataFrame()
    cumulative_lookup = cumulative_series.set_index("week") if not cumulative_series.empty else pd.DataFrame()

    def _series_value(frame: pd.DataFrame, week: Optional[int], column: str, default: float = 0.0) -> float:
        if week is None or frame.empty or week not in frame.index or column not in frame.columns:
            return default
        value = frame.at[week, column]
        if pd.isna(value):
            return default
        return float(value)

    released_this_week = int(_series_value(release_lookup, analysis_week, "released_dossiers", default=0.0))
    released_previous_week = int(_series_value(release_lookup, previous_week, "released_dossiers", default=0.0))
    released_weight_this_week = round(_series_value(release_lookup, analysis_week, "released_weight_t", default=0.0), 2)
    released_weight_previous_week = round(_series_value(release_lookup, previous_week, "released_weight_t", default=0.0), 2)
    cumulative_approved_current = int(
        _series_value(cumulative_lookup, analysis_week, "cumulative_approved_dossiers", default=0.0)
    )
    cumulative_approved_previous = int(
        _series_value(cumulative_lookup, previous_week, "cumulative_approved_dossiers", default=0.0)
    )
    cumulative_weight_current = round(
        _series_value(cumulative_lookup, analysis_week, "cumulative_released_weight_t", default=0.0), 2
    )
    cumulative_weight_previous = round(
        _series_value(cumulative_lookup, previous_week, "cumulative_released_weight_t", default=0.0), 2
    )

    total_open_backlog = int(backlog_aging["open_backlog"].sum()) if not backlog_aging.empty else 0
    oldest_reference_week = None
    max_age_weeks = None
    if not backlog_aging.empty:
        valid_oldest = backlog_aging["oldest_reference_week"].dropna()
        valid_ages = backlog_aging["max_age_weeks"].dropna()
        if not valid_oldest.empty:
            oldest_reference_week = int(valid_oldest.min())
        if not valid_ages.empty:
            max_age_weeks = int(valid_ages.max())

    stagnant_open_backlog = int(stagnant_groups["open_backlog"].sum()) if not stagnant_groups.empty else 0

    return {
        "analysis_week": analysis_week,
        "previous_week": previous_week,
        "delta_kpis": {
            "analysis_week": analysis_week,
            "previous_week": previous_week,
            "released_this_week": released_this_week,
            "released_weight_t_this_week": released_weight_this_week,
            "change_vs_previous_week": released_this_week - released_previous_week,
            "weight_change_t_vs_previous_week": round(released_weight_this_week - released_weight_previous_week, 2),
        },
        "weekly_comparison": {
            "current_vs_previous": {
                "current_week": analysis_week,
                "previous_week": previous_week,
                "current_released_dossiers": released_this_week,
                "previous_released_dossiers": released_previous_week,
                "current_released_weight_t": released_weight_this_week,
                "previous_released_weight_t": released_weight_previous_week,
                "cumulative_approved_current": cumulative_approved_current,
                "cumulative_approved_previous": cumulative_approved_previous,
                "cumulative_approved_growth": cumulative_approved_current - cumulative_approved_previous,
                "cumulative_released_weight_t_current": cumulative_weight_current,
                "cumulative_released_weight_t_previous": cumulative_weight_previous,
                "cumulative_released_weight_t_growth": round(cumulative_weight_current - cumulative_weight_previous, 2),
            },
            "release_series": _serialise_weekly_records(release_series),
            "cumulative_series": _serialise_weekly_records(cumulative_series),
        },
        "backlog_aging_summary": {
            "analysis_week": analysis_week,
            "total_open_backlog": total_open_backlog,
            "oldest_reference_week": oldest_reference_week,
            "max_age_weeks": max_age_weeks,
            "groups": _serialise_weekly_records(backlog_aging),
        },
        "stagnant_groups_summary": {
            "analysis_week": analysis_week,
            "stagnant_groups": int(len(stagnant_groups)),
            "total_open_backlog": stagnant_open_backlog,
            "groups": _serialise_weekly_records(stagnant_groups),
        },
    }


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

    weight_dossier_source = df.get("peso_dossier_kg", pd.Series(index=df.index, dtype="float64"))
    weight_block_source = df.get("peso_bloque_kg", pd.Series(index=df.index, dtype="float64"))

    out["weight_dossier_kg"] = _normalise_weight(weight_dossier_source)
    out["weight_block_kg"] = _normalise_weight(weight_block_source)
    # Keep backward-compatible alias used by weekly payload internals.
    out["weight_kg"] = out["weight_dossier_kg"]

    out["reference_week"] = _normalise_week_series(
        df.get("hito_semana", pd.Series(index=df.index, dtype="object"))
    )
    out["release_week"] = _normalise_week_series(
        df.get("semana_liberacion_dossier", pd.Series(index=df.index, dtype="object"))
    )
    out["bloque"] = _normalise_bloque(df.get("bloque", pd.Series(index=df.index, dtype="object")))
    out.attrs["weight_source_column"] = "peso_dossier_kg"
    out.attrs["has_weight_block_source"] = "peso_bloque_kg" in df.columns
    out.attrs["has_weight_dossier_source"] = "peso_dossier_kg" in df.columns

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
    legacy_weight = _normalise_weight(df.get("PESO", pd.Series(index=df.index, dtype="float64")))
    out["weight_kg"] = legacy_weight
    out["weight_dossier_kg"] = legacy_weight
    out["weight_block_kg"] = legacy_weight
    out["reference_week"] = _normalise_week_series(
        df.get("HITO_SEMANA", pd.Series(index=df.index, dtype="object"))
    )
    out["release_week"] = _normalise_week_series(
        df.get("SEMANA_LIBERACION_DOSSIER", pd.Series(index=df.index, dtype="object"))
    )
    out["bloque"] = _normalise_bloque(df.get("BLOQUE", pd.Series(index=df.index, dtype="object")))
    out.attrs["weight_source_column"] = "PESO"
    out.attrs["has_weight_block_source"] = False
    out.attrs["has_weight_dossier_source"] = True
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


def _build_weight_audit(df: pd.DataFrame) -> Dict[str, Any]:
    has_block_source = bool(df.attrs.get("has_weight_block_source", False))
    weight_block_column = "weight_block_kg" if has_block_source and "weight_block_kg" in df.columns else "weight_kg"
    weight_dossier_column = "weight_dossier_kg" if "weight_dossier_kg" in df.columns else "weight_kg"
    kpi_source_column = "peso_bloque_kg" if weight_block_column == "weight_block_kg" else str(df.attrs.get("weight_source_column", "weight_kg"))

    scoped = _filter_kpi_scope(df)
    raw_total_weight_kg = float(df.get(weight_block_column, pd.Series(dtype="float64")).sum())
    in_scope_total_weight_kg = float(scoped.get(weight_block_column, pd.Series(dtype="float64")).sum())
    displayed_total_weight_t = in_scope_total_weight_kg / 1000.0

    in_scope_dossier_kg = float(scoped.get(weight_dossier_column, pd.Series(dtype="float64")).sum())
    in_scope_block_kg = float(scoped.get(weight_block_column, pd.Series(dtype="float64")).sum())
    in_scope_block_vs_dossier_delta_kg = in_scope_block_kg - in_scope_dossier_kg
    warning_triggered = abs(in_scope_block_vs_dossier_delta_kg) >= _WEIGHT_AUDIT_DELTA_WARNING_KG

    return {
        "weight_source_column": kpi_source_column,
        "kpi_weight_column": weight_block_column,
        "weight_scope_filter": "in_contract_scope == True",
        "raw_total_weight_kg": round(raw_total_weight_kg, 2),
        "in_scope_total_weight_kg": round(in_scope_total_weight_kg, 2),
        "in_scope_weight_dossier_kg": round(in_scope_dossier_kg, 2),
        "in_scope_weight_block_kg": round(in_scope_block_kg, 2),
        "in_scope_block_vs_dossier_delta_kg": round(in_scope_block_vs_dossier_delta_kg, 2),
        "delta_warning_threshold_kg": round(_WEIGHT_AUDIT_DELTA_WARNING_KG, 2),
        "delta_warning_triggered": warning_triggered,
        "displayed_total_weight_t": round(displayed_total_weight_t, 2),
        "displayed_weight_unit": "t",
    }


def _build_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    total_rows = int(len(df))
    rows_in_scope = int(df.get("in_contract_scope", pd.Series(dtype="bool")).fillna(True).astype(bool).sum()) if total_rows else 0
    rows_out_of_scope = total_rows - rows_in_scope

    scoped = _filter_kpi_scope(df)
    weight_audit = _build_weight_audit(df)
    distribution = _status_distribution(scoped)
    total_dossiers = int(len(scoped))
    approved = distribution["approved"]
    pending = distribution["pending"]
    in_review = distribution["in_review"]
    rejected = distribution["rejected"]
    peso_total_ton = float(weight_audit["displayed_total_weight_t"])

    kpi_weight_column = str(weight_audit.get("kpi_weight_column", "weight_kg"))
    approved_mask = scoped.get("status") == "approved" if "status" in scoped.columns else pd.Series(False, index=scoped.index)
    peso_aprobado_ton = round(
        float(scoped.loc[approved_mask, kpi_weight_column].sum() / 1000.0), 2
    ) if not scoped.empty and "status" in scoped.columns and kpi_weight_column in scoped.columns else 0.0
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
        "weight_audit": weight_audit,
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
        contractor, stage, status, in_contract_scope, weight_kg,
        reference_week, release_week, bloque

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
    standard_df = _ensure_standardized_frame(df)
    kpis = _build_kpis(standard_df)
    log.info(
        "[compute_kpis] total_rows=%d  in_scope=%d  out_of_scope=%d",
        kpis["total_rows"], kpis["rows_in_contract_scope"], kpis["rows_out_of_scope"],
    )
    log.info(
        "[compute_kpis] status_distribution: approved=%d  pending=%d  in_review=%d  rejected=%d",
        kpis["approved_dossiers"], kpis["pending_dossiers"],
        kpis["in_review_dossiers"], kpis["rejected_dossiers"],
    )
    audit = kpis.get("weight_audit", {})
    log.info(
        "[compute_kpis] weight_audit source=%s scope=%s raw_kg=%.2f in_scope_kg=%.2f displayed_t=%.2f",
        audit.get("weight_source_column", "weight_kg"),
        audit.get("weight_scope_filter", "in_contract_scope == True"),
        float(audit.get("raw_total_weight_kg", 0.0)),
        float(audit.get("in_scope_total_weight_kg", 0.0)),
        float(audit.get("displayed_total_weight_t", 0.0)),
    )
    if bool(audit.get("delta_warning_triggered", False)):
        log.warning(
            "[compute_kpis] WEIGHT_AUDIT_WARNING delta_kg=%.2f threshold_kg=%.2f (block vs dossier in-scope)",
            float(audit.get("in_scope_block_vs_dossier_delta_kg", 0.0)),
            float(audit.get("delta_warning_threshold_kg", _WEIGHT_AUDIT_DELTA_WARNING_KG)),
        )
    return kpis


def weekly_management_payload(contractor: str = "BAYSA", selected_week: object = None) -> Dict[str, Any]:
    """Return the v0.3 weekly management payload for the active BAYSA dataset."""
    return build_weekly_management_payload(load_dossiers(contractor), selected_week=selected_week)
