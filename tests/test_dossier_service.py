import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from backend.services.dossier_service import (
    _build_backlog_aging_frame,
    _build_cumulative_weekly_growth,
    _build_kpis,
    _build_weekly_release_series,
    _detect_stagnant_groups,
    _resolve_analysis_week,
    _standardize_baysa_processed,
    build_weekly_management_payload,
    compute_kpis,
)
from scripts.normalize_baysa_dataset import _derive_in_contract_scope


def _weekly_df(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    defaults = {
        "contractor": "BAYSA",
        "stage": "ETAPA_1",
        "status": "pending",
        "in_contract_scope": True,
        "weight_kg": 0.0,
        "reference_week": pd.NA,
        "release_week": pd.NA,
        "bloque": "PRO_01",
    }
    for column, value in defaults.items():
        if column not in frame.columns:
            frame[column] = value
    frame["reference_week"] = frame["reference_week"].astype("Int64")
    frame["release_week"] = frame["release_week"].astype("Int64")
    return frame


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
    assert standardized["reference_week"].isna().all()
    assert standardized["release_week"].isna().all()


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


def test_kpis_weight_audit_reports_raw_in_scope_and_displayed_tons():
    df = pd.DataFrame(
        {
            "contractor": ["BAYSA", "BAYSA", "BAYSA"],
            "stage": ["ETAPA_1", "ETAPA_1", "ETAPA_2"],
            "status": ["approved", "pending", "approved"],
            "in_contract_scope": [True, False, True],
            "weight_kg": [1000.0, 500.0, 2500.0],
        }
    )
    df.attrs["weight_source_column"] = "peso_dossier_kg"

    kpis = _build_kpis(df)
    audit = kpis["weight_audit"]

    assert audit["weight_source_column"] == "peso_dossier_kg"
    assert audit["kpi_weight_column"] == "weight_kg"
    assert audit["weight_scope_filter"] == "in_contract_scope == True"
    assert audit["raw_total_weight_kg"] == 4000.0
    assert audit["in_scope_total_weight_kg"] == 3500.0
    assert audit["in_scope_weight_dossier_kg"] == 3500.0
    assert audit["in_scope_weight_block_kg"] == 3500.0
    assert audit["in_scope_block_vs_dossier_delta_kg"] == 0.0
    assert audit["delta_warning_triggered"] is False
    assert audit["displayed_total_weight_t"] == 3.5
    assert audit["displayed_weight_unit"] == "t"
    assert kpis["peso_total_ton"] == 3.5


def test_compute_kpis_standardizes_baysa_processed_frame_and_excludes_out_of_scope_weight():
    raw = pd.DataFrame(
        {
            "contractor": ["BAYSA", "BAYSA", "BAYSA"],
            "etapa": [1, 1, 2],
            "estatus": ["LIBERADO", "ATENCIÓN COMENTARIOS", "LIBERADO"],
            "in_contract_scope": [True, False, True],
            "peso_dossier_kg": [1500.0, 2000.0, 500.0],
        }
    )

    kpis = compute_kpis(raw)
    audit = kpis["weight_audit"]

    assert kpis["rows_in_contract_scope"] == 2
    assert kpis["rows_out_of_scope"] == 1
    assert kpis["peso_total_ton"] == 2.0
    assert audit["weight_source_column"] == "peso_dossier_kg"
    assert audit["kpi_weight_column"] == "weight_kg"
    assert audit["raw_total_weight_kg"] == 4000.0
    assert audit["in_scope_total_weight_kg"] == 2000.0
    assert audit["displayed_total_weight_t"] == 2.0


def test_compute_kpis_prefers_block_weight_for_totals_and_warns_on_large_delta():
    raw = pd.DataFrame(
        {
            "contractor": ["BAYSA", "BAYSA", "BAYSA"],
            "etapa": [1, 1, 2],
            "estatus": ["LIBERADO", "LIBERADO", "ATENCIÓN COMENTARIOS"],
            "in_contract_scope": [True, True, True],
            "peso_dossier_kg": [1000.0, 0.0, 500.0],
            "peso_bloque_kg": [120000.0, 130000.0, 110000.0],
        }
    )

    kpis = compute_kpis(raw)
    audit = kpis["weight_audit"]

    assert audit["weight_source_column"] == "peso_bloque_kg"
    assert audit["kpi_weight_column"] == "weight_block_kg"
    assert audit["in_scope_weight_dossier_kg"] == 1500.0
    assert audit["in_scope_weight_block_kg"] == 360000.0
    assert audit["in_scope_block_vs_dossier_delta_kg"] == 358500.0
    assert audit["delta_warning_triggered"] is True
    assert kpis["peso_total_ton"] == 360.0
    assert kpis["peso_liberado_ton"] == 250.0


def test_analysis_week_resolver_uses_selected_week_or_latest_available_week():
    df = _weekly_df(
        [
            {"status": "approved", "release_week": 186, "reference_week": 180, "weight_kg": 500.0},
            {"status": "pending", "reference_week": 191, "bloque": "SUE_01"},
            {"status": "in_review", "reference_week": pd.NA, "bloque": "DOSSIER GENERAL"},
        ]
    )

    assert _resolve_analysis_week(df) == 191
    assert _resolve_analysis_week(df, selected_week="188") == 188


def test_weekly_release_series_supports_missing_week_values_and_zero_fills_previous_week():
    df = _weekly_df(
        [
            {"status": "approved", "release_week": 180, "weight_kg": 1000.0, "reference_week": 175},
            {"status": "approved", "release_week": pd.NA, "weight_kg": 2000.0, "reference_week": 176},
            {"status": "approved", "release_week": 182, "weight_kg": 500.0, "reference_week": 177},
            {"status": "pending", "reference_week": 182},
        ]
    )

    release_series = _build_weekly_release_series(df, analysis_week=182)

    assert release_series["week"].tolist() == [180, 181, 182]
    assert release_series["released_dossiers"].tolist() == [1, 0, 1]
    assert release_series["released_weight_t"].tolist() == [1.0, 0.0, 0.5]


def test_cumulative_growth_builder_handles_week_gaps_without_resetting_progress():
    release_series = pd.DataFrame(
        {
            "week": [180, 181, 182],
            "released_dossiers": [1, 0, 2],
            "released_weight_t": [1.0, 0.0, 2.5],
        }
    )

    cumulative = _build_cumulative_weekly_growth(release_series)

    assert cumulative["cumulative_approved_dossiers"].tolist() == [1, 1, 3]
    assert cumulative["cumulative_released_weight_t"].tolist() == [1.0, 1.0, 3.5]


def test_weekly_management_payload_handles_no_previous_week_data():
    df = _weekly_df(
        [
            {"status": "approved", "release_week": 180, "reference_week": 178, "weight_kg": 1200.0},
            {"status": "pending", "reference_week": 180, "bloque": "SUE_03"},
        ]
    )

    payload = build_weekly_management_payload(df, selected_week=180)

    assert payload["analysis_week"] == 180
    assert payload["previous_week"] == 179
    assert payload["delta_kpis"] == {
        "analysis_week": 180,
        "previous_week": 179,
        "released_this_week": 1,
        "released_weight_t_this_week": 1.2,
        "change_vs_previous_week": 1,
        "weight_change_t_vs_previous_week": 1.2,
    }
    assert payload["weekly_comparison"]["current_vs_previous"]["cumulative_approved_previous"] == 0
    assert payload["weekly_comparison"]["current_vs_previous"]["cumulative_approved_growth"] == 1


def test_weekly_management_payload_handles_empty_filtered_frame():
    payload = build_weekly_management_payload(_weekly_df([]))

    assert payload["analysis_week"] is None
    assert payload["delta_kpis"]["released_this_week"] == 0
    assert payload["weekly_comparison"]["release_series"] == []
    assert payload["backlog_aging_summary"]["groups"] == []
    assert payload["stagnant_groups_summary"]["groups"] == []


def test_backlog_aging_builder_handles_missing_reference_weeks_and_age_calculation():
    df = _weekly_df(
        [
            {"status": "pending", "reference_week": 185, "bloque": "PRO_01"},
            {"status": "in_review", "reference_week": pd.NA, "bloque": "PRO_02"},
            {"status": "approved", "release_week": 189, "reference_week": 184, "weight_kg": 500.0},
        ]
    )

    backlog = _build_backlog_aging_frame(df, analysis_week=190)
    group = backlog.iloc[0].to_dict()

    assert group["open_backlog"] == 2
    assert group["pending_dossiers"] == 1
    assert group["in_review_dossiers"] == 1
    assert group["rows_without_reference_week"] == 1
    assert int(group["oldest_reference_week"]) == 185
    assert int(group["max_age_weeks"]) == 5
    assert group["avg_age_weeks"] == 5.0


def test_stagnant_group_detector_flags_only_groups_without_current_week_movement():
    df = _weekly_df(
        [
            {"status": "pending", "reference_week": 184, "bloque": "PRO_01", "stage": "ETAPA_1"},
            {"status": "pending", "reference_week": 183, "bloque": "PRO_02", "stage": "ETAPA_1"},
            {"status": "approved", "release_week": 189, "reference_week": 182, "weight_kg": 1000.0, "bloque": "SUE_01", "stage": "ETAPA_2"},
            {"status": "pending", "reference_week": 185, "bloque": "SUE_02", "stage": "ETAPA_2"},
            {"status": "approved", "release_week": 190, "reference_week": 185, "weight_kg": 900.0, "bloque": "SUE_03", "stage": "ETAPA_2"},
        ]
    )

    stagnant = _detect_stagnant_groups(df, analysis_week=190)

    assert len(stagnant) == 1
    group = stagnant.iloc[0].to_dict()
    assert group["stage_category"] == "Stage 1"
    assert group["building_family"] == "PRO"
    assert group["open_backlog"] == 2
    assert group["released_this_week"] == 0
    assert group["cumulative_approved_growth"] == 0


def test_weekly_management_payload_exposes_backlog_and_stagnant_summaries():
    df = _weekly_df(
        [
            {"status": "approved", "release_week": 188, "reference_week": 180, "weight_kg": 1000.0, "bloque": "PRO_01", "stage": "ETAPA_1"},
            {"status": "approved", "release_week": 190, "reference_week": 181, "weight_kg": 500.0, "bloque": "PRO_02", "stage": "ETAPA_1"},
            {"status": "pending", "reference_week": 184, "bloque": "SUE_01", "stage": "ETAPA_2"},
            {"status": "pending", "reference_week": 186, "bloque": "SUE_02", "stage": "ETAPA_2"},
        ]
    )

    payload = build_weekly_management_payload(df, selected_week=190)

    assert payload["weekly_comparison"]["current_vs_previous"]["current_released_dossiers"] == 1
    assert payload["weekly_comparison"]["current_vs_previous"]["cumulative_approved_growth"] == 1
    assert payload["weekly_comparison"]["current_vs_previous"]["cumulative_released_weight_t_growth"] == 0.5
    assert payload["backlog_aging_summary"]["total_open_backlog"] == 2
    assert payload["backlog_aging_summary"]["oldest_reference_week"] == 184
    assert payload["stagnant_groups_summary"]["stagnant_groups"] == 1
    assert payload["stagnant_groups_summary"]["total_open_backlog"] == 2
