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
from dash import Input, Output

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.services.dossier_service import build_weekly_management_payload
from backend.services.dossier_service import compute_kpis

from dashboard.components.cards import (
    backlog_aging_summary,
    executive_cards,
    executive_summary_table,
    quality_cards,
    stagnant_groups_summary,
    weekly_management_cards,
)
from dashboard.components.figures import (
    cumulative_approved_growth_figure,
    cumulative_released_weight_growth_figure,
    derive_building_family,
    derive_stage_category,
    executive_summary_frame,
    status_by_block_figure,
    status_by_stage_figure,
    weekly_released_dossiers_figure,
    weekly_released_weight_figure,
    weekly_accumulated_progress_figure,
    weekly_progress_figure,
)
from dashboard.layout import create_layout

_PROCESSED_CSV_PATH = _PROJECT_ROOT / "data" / "processed" / "baysa_dossiers_clean.csv"

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


app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
    title="QA Platform Dashboard",
    suppress_callback_exceptions=True,
)
server = app.server
app.layout = create_layout()


@app.callback(
    Output("filter-contractor", "options"),
    Output("filter-discipline", "options"),
    Output("filter-system", "options"),
    Output("filter-week", "options"),
    Output("executive-kpis", "children"),
    Output("weekly-management-kpis", "children"),
    Output("quality-kpis", "children"),
    Output("weekly-release-count-graph", "figure"),
    Output("weekly-release-weight-graph", "figure"),
    Output("cumulative-approved-growth-graph", "figure"),
    Output("cumulative-release-weight-graph", "figure"),
    Output("backlog-aging-summary", "children"),
    Output("stagnant-groups-summary", "children"),
    Output("stage-status-graph", "figure"),
    Output("block-status-graph", "figure"),
    Output("weekly-progress-graph", "figure"),
    Output("weekly-accum-graph", "figure"),
    Output("executive-summary-table", "children"),
    Input("filter-contractor", "value"),
    Input("filter-discipline", "value"),
    Input("filter-system", "value"),
    Input("filter-week", "value"),
)
def update_dashboard(
    contractor: Optional[str],
    discipline: Optional[str],
    system: Optional[str],
    week: Optional[str],
):
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
    summary_table = executive_summary_table(executive_summary_frame(summary_filtered))
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
    discipline_options = [{"label": str(v), "value": str(v)} for v in discipline_values]

    family_values = ["PRO", "SUE", "SHARED"]
    system_options = [{"label": v, "value": v} for v in family_values]

    week_options: list[dict[str, str]] = []
    if not in_scope_df.empty and "hito_semana" in in_scope_df.columns:
        semanas = sorted(
            int(s)
            for s in pd.to_numeric(in_scope_df["hito_semana"], errors="coerce").dropna().unique()
        )
        week_options = [{"label": f"Week {s}", "value": str(s)} for s in semanas]

    return (
        contractor_options,
        discipline_options,
        system_options,
        week_options,
        executive_cards(kpi_payload),
        weekly_management_cards(weekly_payload),
        quality_cards(kpi_payload),
        weekly_released_dossiers_figure(weekly_payload),
        weekly_released_weight_figure(weekly_payload),
        cumulative_approved_growth_figure(weekly_payload),
        cumulative_released_weight_growth_figure(weekly_payload),
        backlog_aging_summary(weekly_payload),
        stagnant_groups_summary(weekly_payload),
        status_by_stage_figure(local_filtered),
        status_by_block_figure(local_filtered),
        weekly_progress_figure(local_filtered),
        weekly_accumulated_progress_figure(local_filtered),
        summary_table,
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
                --brand-line: #9db4c7;
                --qa-ink: #10222f;
                --qa-surface: #eef3f8;
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
      .qa-panel {
                border: 1px solid rgba(157,180,199,.48);
        border-radius: 16px;
                background: rgba(255,255,255,.94);
                box-shadow: 0 9px 22px rgba(16,34,47,.08);
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
      @media (max-width: 900px) {
        .qa-shell {
          padding: 12px;
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
