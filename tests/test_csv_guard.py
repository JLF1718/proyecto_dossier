from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tools.csv_guard import GuardError, apply_patch_csv, validate_csv


SCHEMA = {
    "key": ["contractor", "numero", "numero_fase", "etapa", "semana_bloque_peso"],
    "required": [
        "contractor",
        "numero",
        "numero_fase",
        "etapa",
        "semana_bloque_peso",
        "hito",
        "peso_dossier_kg",
        "total_piezas",
        "estatus",
        "in_contract_scope_bool",
    ],
    "dtypes": {
        "contractor": "string",
        "numero": "string",
        "numero_fase": "Int64",
        "etapa": "Int64",
        "hito": "Int64",
        "semana_bloque_peso": "Int64",
        "bloque_kg": "float64",
        "peso_dossier_kg": "float64",
        "total_piezas": "Int64",
        "estatus": "string",
        "semana_liberacion_dossier": "Int64",
        "in_contract_scope_bool": "boolean",
    },
    "allowed": {"estatus": ["approved", "pending", "rejected"]},
    "rules": {"numero_blank_sets_in_contract_scope_bool_false": True},
}


@pytest.fixture
def schema_file(tmp_path: Path) -> Path:
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    return path


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def _base_row(**overrides):
    row = {
        "contractor": "BAYSA",
        "numero": "DOS-001",
        "numero_fase": 1,
        "etapa": 1,
        "hito": 10,
        "semana_bloque_peso": 202610,
        "bloque_kg": 100.5,
        "peso_dossier_kg": 90.0,
        "total_piezas": 3,
        "estatus": "pending",
        "semana_liberacion_dossier": pd.NA,
        "in_contract_scope_bool": True,
    }
    row.update(overrides)
    return row


def test_validate_fails_on_duplicate_key(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_base_row(), _base_row()])

    with pytest.raises(GuardError, match="duplicate key"):
        validate_csv(csv_path, schema_file)


def test_validate_fails_on_missing_column(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    row = _base_row()
    del row["hito"]
    _write_csv(csv_path, [row])

    with pytest.raises(GuardError, match="missing required schema column 'hito'"):
        validate_csv(csv_path, schema_file)


def test_validate_fails_on_bad_dtype(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_base_row(numero_fase="abc")])

    with pytest.raises(GuardError, match="invalid Int64 value"):
        validate_csv(csv_path, schema_file)


def test_validate_fails_on_invalid_estatus(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_base_row(estatus="in_review")])

    with pytest.raises(GuardError, match="invalid value"):
        validate_csv(csv_path, schema_file)


def test_apply_fails_on_delete_missing(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    patch_path = tmp_path / "patch.csv"
    _write_csv(csv_path, [_base_row()])

    patch_rows = [
        {
            "op": "DELETE",
            "contractor": "BAYSA",
            "numero": "DOS-404",
            "numero_fase": 1,
            "etapa": 1,
            "semana_bloque_peso": 202610,
        }
    ]
    _write_csv(patch_path, patch_rows)

    with pytest.raises(GuardError, match="DELETE key not found"):
        apply_patch_csv(csv_path, schema_file, patch_path)


def test_apply_upsert_insert_and_update(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    patch_path = tmp_path / "patch.csv"
    _write_csv(csv_path, [_base_row(estatus="pending", peso_dossier_kg=100.0)])

    patch_rows = [
        {
            "op": "UPSERT",
            "contractor": "BAYSA",
            "numero": "DOS-001",
            "numero_fase": 1,
            "etapa": 1,
            "semana_bloque_peso": 202610,
            "estatus": "approved",
            "peso_dossier_kg": 120.0,
        },
        {
            "op": "UPSERT",
            "contractor": "BAYSA",
            "numero": "DOS-002",
            "numero_fase": 1,
            "etapa": 1,
            "semana_bloque_peso": 202611,
            "hito": 11,
            "peso_dossier_kg": 80.0,
            "total_piezas": 2,
            "estatus": "pending",
            "in_contract_scope_bool": True,
        },
    ]
    _write_csv(patch_path, patch_rows)

    summary = apply_patch_csv(csv_path, schema_file, patch_path)
    result = pd.read_csv(csv_path)

    assert summary.updated == 1
    assert summary.inserted == 1
    assert summary.deleted == 0
    assert summary.backup_path.exists()

    updated = result[result["numero"] == "DOS-001"].iloc[0]
    inserted = result[result["numero"] == "DOS-002"].iloc[0]

    assert updated["estatus"] == "approved"
    assert float(updated["peso_dossier_kg"]) == 120.0
    assert inserted["estatus"] == "pending"


def test_apply_coerces_blank_numero_to_false(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    patch_path = tmp_path / "patch.csv"

    _write_csv(csv_path, [_base_row()])

    patch_rows = [
        {
            "op": "UPSERT",
            "contractor": "BAYSA",
            "numero": "",
            "numero_fase": 2,
            "etapa": 2,
            "semana_bloque_peso": 202612,
            "hito": 20,
            "peso_dossier_kg": 30.0,
            "total_piezas": 1,
            "estatus": "approved",
            "in_contract_scope_bool": True,
        }
    ]
    _write_csv(patch_path, patch_rows)

    summary = apply_patch_csv(csv_path, schema_file, patch_path)
    result = pd.read_csv(csv_path)

    assert summary.inserted == 1
    blank_numero_row = result[result["numero"].isna()].iloc[0]
    assert str(blank_numero_row["in_contract_scope_bool"]).lower() == "false"
