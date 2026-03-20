from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tools.csv_editor.core import CsvEditorError, apply_changes_by_bloque


SCHEMA = {
    "key": ["contractor", "bloque"],
    "required": ["contractor", "numero", "bloque"],
    "dtypes": {
        "contractor": "string",
        "numero": "string",
        "bloque": "string",
        "estatus": "string",
        "semana_liberacion_dossier": "Int64",
        "peso_dossier_kg": "float64",
        "total_piezas": "Int64",
        "in_contract_scope": "boolean",
    },
    "allowed": {"estatus": ["approved", "pending", "in_review"]},
}


@pytest.fixture
def schema_file(tmp_path: Path) -> Path:
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    return path


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def _row(bloque: str, **overrides: object) -> dict:
    base = {
        "contractor": "BAYSA",
        "numero": "DOS-001",
        "bloque": bloque,
        "estatus": "pending",
        "semana_liberacion_dossier": 202601,
        "peso_dossier_kg": 100.0,
        "total_piezas": 10,
        "in_contract_scope": True,
    }
    base.update(overrides)
    return base


def test_updates_exactly_one_row_by_bloque(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01"), _row("B-02", numero="DOS-002")])

    apply_changes_by_bloque(
        csv_path,
        schema_file,
        "B-02",
        {"estatus": "approved", "peso_dossier_kg": "123.5"},
    )

    result = pd.read_csv(csv_path)
    row_1 = result[result["bloque"] == "B-01"].iloc[0]
    row_2 = result[result["bloque"] == "B-02"].iloc[0]

    assert row_1["estatus"] == "pending"
    assert row_2["estatus"] == "approved"
    assert float(row_2["peso_dossier_kg"]) == 123.5


def test_only_specified_fields_changed(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01", numero="DOS-050", total_piezas=7)])

    apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "approved"})

    result = pd.read_csv(csv_path)
    row = result.iloc[0]
    assert row["estatus"] == "approved"
    assert row["numero"] == "DOS-050"
    assert int(row["total_piezas"]) == 7


def test_estatus_uppercase_is_stored_lowercase(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01", estatus="pending")])

    apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "APPROVED"})

    result = pd.read_csv(csv_path)
    assert result.iloc[0]["estatus"] == "approved"


def test_estatus_title_case_is_stored_lowercase(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01", estatus="approved")])

    apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "Pending"})

    result = pd.read_csv(csv_path)
    assert result.iloc[0]["estatus"] == "pending"


def test_estatus_invalid_value_fails(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01", estatus="pending")])

    with pytest.raises(CsvEditorError, match="Invalid estatus"):
        apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "OBSERVADO"})


def test_estatus_revision_inpros_variant_maps_to_in_review(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01", estatus="pending")])

    apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "EN REVISIÓN INPROS"})

    result = pd.read_csv(csv_path)
    assert result.iloc[0]["estatus"] == "in_review"


def test_backup_created(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01")])

    backup_path = apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "approved"})

    assert backup_path.exists()
    assert backup_path.parent.name == "backups"


def test_validate_called_and_enforced(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01", estatus="pending")])

    calls = {"count": 0}

    def fake_validate(_csv: Path, _schema: Path) -> pd.DataFrame:
        calls["count"] += 1
        raise CsvEditorError("force fail")

    with pytest.raises(CsvEditorError, match="Validation failed"):
        apply_changes_by_bloque(
            csv_path,
            schema_file,
            "B-01",
            {"estatus": "approved"},
            validate_fn=fake_validate,
        )

    restored = pd.read_csv(csv_path)
    assert restored.iloc[0]["estatus"] == "pending"
    assert calls["count"] == 1


def test_duplicate_bloque_fails(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01"), _row("B-01", numero="DOS-002")])

    with pytest.raises(CsvEditorError, match="Duplicate bloque"):
        apply_changes_by_bloque(csv_path, schema_file, "B-01", {"estatus": "approved"})


def test_missing_bloque_fails(tmp_path: Path, schema_file: Path) -> None:
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path, [_row("B-01")])

    with pytest.raises(CsvEditorError, match="Bloque not found"):
        apply_changes_by_bloque(csv_path, schema_file, "B-404", {"estatus": "approved"})
