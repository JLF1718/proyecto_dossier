import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from backend.services.dossier_service import _build_kpis, _standardize_baysa_processed
from scripts.normalize_baysa_dataset import _derive_in_contract_scope


def test_in_contract_scope_marks_double_dash_as_out_of_scope():
    scope = _derive_in_contract_scope(pd.Series(["1", "25", "--", None]))

    assert scope.tolist() == [True, True, False, False]


def test_baysa_processed_status_mapping_keeps_internal_review_separate():
    df = pd.DataFrame(
        {
            "contractor": ["BAYSA"] * 4,
            "etapa": [1, 1, 1, 1],
            "estatus": [
                "LIBERADO",
                "ATENCIÓN COMENTARIOS",
                "REVISIÓN INPROS",
                "FUERA DE ALCANCE",
            ],
            "in_contract_scope": [True, True, True, False],
            "peso_dossier_kg": [100.0, 100.0, 100.0, 100.0],
        }
    )

    standardized = _standardize_baysa_processed(df)

    assert standardized["status"].tolist() == [
        "approved",
        "pending",
        "in_review",
        "out_of_scope",
    ]


def test_kpis_exclude_out_of_scope_rows_from_dashboard_counts():
    df = pd.DataFrame(
        {
            "contractor": ["BAYSA", "BAYSA", "BAYSA", "BAYSA"],
            "stage": ["ETAPA_1", "ETAPA_1", "ETAPA_1", "ETAPA_2"],
            "status": ["approved", "pending", "in_review", "out_of_scope"],
            "in_contract_scope": [True, True, True, False],
            "weight_kg": [1000.0, 500.0, 250.0, 900.0],
        }
    )

    kpis = _build_kpis(df)

    assert kpis["total_rows"] == 4
    assert kpis["rows_in_contract_scope"] == 3
    assert kpis["rows_out_of_scope"] == 1
    assert kpis["total_dossiers"] == 3
    assert kpis["approved_dossiers"] == 1
    assert kpis["pending_dossiers"] == 1
    assert kpis["in_review_dossiers"] == 1
    assert kpis["rejected_dossiers"] == 0
    assert kpis["status_distribution"] == {
        "approved": 1,
        "pending": 1,
        "in_review": 1,
        "rejected": 0,
    }
