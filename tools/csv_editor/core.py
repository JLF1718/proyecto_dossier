from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from tools.csv_guard import load_schema, validate_csv


ALLOWED_ESTATUS = {"approved", "pending", "in_review"}
IN_REVIEW_VARIANTS = {
    "in review",
    "in-review",
    "in_review",
    "en revision",
    "en revisión",
    "revision",
    "revisión",
    "en revision inpros",
    "en revisión inpros",
    "revision inpros",
    "revisión inpros",
}


class CsvEditorError(Exception):
    """Raised when local CSV edit operations fail."""


def load_csv(csv_path: Path) -> pd.DataFrame:
    """Load CSV with consistent NA handling used by guard tooling."""
    try:
        return pd.read_csv(csv_path, keep_default_na=False)
    except FileNotFoundError as exc:
        raise CsvEditorError(f"CSV not found: {csv_path}") from exc


def get_row_by_bloque(df: pd.DataFrame, bloque: str) -> tuple[int, pd.Series]:
    """Return exactly one row by unique bloque."""
    if "bloque" not in df.columns:
        raise CsvEditorError("Column 'bloque' is required")

    matches = df.index[df["bloque"].astype("string") == str(bloque)]
    if len(matches) == 0:
        raise CsvEditorError(f"Bloque not found: {bloque}")
    if len(matches) > 1:
        raise CsvEditorError(f"Duplicate bloque found: {bloque}")

    idx = int(matches[0])
    return idx, df.loc[idx]


def _coerce_changed_values(changes: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    schema = load_schema(schema_path)
    dtypes = schema.get("dtypes", {})
    coerced: dict[str, Any] = {}

    for field, value in changes.items():
        dtype_name = dtypes.get(field)
        if dtype_name is None:
            coerced[field] = value
            continue

        if value is None:
            coerced[field] = pd.NA
            continue

        raw = str(value).strip()
        if raw == "":
            coerced[field] = pd.NA
            continue

        if dtype_name == "string":
            coerced[field] = raw
        elif dtype_name == "Int64":
            try:
                coerced[field] = int(raw)
            except ValueError as exc:
                raise CsvEditorError(f"Invalid Int64 value for '{field}': {value!r}") from exc
        elif dtype_name == "float64":
            try:
                coerced[field] = float(raw)
            except ValueError as exc:
                raise CsvEditorError(f"Invalid float64 value for '{field}': {value!r}") from exc
        elif dtype_name == "boolean":
            normalized = raw.lower()
            if normalized in {"true", "1", "yes", "y", "t"}:
                coerced[field] = True
            elif normalized in {"false", "0", "no", "n", "f"}:
                coerced[field] = False
            else:
                raise CsvEditorError(f"Invalid boolean value for '{field}': {value!r}")
        else:
            coerced[field] = value

    return coerced


def _validate_and_normalize_estatus(changes: dict[str, Any]) -> dict[str, Any]:
    if "estatus" not in changes:
        return changes

    value = changes["estatus"]
    if pd.isna(value):
        raise CsvEditorError("Invalid estatus: expected approved|pending|in_review")

    normalized = str(value).strip().lower()
    if normalized in IN_REVIEW_VARIANTS:
        normalized = "in_review"

    if normalized not in ALLOWED_ESTATUS:
        raise CsvEditorError(
            f"Invalid estatus '{value}'. Allowed values: approved|pending|in_review"
        )

    updated = dict(changes)
    updated["estatus"] = normalized
    return updated


def apply_changes_by_bloque(
    csv_path: Path,
    schema_path: Path,
    bloque: str,
    changes: dict[str, Any],
    *,
    validate_fn: Callable[[Path, Path], pd.DataFrame] | None = None,
) -> Path:
    """Apply field updates to one unique bloque with backup, atomic write and post-validation."""
    if not changes:
        raise CsvEditorError("No changes to apply")

    df = load_csv(csv_path)
    row_idx, _ = get_row_by_bloque(df, bloque)

    unknown_fields = [field for field in changes if field not in df.columns]
    if unknown_fields:
        raise CsvEditorError(f"Unknown fields: {unknown_fields}")

    coerced_changes = _coerce_changed_values(changes, schema_path)
    coerced_changes = _validate_and_normalize_estatus(coerced_changes)
    updated_df = df.copy()
    for field, value in coerced_changes.items():
        updated_df.at[row_idx, field] = value

    backup_dir = csv_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.csv"
    shutil.copy2(csv_path, backup_path)

    tmp_fd, tmp_path_str = tempfile.mkstemp(
        prefix=f"{csv_path.stem}_",
        suffix=".tmp",
        dir=str(csv_path.parent),
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)

    try:
        updated_df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, csv_path)
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise CsvEditorError(f"Atomic write failed: {exc}") from exc

    validator = validate_fn or validate_csv
    try:
        validator(csv_path, schema_path)
    except Exception as exc:
        shutil.copy2(backup_path, csv_path)
        raise CsvEditorError(f"Validation failed after edit, restored backup: {exc}") from exc

    return backup_path
