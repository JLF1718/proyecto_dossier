"""QA Platform Dashboard (Starter)

Run with:
    python dashboard/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, clientside_callback

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.services.dossier_service import (
    build_executive_report_payload,
    build_historical_comparison_payload,
    build_weekly_management_payload,
    compute_kpis,
    list_weekly_snapshots,
)
from backend.services.piece_signal_service import load_piece_signal_payload

from dashboard.components.cards import (
    backlog_aging_summary,
    executive_report_pack,
    executive_cards,
    executive_summary_table,
    physical_signal_cards,
    physical_signal_comparison_table,
    physical_signal_exceptions_table,
    historical_comparison_cards,
    quality_cards,
    risk_exception_cards,
    stagnant_groups_summary,
    weekly_management_cards,
)
from dashboard.components.figures import (
    cumulative_approved_growth_figure,
    cumulative_released_weight_growth_figure,
    derive_building_family,
    derive_stage_category,
    executive_summary_frame,
    snapshot_approval_trend_figure,
    snapshot_backlog_trend_figure,
    snapshot_released_trend_figure,
    snapshot_released_weight_trend_figure,
    physical_signal_weekly_trend_figure,
    status_by_block_figure,
    status_by_stage_figure,
    weekly_released_dossiers_figure,
    weekly_released_weight_figure,
    weekly_accumulated_progress_figure,
    weekly_progress_figure,
)
from dashboard.i18n import normalize_lang, stage_label, t
from dashboard.layout import create_layout

_PROCESSED_CSV_PATH = _PROJECT_ROOT / "data" / "processed" / "baysa_dossiers_clean.csv"
_DASH_ASSETS_PATH = _PROJECT_ROOT / "assets"
_PHYSICAL_SIGNAL_ENABLED = os.getenv("QA_ENABLE_PHYSICAL_SIGNAL", "1").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_dash_base_path(raw_path: str) -> str:
    value = (raw_path or "/").strip()
    if not value:
        return "/"
    if not value.startswith("/"):
        value = f"/{value}"
    if not value.endswith("/"):
        value = f"{value}/"
    return value

_APPROVED = {"approved", "liberado", "aprobado", "aceptado"}
_IN_REVIEW = {
    "in_review",
    "in review",
    "en_revisión",
    "en revisión",
    "revisión inpros",
    "en revision inpros",
    "en_revision_inpros",
}

_STAGE_FILTER_ORDER = [
    "Stage 1",
    "Stage 2",
    "Stage 3",
    "Stage 4",
    "General Information",
    "Protective Coatings",
]


def _load_local_dossier_csv() -> pd.DataFrame:
    """Load processed BAYSA CSV keeping all rows for KPI split calculations."""
    try:
        df = pd.read_csv(_PROCESSED_CSV_PATH)
        return df
    except Exception:
        return pd.DataFrame()


def _in_scope(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "in_contract_scope" not in df.columns:
        return df
    return df[df["in_contract_scope"].astype(str).str.lower().isin(["true", "1", "yes"])]


def _compute_kpis(all_rows_df: pd.DataFrame) -> Dict[str, Any]:
    return compute_kpis(all_rows_df)


def _apply_local_csv_filters(
    df: pd.DataFrame,
    contractor: Optional[str],
    discipline: Optional[str],
    system: Optional[str],
    week: Optional[str],
    *,
    include_out_of_scope: bool = False,
) -> pd.DataFrame:
    """Apply dashboard filters to processed CSV rows."""
    if df.empty:
        return df
    out = df.copy()

    if not include_out_of_scope:
        out = _in_scope(out)

    if contractor and "contractor" in out.columns:
        out = out[out["contractor"].astype(str).str.upper() == contractor.strip().upper()]

    out["stage_category"] = derive_stage_category(out)
    out["building_family"] = derive_building_family(out)

    if discipline:
        out = out[out["stage_category"] == discipline]
    if system:
        out = out[out["building_family"] == system]
    if week and "hito_semana" in out.columns:
        try:
            week_num = float(week)
            out = out[pd.to_numeric(out["hito_semana"], errors="coerce") == week_num]
        except (ValueError, TypeError):
            pass
    return out


def _piece_stage_category(series: pd.Series) -> pd.Series:
    out = pd.Series("", index=series.index, dtype="object")
    numeric = pd.to_numeric(series, errors="coerce")
    out.loc[numeric.notna()] = "Stage " + numeric.loc[numeric.notna()].astype(int).astype(str)
    return out


app = dash.Dash(
    __name__,
    assets_folder=str(_DASH_ASSETS_PATH),
    requests_pathname_prefix=_normalize_dash_base_path(os.getenv("DASH_BASE_PATH", "/")),
    routes_pathname_prefix=_normalize_dash_base_path(os.getenv("DASH_BASE_PATH", "/")),
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
    title="QA Platform Dashboard",
    suppress_callback_exceptions=True,
)
server = app.server
app.layout = create_layout()


@app.callback(
    Output("language-store", "data"),
    Input("language-selector", "value"),
)
def update_language_store(language_value: Optional[str]) -> Dict[str, str]:
    return {"lang": normalize_lang(language_value)}


@app.callback(
    Output("hero-kicker", "children"),
    Output("hero-title", "children"),
    Output("hero-subtitle", "children"),
    Output("brand-subunit", "children"),
    Output("export-banner-kicker", "children"),
    Output("export-banner-title", "children"),
    Output("export-banner-subtitle", "children"),
    Output("section-executive-overview", "children"),
    Output("section-weekly-management", "children"),
    Output("section-physical-signal", "children"),
    Output("section-risk-exceptions", "children"),
    Output("section-historical-comparison", "children"),
    Output("section-dossier-analysis", "children"),
    Output("section-executive-summary", "children"),
    Output("section-executive-report-pack", "children"),
    Output("section-quality-signals", "children"),
    Output("filter-contractor-label", "children"),
    Output("filter-discipline-label", "children"),
    Output("filter-system-label", "children"),
    Output("filter-week-label", "children"),
    Output("filter-compare-week-label", "children"),
    Output("filter-contractor", "placeholder"),
    Output("filter-discipline", "placeholder"),
    Output("filter-system", "placeholder"),
    Output("filter-week", "placeholder"),
    Output("filter-compare-week", "placeholder"),
    Output("language-selector", "options"),
    Output("presentation-mode-label", "children"),
    Output("presentation-mode-toggle", "options"),
    Output("management-history-label", "children"),
    Output("management-history-toggle", "options"),
    Output("print-action-label", "children"),
    Input("language-store", "data"),
)
def update_static_labels(language_store: Optional[Dict[str, str]]):
    lang = normalize_lang((language_store or {}).get("lang"))

    contractor = t(lang, "filter.contractor")
    discipline = t(lang, "filter.discipline")
    system = t(lang, "filter.system")
    week = t(lang, "filter.week")

    return (
        t(lang, "hero.kicker"),
        t(lang, "hero.title"),
        t(lang, "hero.subtitle"),
        t(lang, "brand.subunit"),
        t(lang, "export.banner.kicker"),
        t(lang, "export.banner.title"),
        t(lang, "export.banner.subtitle"),
        t(lang, "section.executive_overview"),
        t(lang, "section.weekly_management"),
        t(lang, "section.physical_signal"),
        t(lang, "section.risk_exceptions"),
        t(lang, "section.historical_comparison"),
        t(lang, "section.dossier_analysis"),
        t(lang, "section.executive_summary"),
        t(lang, "section.executive_report_pack"),
        t(lang, "section.quality_signals"),
        contractor,
        discipline,
        system,
        week,
        t(lang, "filter.compare_week"),
        t(lang, "filter.placeholder", label=contractor.lower()),
        t(lang, "filter.placeholder", label=discipline.lower()),
        t(lang, "filter.placeholder", label=system.lower()),
        t(lang, "filter.placeholder", label=week.lower()),
        t(lang, "filter.placeholder", label=t(lang, "filter.compare_week").lower()),
        [
            {"label": t(lang, "lang.en"), "value": "en"},
            {"label": t(lang, "lang.es"), "value": "es"},
        ],
        t(lang, "presentation.mode"),
        [{"label": t(lang, "presentation.hint"), "value": "on"}],
        t(lang, "filter.history_mode"),
        [{"label": t(lang, "history.mode_hint"), "value": "on"}],
        t(lang, "export.print.action"),
    )


clientside_callback(
    """
    function(nClicks) {
        if (!nClicks) {
            return window.dash_clientside.no_update;
        }
        window.print();
        return "printed";
    }
    """,
    Output("print-action-status", "children"),
    Input("print-action", "n_clicks"),
    prevent_initial_call=True,
)


@app.callback(
    Output("qa-shell-root", "className"),
    Input("presentation-mode-toggle", "value"),
)
def update_presentation_mode(toggle_value: Optional[list[str]]) -> str:
    is_presentation = bool(toggle_value) and "on" in toggle_value
    return "qa-shell qa-export-ready" if is_presentation else "qa-shell"


@app.callback(
    Output("filter-contractor", "options"),
    Output("filter-discipline", "options"),
    Output("filter-system", "options"),
    Output("filter-week", "options"),
    Output("filter-compare-week", "options"),
    Output("executive-kpis", "children"),
    Output("weekly-management-kpis", "children"),
    Output("physical-signal-kpis", "children"),
    Output("risk-exception-kpis", "children"),
    Output("historical-comparison-kpis", "children"),
    Output("quality-kpis", "children"),
    Output("physical-signal-weekly-graph", "figure"),
    Output("weekly-release-count-graph", "figure"),
    Output("weekly-release-weight-graph", "figure"),
    Output("cumulative-approved-growth-graph", "figure"),
    Output("cumulative-release-weight-graph", "figure"),
    Output("snapshot-release-trend-graph", "figure"),
    Output("snapshot-backlog-trend-graph", "figure"),
    Output("snapshot-approval-trend-graph", "figure"),
    Output("snapshot-weight-trend-graph", "figure"),
    Output("backlog-aging-summary", "children"),
    Output("stagnant-groups-summary", "children"),
    Output("physical-signal-exceptions", "children"),
    Output("physical-signal-comparison-table", "children"),
    Output("stage-status-graph", "figure"),
    Output("block-status-graph", "figure"),
    Output("weekly-progress-graph", "figure"),
    Output("weekly-accum-graph", "figure"),
    Output("executive-summary-table", "children"),
    Output("executive-report-pack", "children"),
    Input("language-store", "data"),
    Input("filter-contractor", "value"),
    Input("filter-discipline", "value"),
    Input("filter-system", "value"),
    Input("filter-week", "value"),
    Input("management-history-toggle", "value"),
    Input("filter-compare-week", "value"),
)
def update_dashboard(
    language_store: Optional[Dict[str, str]],
    contractor: Optional[str],
    discipline: Optional[str],
    system: Optional[str],
    week: Optional[str],
    history_toggle: Optional[list[str]],
    compare_week: Optional[str],
):
    lang = normalize_lang((language_store or {}).get("lang"))
    local_df = _load_local_dossier_csv()
    in_scope_df = _in_scope(local_df).copy()

    if not in_scope_df.empty:
        in_scope_df["stage_category"] = derive_stage_category(in_scope_df)
        in_scope_df["building_family"] = derive_building_family(in_scope_df)

    kpi_payload = _compute_kpis(local_df)
    local_filtered = _apply_local_csv_filters(
        local_df,
        contractor=contractor,
        discipline=discipline,
        system=system,
        week=week,
    )
    summary_filtered = _apply_local_csv_filters(
        local_df,
        contractor=contractor,
        discipline=discipline,
        system=system,
        week=week,
        include_out_of_scope=True,
    )
    summary_table = executive_summary_table(executive_summary_frame(summary_filtered), lang=lang)
    management_filtered = _apply_local_csv_filters(
        local_df,
        contractor=contractor,
        discipline=discipline,
        system=system,
        week=None,
        include_out_of_scope=True,
    )
    weekly_payload = build_weekly_management_payload(management_filtered, selected_week=week)

    contractor_options: list[dict[str, str]] = []
    if "contractor" in in_scope_df.columns:
        contractor_values = sorted(v for v in in_scope_df["contractor"].dropna().astype(str).unique() if v.strip())
        contractor_options = [{"label": v.upper(), "value": v.upper()} for v in contractor_values]

    stage_values = {
        str(v).strip()
        for v in in_scope_df.get("stage_category", pd.Series(dtype=object)).dropna().unique()
        if str(v).strip()
    }
    discipline_values = [stage for stage in _STAGE_FILTER_ORDER if stage in stage_values]
    discipline_options = [{"label": stage_label(str(v), lang), "value": str(v)} for v in discipline_values]

    family_values = ["PRO", "SUE", "SHARED"]
    system_options = [{"label": v, "value": v} for v in family_values]

    week_options: list[dict[str, str]] = []
    if not in_scope_df.empty and "hito_semana" in in_scope_df.columns:
        semanas = sorted(
            int(s)
            for s in pd.to_numeric(in_scope_df["hito_semana"], errors="coerce").dropna().unique()
        )
        week_options = [{"label": t(lang, "week.label", week=s), "value": str(s)} for s in semanas]

    snapshot_options = [
        {"label": t(lang, "week.label", week=int(item["analysis_week"])), "value": str(int(item["analysis_week"]))}
        for item in reversed(list_weekly_snapshots())
        if item.get("analysis_week") is not None
    ]

    history_mode = bool(history_toggle) and "on" in history_toggle
    effective_compare_week = compare_week if history_mode else None
    historical_payload = build_historical_comparison_payload(
        management_filtered,
        selected_week=week,
        comparison_week=effective_compare_week,
    )
    report_payload = build_executive_report_payload(
        management_filtered,
        selected_week=week,
        comparison_week=effective_compare_week,
        language=lang,
    )

    piece_payload = {"kpis": {}, "week_summary": [], "comparison": [], "exceptions": []}
    if _PHYSICAL_SIGNAL_ENABLED:
        raw_piece = load_piece_signal_payload(rebuild_if_missing=True)
        comparison_df = raw_piece.get("comparison", pd.DataFrame()).copy()
        week_df = raw_piece.get("week_summary", pd.DataFrame()).copy()
        exceptions_df = raw_piece.get("exceptions", pd.DataFrame()).copy()

        if not comparison_df.empty:
            comparison_df["stage_category"] = _piece_stage_category(comparison_df.get("etapa", pd.Series(dtype="object")))
            if discipline:
                comparison_df = comparison_df[comparison_df["stage_category"] == discipline]
            if system:
                comparison_df = comparison_df[comparison_df["family"].astype(str) == system]

        if not exceptions_df.empty and not comparison_df.empty and "block" in exceptions_df.columns:
            allowed_blocks = set(comparison_df["block"].astype(str).tolist())
            exceptions_df = exceptions_df[exceptions_df["block"].astype(str).isin(allowed_blocks)]

        piece_payload = {
            "kpis": raw_piece.get("kpis", {}),
            "week_summary": week_df.to_dict("records") if not week_df.empty else [],
            "comparison": comparison_df.to_dict("records") if not comparison_df.empty else [],
            "exceptions": exceptions_df.to_dict("records") if not exceptions_df.empty else [],
        }

    return (
        contractor_options,
        discipline_options,
        system_options,
        week_options,
        snapshot_options,
        executive_cards(kpi_payload, lang=lang),
        weekly_management_cards(weekly_payload, lang=lang),
        physical_signal_cards(piece_payload, lang=lang),
        risk_exception_cards(weekly_payload, lang=lang),
        historical_comparison_cards(historical_payload, lang=lang),
        quality_cards(kpi_payload, lang=lang),
        physical_signal_weekly_trend_figure(piece_payload, lang=lang),
        weekly_released_dossiers_figure(weekly_payload, lang=lang),
        weekly_released_weight_figure(weekly_payload, lang=lang),
        cumulative_approved_growth_figure(weekly_payload, lang=lang),
        cumulative_released_weight_growth_figure(weekly_payload, lang=lang),
        snapshot_released_trend_figure(historical_payload, lang=lang),
        snapshot_backlog_trend_figure(historical_payload, lang=lang),
        snapshot_approval_trend_figure(historical_payload, lang=lang),
        snapshot_released_weight_trend_figure(historical_payload, lang=lang),
        backlog_aging_summary(weekly_payload, lang=lang),
        stagnant_groups_summary(weekly_payload, lang=lang),
        physical_signal_exceptions_table(piece_payload, lang=lang),
        physical_signal_comparison_table(piece_payload, lang=lang),
        status_by_stage_figure(local_filtered, lang=lang),
        status_by_block_figure(local_filtered, lang=lang),
        weekly_progress_figure(local_filtered, lang=lang),
        weekly_accumulated_progress_figure(local_filtered, lang=lang),
        summary_table,
        executive_report_pack(report_payload, lang=lang),
    )


app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
            :root {
                --brand-navy: #0b2a4a;
                --brand-blue: #1f4e79;
                --brand-cyan: #2f7e95;
                --brand-gold: #b49552;
                --brand-line: #9db4c7;
                --qa-ink: #10222f;
                --qa-surface: #eef3f8;
                --qa-paper: #ffffff;
            }
      body {
        margin: 0;
        color: var(--qa-ink);
        font-family: 'IBM Plex Sans', sans-serif;
        background:
                    radial-gradient(circle at 90% 10%, rgba(47,126,149,.16), transparent 35%),
                    radial-gradient(circle at 8% 20%, rgba(31,78,121,.12), transparent 42%),
          var(--qa-surface);
      }
      h1, h2, h3, h4, h5 {
        font-family: 'Space Grotesk', sans-serif;
                letter-spacing: .008em;
      }
      .qa-shell {
                padding: 18px;
                max-width: 1480px;
                margin: 0 auto;
      }
            .qa-hero {
                border-top: 5px solid #66d0e2;
                border-left: 3px solid rgba(255,255,255,.35);
                background:
                    linear-gradient(140deg, rgba(4,20,39,.98), rgba(12,53,90,.97) 60%, rgba(18,75,116,.95)),
                    radial-gradient(circle at 88% 16%, rgba(102,208,226,.22), transparent 42%);
                color: #f8fbff;
                box-shadow: 0 16px 32px rgba(9,26,45,.3);
                position: relative;
                overflow: hidden;
            }
            .qa-hero::after {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(0,0,0,.1));
                pointer-events: none;
            }
            .qa-hero .card-body {
                position: relative;
                z-index: 1;
                display: grid;
                gap: 1rem;
            }
            .qa-hero-topline {
                display: flex;
                align-items: flex-start;
                justify-content: flex-start;
                gap: 1rem;
                flex-wrap: wrap;
            }
            .qa-hero-copy {
                min-width: 0;
                flex: 1 1 520px;
                max-width: 920px;
            }
            .qa-hero-kicker {
                color: #a9d9e4;
                font-size: .72rem;
                text-transform: uppercase;
                letter-spacing: .14em;
                font-weight: 600;
            }
            .qa-page-title {
                color: #ffffff;
                font-size: clamp(1.7rem, 3.1vw, 2.55rem);
                font-weight: 800;
                letter-spacing: .02em;
                text-transform: uppercase;
                line-height: 1.05;
                text-shadow: 0 2px 12px rgba(4,16,30,.42);
            }
            .qa-hero-subtitle {
                color: rgba(236,247,252,.95);
                font-size: .88rem;
                letter-spacing: .035em;
                font-weight: 500;
            }
            .qa-brand-lockup {
                display: inline-flex;
                align-items: center;
                gap: .85rem;
                min-width: 245px;
                padding: .72rem .86rem;
                border: 1px solid rgba(255,255,255,.18);
                border-radius: 14px;
                background: rgba(255,255,255,.08);
                backdrop-filter: blur(10px);
            }
            .qa-brand-media {
                flex: 0 0 auto;
            }
            .qa-brand-logo {
                display: block;
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }
            .qa-logo-badge {
                width: 70px;
                height: 70px;
                border-radius: 12px;
                padding: 8px;
                background: #ffffff;
                border: 1px solid rgba(16,34,47,.14);
                box-shadow: 0 1px 4px rgba(7,26,44,.18);
                display: grid;
                place-items: center;
            }
            .qa-logo-badge--compact {
                width: 58px;
                height: 58px;
                padding: 6px;
                border-radius: 10px;
            }
            .qa-brand-monogram {
                width: 100%;
                height: 100%;
                border-radius: 14px;
                display: grid;
                place-items: center;
                background: linear-gradient(145deg, rgba(180,149,82,.95), rgba(122,96,45,.95));
                color: #ffffff;
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.15rem;
                font-weight: 700;
                letter-spacing: .08em;
            }
            .qa-brand-copy {
                min-width: 0;
            }
            .qa-brand-wordmark {
                color: #ffffff;
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.05rem;
                font-weight: 700;
                letter-spacing: .12em;
            }
            .qa-brand-subunit {
                color: rgba(236,247,252,.86);
                font-size: .76rem;
                text-transform: uppercase;
                letter-spacing: .08em;
            }
            .qa-export-banner {
                display: none;
                padding: .95rem 1rem;
                border-radius: 14px;
                background: linear-gradient(135deg, rgba(255,255,255,.16), rgba(255,255,255,.06));
                border: 1px solid rgba(255,255,255,.14);
            }
            .qa-export-banner-row {
                display: flex;
                align-items: center;
                gap: .9rem;
            }
            .qa-export-banner-media {
                flex: 0 0 auto;
            }
            .qa-export-banner-copy {
                min-width: 0;
            }
            .qa-export-banner-kicker {
                color: #d7ebf2;
                font-size: .72rem;
                font-weight: 700;
                letter-spacing: .14em;
                text-transform: uppercase;
                margin-bottom: .3rem;
            }
            .qa-export-banner-title {
                color: #ffffff;
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.05rem;
                font-weight: 700;
                line-height: 1.2;
                margin-bottom: .2rem;
            }
            .qa-export-banner-subtitle {
                color: rgba(236,247,252,.9);
                font-size: .82rem;
                max-width: 74ch;
            }
            .qa-shell-toolbar .card-body {
                display: grid;
                gap: .4rem;
            }
            .qa-control-card {
                border-radius: 14px;
            }
            .qa-export-actions {
                display: flex;
                align-items: center;
                height: 100%;
            }
            .qa-print-button {
                width: 100%;
                min-height: 40px;
                border: 1px solid rgba(11,42,74,.14);
                border-radius: 10px;
                background: linear-gradient(180deg, #ffffff, #f0f5fa);
                color: var(--brand-navy);
                font-weight: 600;
                letter-spacing: .01em;
            }
            .qa-print-button:hover {
                background: linear-gradient(180deg, #ffffff, #e7eff7);
            }
            .qa-filter-row {
                padding: .55rem .35rem .2rem;
                border-top: 1px solid rgba(157,180,199,.42);
                border-bottom: 1px solid rgba(157,180,199,.42);
            }
            .qa-section-title {
                color: var(--brand-navy);
                text-transform: uppercase;
                letter-spacing: .05em;
                font-size: .82rem;
                margin-bottom: .45rem;
            }
            .qa-section-title-muted {
                color: #587087;
            }
            .qa-kpi-zone {
                border-bottom: 1px solid rgba(157,180,199,.35);
                padding-bottom: .35rem;
            }
            .qa-secondary-kpis {
                opacity: .92;
            }
            .qa-export-section {
                margin-bottom: 1rem;
                break-inside: avoid;
                page-break-inside: avoid;
            }
            .qa-export-section--secondary {
                opacity: .84;
            }
            .qa-export-ready {
                background: #f5f8fb;
            }
            .qa-export-ready .qa-export-banner {
                display: block;
            }
            .qa-export-ready .qa-hero {
                box-shadow: 0 8px 18px rgba(9,26,45,.2);
            }
            .qa-export-ready .qa-panel {
                box-shadow: 0 4px 12px rgba(16,34,47,.08);
                border-color: rgba(157,180,199,.62);
            }
            .qa-export-ready .qa-filter-row {
                display: none;
            }
            .qa-export-ready .qa-kpi-zone {
                border-bottom-color: rgba(157,180,199,.55);
            }
            .qa-export-ready .qa-section-title {
                margin-top: .5rem !important;
                margin-bottom: .65rem !important;
                font-size: .88rem;
                letter-spacing: .08em;
            }
            .qa-export-ready .qa-export-section--secondary {
                display: none;
            }
            .qa-report-header .card-body {
                display: grid;
                gap: .45rem;
            }
            .qa-export-ready .modebar {
                display: none !important;
            }
      .qa-panel {
                border: 1px solid rgba(157,180,199,.48);
        border-radius: 16px;
                background: rgba(255,255,255,.94);
                box-shadow: 0 9px 22px rgba(16,34,47,.08);
      }
            .qa-kpi-card,
            .qa-chart-card,
            .qa-table-card,
            .qa-hero,
            .qa-export-banner {
                    break-inside: avoid;
                    page-break-inside: avoid;
            }
            .qa-chart-card .card-body,
            .qa-table-card .card-body {
                    padding: 1rem 1rem .9rem;
            }
      .qa-kpi-value {
                font-family: 'Space Grotesk', sans-serif;
                font-size: clamp(1.8rem, 3.2vw, 2.35rem);
        font-weight: 700;
                line-height: 1.05;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: clip;
                font-variant-numeric: tabular-nums;
      }
      .qa-subtitle {
                color: #405465;
                font-size: .78rem;
                letter-spacing: .02em;
      }
            @media print {
                @page {
                    size: A4 landscape;
                    margin: 12mm;
                }
                body {
                    background: #ffffff !important;
                }
                .qa-shell {
                    padding: 0;
                    max-width: none;
                }
                .qa-hero {
                    box-shadow: none;
                    border: 1px solid #c7d4df;
                    break-after: avoid;
                    page-break-after: avoid;
                }
                .qa-panel {
                    box-shadow: none;
                    border: 1px solid #c7d4df;
                    background: #ffffff;
                }
                .qa-filter-row,
                .qa-export-controls,
                .qa-presentation-toggle,
                #language-selector,
                #presentation-mode-toggle {
                    display: none !important;
                }
                .qa-export-banner {
                    display: block !important;
                    background: #ffffff;
                    border-color: #c7d4df;
                }
                .qa-logo-badge {
                    border-color: #c7d4df;
                    box-shadow: none;
                }
                .qa-export-banner-kicker,
                .qa-export-banner-title,
                .qa-export-banner-subtitle {
                    color: #10222f;
                }
                .qa-export-section--secondary {
                    display: none !important;
                }
                .qa-export-section--weekly,
                .qa-export-section--risk,
                .qa-export-section--historical,
                .qa-export-section--analysis,
                .qa-export-section--report,
                .qa-export-section--summary {
                    break-before: page;
                    page-break-before: always;
                }
                .qa-export-section {
                    break-inside: avoid;
                    page-break-inside: avoid;
                    margin-bottom: 8mm;
                }
                .qa-chart-card,
                .qa-table-card,
                .qa-kpi-card {
                    break-inside: avoid;
                    page-break-inside: avoid;
                }
                .modebar,
                .dash-table-pagination {
                    display: none !important;
                }
                .dash-table-container .dash-spreadsheet-container th,
                .dash-table-container .dash-spreadsheet-container td {
                    font-size: 11px !important;
                    padding: 6px 8px !important;
                }
            }
      @media (max-width: 900px) {
        .qa-shell {
          padding: 12px;
        }
                .qa-hero-topline {
                    flex-direction: column;
                }
                .qa-brand-lockup {
                    width: 100%;
                    min-width: 0;
                }
                .qa-export-banner-row {
                    align-items: flex-start;
                }
                .qa-hero-kicker {
                    letter-spacing: .11em;
                }
                .qa-hero-subtitle {
                    font-size: .82rem;
                }
        .qa-kpi-value {
                    font-size: 1.65rem;
        }
      }
    </style>
  </head>
  <body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
  </body>
</html>
"""


if __name__ == "__main__":
    dash_host = os.getenv("DASH_HOST", "0.0.0.0")
    dash_port = int(os.getenv("DASH_PORT", "8050"))
    dash_debug = os.getenv("DASH_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    app.run(debug=dash_debug, host=dash_host, port=dash_port)
