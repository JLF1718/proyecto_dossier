from __future__ import annotations

import pandas as pd

from backend.services.piece_signal_service import (
    _build_block_comparison,
    _build_block_dim_map,
    _build_piece_block_summary,
    _build_piece_exceptions,
    _build_piece_week_summary,
    _build_dossier_block_progress,
    _transform_piece_index,
    build_piece_signal_outputs,
)


def _sample_piece_raw() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "BLOQUE": "PRO_01",
                "Marca": "M-100",
                "Cant.": 1,
                "Nombre": "Pieza A",
                "Perfil": "W10",
                "Largo (mm)": 1000,
                "Peso(kg) un.": 100,
                "Peso(kg) tot.": 100,
                "Peso(kg) Descal.": 102,
                "Estimacion": "S-188",
                "Semana": 188,
                "Nivel": None,
                "Columna1": "x",
                "Columna2": None,
            },
            {
                "BLOQUE": "PRO_01",
                "Marca": "M-100",
                "Cant.": 1,
                "Nombre": "Pieza A repetida",
                "Perfil": "W10",
                "Largo (mm)": 950,
                "Peso(kg) un.": 95,
                "Peso(kg) tot.": 95,
                "Peso(kg) Descal.": 96,
                "Estimacion": "bad@value",
                "Semana": None,
                "Nivel": None,
                "Columna1": "y",
                "Columna2": None,
            },
            {
                "BLOQUE": "SUE_01",
                "Marca": "S-200",
                "Cant.": 1,
                "Nombre": "Pieza B",
                "Perfil": "W12",
                "Largo (mm)": 1200,
                "Peso(kg) un.": 200,
                "Peso(kg) tot.": 200,
                "Peso(kg) Descal.": 205,
                "Estimacion": None,
                "Semana": 189,
                "Nivel": "N1",
                "Columna1": "z",
                "Columna2": None,
            },
        ]
    )


def _sample_dossier() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "bloque": "PRO_01",
                "etapa": 1,
                "fase": 1,
                "peso_bloque_kg": 1000,
                "peso_dossier_kg": 1000,
                "estatus": "approved",
            },
            {
                "bloque": "SUE_01",
                "etapa": 2,
                "fase": 1,
                "peso_bloque_kg": 2000,
                "peso_dossier_kg": 0,
                "estatus": "pending",
            },
        ]
    )


def test_transform_preserves_repeated_marca_and_blank_semana_rows():
    dim_map, _ = _build_block_dim_map(_sample_dossier())
    clean = _transform_piece_index(_sample_piece_raw(), dim_map)

    assert len(clean) == 3
    assert (clean["marca"] == "M-100").sum() == 2
    assert int(clean["semana_is_blank"].sum()) == 1
    assert clean["semana"].isna().sum() == 1


def test_block_enrichment_uses_block_only_and_sets_match_flag():
    dim_map, _ = _build_block_dim_map(_sample_dossier())
    raw = _sample_piece_raw().copy()
    raw.loc[len(raw)] = {
        "BLOQUE": "X_404",
        "Marca": "X",
        "Cant.": 1,
        "Nombre": "Missing block",
        "Perfil": "W8",
        "Largo (mm)": 300,
        "Peso(kg) un.": 10,
        "Peso(kg) tot.": 10,
        "Peso(kg) Descal.": 10,
        "Estimacion": None,
        "Semana": None,
        "Nivel": None,
        "Columna1": "m",
        "Columna2": None,
    }

    clean = _transform_piece_index(raw, dim_map)
    missing_row = clean[clean["block"] == "X_404"].iloc[0]

    assert bool(missing_row["dossier_dim_match_flag"]) is False
    assert "dim_enrichment_missing" in str(missing_row["data_quality_flags"])


def test_week_summary_uses_only_rows_with_semana():
    dim_map, _ = _build_block_dim_map(_sample_dossier())
    clean = _transform_piece_index(_sample_piece_raw(), dim_map)
    weekly = _build_piece_week_summary(clean)

    assert weekly["week"].tolist() == [188, 189]
    assert weekly["piece_rows"].sum() == 2
    assert weekly["cumulative_piece_rows"].tolist() == [1, 2]


def test_block_comparison_sets_alignment_indicators():
    dim_map, _ = _build_block_dim_map(_sample_dossier())
    clean = _transform_piece_index(_sample_piece_raw(), dim_map)
    block_summary = _build_piece_block_summary(clean)
    dossier_progress = _build_dossier_block_progress(_sample_dossier())

    comparison = _build_block_comparison(block_summary, dossier_progress)
    pro_row = comparison[comparison["block"] == "PRO_01"].iloc[0]

    assert "alignment_status" in comparison.columns
    assert bool(pro_row["physical_signal_ahead_of_documentary"] or pro_row["both_aligned"] or pro_row["documentary_ahead_of_physical_signal"]) is True


def test_exception_builder_includes_required_exception_types():
    dim_map, ambiguous = _build_block_dim_map(_sample_dossier())
    clean = _transform_piece_index(_sample_piece_raw(), dim_map)
    block_summary = _build_piece_block_summary(clean)
    comparison = _build_block_comparison(block_summary, _build_dossier_block_progress(_sample_dossier()))

    exceptions = _build_piece_exceptions(clean, block_summary, comparison, ambiguous_blocks=ambiguous)
    exception_types = set(exceptions["exception_type"].tolist())

    assert "malformed estimation value" in exception_types


def test_build_piece_signal_outputs_returns_isolated_frames_without_mutating_dossier_semantics():
    outputs = build_piece_signal_outputs(
        piece_raw_df=_sample_piece_raw(),
        dossier_df=_sample_dossier(),
        write_outputs=False,
    )

    assert set(outputs.keys()) == {"piece_clean", "block_summary", "week_summary", "exceptions", "comparison"}
    assert "documented_progress_pct" in outputs["comparison"].columns
    assert "physical_signal_pct" in outputs["comparison"].columns
