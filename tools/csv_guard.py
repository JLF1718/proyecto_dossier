#!/usr/bin/env python3
"""Guarded CSV validation and patch application for dossier data."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class GuardError(Exception):
    """Raised when validation or patch application fails."""


@dataclass
class ApplySummary:
    updated: int
    inserted: int
    deleted: int
    backup_path: Path


def load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        with schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise GuardError(f"Schema not found: {schema_path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardError(f"Invalid schema JSON: {schema_path} ({exc})") from exc


def _is_blank(value: Any) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _coerce_boolean_value(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "t"}:
        return True
    if normalized in {"false", "0", "no", "n", "f"}:
        return False
    return None


def _coerce_column(
    df: pd.DataFrame,
    column: str,
    dtype_name: str,
    source_name: str,
) -> tuple[pd.Series, list[str]]:
    series = df[column]
    errors: list[str] = []

    if dtype_name == "string":
        return series.astype("string"), errors

    if dtype_name == "Int64":
        numeric = pd.to_numeric(series, errors="coerce")
        non_blank_mask = series.notna() & series.astype("string").str.strip().ne("")
        bad_mask = non_blank_mask & numeric.isna()
        for idx in df.index[bad_mask]:
            val = series.loc[idx]
            errors.append(
                f"{source_name}: row {idx + 2}, column '{column}' has invalid Int64 value: {val!r}"
            )
        return numeric.astype("Int64"), errors

    if dtype_name == "float64":
        numeric = pd.to_numeric(series, errors="coerce")
        non_blank_mask = series.notna() & series.astype("string").str.strip().ne("")
        bad_mask = non_blank_mask & numeric.isna()
        for idx in df.index[bad_mask]:
            val = series.loc[idx]
            errors.append(
                f"{source_name}: row {idx + 2}, column '{column}' has invalid float64 value: {val!r}"
            )
        return numeric.astype("float64"), errors

    if dtype_name == "boolean":
        coerced = series.map(_coerce_boolean_value).astype("boolean")
        non_blank_mask = series.notna() & series.astype("string").str.strip().ne("")
        bad_mask = non_blank_mask & coerced.isna()
        for idx in df.index[bad_mask]:
            val = series.loc[idx]
            errors.append(
                f"{source_name}: row {idx + 2}, column '{column}' has invalid boolean value: {val!r}"
            )
        return coerced, errors

    errors.append(f"Unsupported dtype in schema for column '{column}': {dtype_name}")
    return series, errors


def _coerce_dataframe(
    df: pd.DataFrame,
    dtypes: dict[str, str],
    source_name: str,
) -> tuple[pd.DataFrame, list[str]]:
    coerced = df.copy()
    errors: list[str] = []
    for column, dtype_name in dtypes.items():
        if column not in coerced.columns:
            continue
        coerced_column, col_errors = _coerce_column(coerced, column, dtype_name, source_name)
        coerced[column] = coerced_column
        errors.extend(col_errors)
    return coerced, errors


def validate_dataframe(df: pd.DataFrame, schema: dict[str, Any], source_name: str = "csv") -> pd.DataFrame:
    errors: list[str] = []
    dtypes: dict[str, str] = schema.get("dtypes", {})
    key_cols: list[str] = schema.get("key", [])
    required_cols: list[str] = schema.get("required", [])

    missing_schema_cols = [col for col in dtypes if col not in df.columns]
    if missing_schema_cols:
        for col in missing_schema_cols:
            errors.append(f"{source_name}: missing required schema column '{col}'")
        raise GuardError("\n".join(errors))

    coerced_df, coercion_errors = _coerce_dataframe(df, dtypes, source_name)
    errors.extend(coercion_errors)

    for col in required_cols:
        if col not in coerced_df.columns:
            errors.append(f"{source_name}: missing required column '{col}'")
            continue
        null_mask = coerced_df[col].isna()
        for idx in coerced_df.index[null_mask]:
            errors.append(f"{source_name}: row {idx + 2}, column '{col}' is required and cannot be null")

    if "estatus" in coerced_df.columns:
        allowed = set(schema.get("allowed", {}).get("estatus", []))
        invalid_mask = coerced_df["estatus"].notna() & ~coerced_df["estatus"].isin(allowed)
        for idx in coerced_df.index[invalid_mask]:
            val = coerced_df.loc[idx, "estatus"]
            errors.append(
                f"{source_name}: row {idx + 2}, column 'estatus' has invalid value {val!r}; "
                f"allowed={sorted(allowed)}"
            )

    if key_cols:
        dup_mask = coerced_df.duplicated(subset=key_cols, keep=False)
        for idx in coerced_df.index[dup_mask]:
            key_values = {k: coerced_df.loc[idx, k] for k in key_cols}
            errors.append(f"{source_name}: row {idx + 2} has duplicate key {key_values}")

    if errors:
        raise GuardError("\n".join(errors))

    return coerced_df


def validate_csv(csv_path: Path, schema_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path, keep_default_na=False)
    except FileNotFoundError as exc:
        raise GuardError(f"CSV not found: {csv_path}") from exc

    schema = load_schema(schema_path)
    return validate_dataframe(df, schema, source_name=str(csv_path))


def _build_key_mask(df: pd.DataFrame, key_cols: list[str], key_values: dict[str, Any]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for col in key_cols:
        val = key_values[col]
        if pd.isna(val):
            mask &= df[col].isna()
        else:
            mask &= df[col] == val
    return mask


def _ensure_patch_shape(patch_df: pd.DataFrame, schema: dict[str, Any]) -> None:
    key_cols: list[str] = schema.get("key", [])
    required_patch_cols = ["op", *key_cols]
    missing = [col for col in required_patch_cols if col not in patch_df.columns]
    if missing:
        raise GuardError(f"Patch missing required columns: {missing}")

    allowed_cols = {"op", *schema.get("dtypes", {}).keys()}
    unknown_cols = [col for col in patch_df.columns if col not in allowed_cols]
    if unknown_cols:
        raise GuardError(f"Patch has unknown columns not in schema: {unknown_cols}")


def apply_patch_csv(csv_path: Path, schema_path: Path, patch_path: Path) -> ApplySummary:
    schema = load_schema(schema_path)

    try:
        csv_df_raw = pd.read_csv(csv_path, keep_default_na=False)
    except FileNotFoundError as exc:
        raise GuardError(f"CSV not found: {csv_path}") from exc

    try:
        patch_df_raw = pd.read_csv(patch_path, keep_default_na=False)
    except FileNotFoundError as exc:
        raise GuardError(f"Patch not found: {patch_path}") from exc

    base_df = validate_dataframe(csv_df_raw, schema, source_name=str(csv_path))
    _ensure_patch_shape(patch_df_raw, schema)

    patch_dtypes = {col: dtype for col, dtype in schema.get("dtypes", {}).items() if col in patch_df_raw.columns}
    patch_df, patch_type_errors = _coerce_dataframe(patch_df_raw.copy(), patch_dtypes, source_name=str(patch_path))
    if patch_type_errors:
        raise GuardError("\n".join(patch_type_errors))

    key_cols: list[str] = schema.get("key", [])
    editable_cols = [col for col in patch_df.columns if col not in {"op", *key_cols}]

    op_series = patch_df["op"].astype("string").str.strip().str.upper()
    invalid_ops = patch_df.index[~op_series.isin(["UPSERT", "DELETE"])]
    if len(invalid_ops) > 0:
        msgs = [
            f"{patch_path}: row {idx + 2}, column 'op' must be UPSERT or DELETE"
            for idx in invalid_ops
        ]
        raise GuardError("\n".join(msgs))

    for col in key_cols:
        null_mask = patch_df[col].isna()
        if null_mask.any():
            msgs = [f"{patch_path}: row {idx + 2}, key column '{col}' cannot be null" for idx in patch_df.index[null_mask]]
            raise GuardError("\n".join(msgs))

    working_df = base_df.copy()
    updated = 0
    inserted = 0
    deleted = 0
    apply_errors: list[str] = []

    for idx, row in patch_df.iterrows():
        op = str(op_series.loc[idx])
        key_values = {col: row[col] for col in key_cols}
        key_mask = _build_key_mask(working_df, key_cols, key_values)
        match_indices = working_df.index[key_mask]

        if op == "DELETE":
            if len(match_indices) == 0:
                apply_errors.append(
                    f"{patch_path}: row {idx + 2}, DELETE key not found: {key_values}"
                )
                continue
            working_df = working_df.drop(index=match_indices)
            deleted += len(match_indices)
            continue

        updates: dict[str, Any] = {}
        for col in editable_cols:
            val = row[col]
            if pd.isna(val):
                continue
            updates[col] = val

        numero_val = row.get("numero", pd.NA)
        if _is_blank(numero_val):
            updates["in_contract_scope_bool"] = False

        if len(match_indices) == 0:
            new_row = {col: pd.NA for col in working_df.columns}
            for col in key_cols:
                new_row[col] = row[col]
            for col, val in updates.items():
                new_row[col] = val
            working_df.loc[len(working_df)] = new_row
            inserted += 1
        else:
            target_idx = match_indices[0]
            for col, val in updates.items():
                working_df.at[target_idx, col] = val
            updated += 1

    if apply_errors:
        raise GuardError("\n".join(apply_errors))

    final_df = validate_dataframe(working_df, schema, source_name="result")

    backup_dir = csv_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    shutil.copy2(csv_path, backup_path)

    tmp_fd, tmp_path_str = tempfile.mkstemp(
        prefix=f"{csv_path.stem}_",
        suffix=".tmp",
        dir=str(csv_path.parent),
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)

    try:
        final_df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, csv_path)
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise GuardError(f"Atomic write failed: {exc}") from exc

    return ApplySummary(updated=updated, inserted=inserted, deleted=deleted, backup_path=backup_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guarded CSV validator and patch applier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate CSV against schema")
    validate_parser.add_argument("--csv", required=True, type=Path, help="Path to CSV file")
    validate_parser.add_argument("--schema", required=True, type=Path, help="Path to schema JSON")

    apply_parser = subparsers.add_parser("apply", help="Apply patch file to CSV")
    apply_parser.add_argument("--csv", required=True, type=Path, help="Path to CSV file")
    apply_parser.add_argument("--schema", required=True, type=Path, help="Path to schema JSON")
    apply_parser.add_argument("--patch", required=True, type=Path, help="Path to patch CSV")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            validated = validate_csv(args.csv, args.schema)
            print(f"Validation OK: rows={len(validated)}")
            return 0

        if args.command == "apply":
            summary = apply_patch_csv(args.csv, args.schema, args.patch)
            print(
                "Apply OK: "
                f"updated={summary.updated} inserted={summary.inserted} "
                f"deleted={summary.deleted} backup={summary.backup_path}"
            )
            return 0

        parser.error("Unknown command")
        return 2
    except GuardError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
