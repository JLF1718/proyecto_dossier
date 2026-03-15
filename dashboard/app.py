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
import requests
from dash import Input, Output

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.components.cards import executive_cards, quality_cards
from dashboard.components.figures import empty_figure, progress_figure, welding_figure
from dashboard.layout import create_layout

API_BASE_URL = os.getenv("QA_API_BASE_URL", os.getenv("QA_API_BASE", "http://127.0.0.1:8000"))
API_ACCESS_KEY = os.getenv("API_ACCESS_KEY", "").strip()
REQUEST_TIMEOUT = float(os.getenv("QA_API_TIMEOUT", "8"))


def _api_headers() -> Dict[str, str]:
    if not API_ACCESS_KEY:
        return {}
    return {"X-Access-Key": API_ACCESS_KEY}


def _fetch_dossiers(contractor: Optional[str], week: Optional[str]) -> pd.DataFrame:
    params: Dict[str, Any] = {"limit": 5000, "skip": 0}
    if contractor:
        params["contratista"] = contractor
    if week:
        params["entrega"] = week

    response = requests.get(
        f"{API_BASE_URL}/api/dossiers",
        params=params,
        headers=_api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return pd.DataFrame(payload.get("items", []))


def _fetch_weld_metrics(contractor: Optional[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if contractor:
        params["contratista"] = contractor

    response = requests.get(
        f"{API_BASE_URL}/api/welds/metrics",
        params=params,
        headers=_api_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if "message" in data:
        return {}
    return data


def _fetch_dossier_kpis() -> Dict[str, Any]:
    """Fetch contractual KPI counts from ``/api/dossiers/kpis``.

    Falls back to computing locally from the processed CSV when the backend is
    unavailable, so the dashboard remains functional during standalone runs.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/dossiers/kpis",
            headers=_api_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return _normalize_kpi_payload(resp.json())
    except Exception:
        from backend.services.dossier_service import compute_kpis, load_dossiers

        return _normalize_kpi_payload(compute_kpis(load_dossiers("BAYSA")))


def _normalize_kpi_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize KPI payload to the canonical dashboard schema.

    Expected keys:
        total_dossiers, approved_dossiers, pending_dossiers, in_review_dossiers
    """
    if not isinstance(payload, dict):
        payload = {}

    normalized = dict(payload)
    normalized["total_dossiers"] = int(payload.get("total_dossiers", payload.get("total", 0)) or 0)
    normalized["approved_dossiers"] = int(payload.get("approved_dossiers", payload.get("approved", 0)) or 0)
    normalized["pending_dossiers"] = int(payload.get("pending_dossiers", payload.get("pending", 0)) or 0)
    normalized["in_review_dossiers"] = int(payload.get("in_review_dossiers", payload.get("in_review", 0)) or 0)
    normalized["rejected_dossiers"] = int(payload.get("rejected_dossiers", payload.get("rejected", 0)) or 0)
    return normalized


def _status_metrics(df: pd.DataFrame) -> Dict[str, int]:
    if df.empty or "ESTATUS" not in df.columns:
        return {"total": 0, "pending": 0, "rejected": 0, "approved": 0}

    series = df["ESTATUS"].fillna("").astype(str).str.upper().str.strip()
    approved = int(series.isin(["LIBERADO", "APROBADO", "ACEPTADO"]).sum())
    rejected = int(series.isin(["OBSERVADO", "RECHAZADO"]).sum())
    pending = int(series.isin(["PLANEADO", "EN_REVISIÓN", "EN REVISION", "PENDIENTE"]).sum())

    # Unknown statuses are counted as pending to avoid dropping data.
    other = len(series) - approved - rejected - pending
    pending += max(other, 0)

    return {
        "total": int(len(series)),
        "pending": pending,
        "rejected": rejected,
        "approved": approved,
    }


def _safe_options(df: pd.DataFrame, columns: list[str]) -> list[dict[str, str]]:
    for col in columns:
        if col in df.columns:
            values = sorted(v for v in df[col].dropna().astype(str).unique() if v.strip())
            return [{"label": v, "value": v} for v in values]
    return []


def _apply_local_filters(
    df: pd.DataFrame,
    discipline: Optional[str],
    system: Optional[str],
) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    if discipline:
        if "DISCIPLINA" in out.columns:
            out = out[out["DISCIPLINA"].astype(str) == discipline]
        elif "ETAPA" in out.columns:
            out = out[out["ETAPA"].astype(str) == discipline]

    if system and "SISTEMA" in out.columns:
        out = out[out["SISTEMA"].astype(str) == system]

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
    Output("quality-kpis", "children"),
    Output("progress-graph", "figure"),
    Output("welding-graph", "figure"),
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
    # KPI cards are mission-critical: keep them available even if other API calls fail.
    kpi_data = _fetch_dossier_kpis()

    dossiers_error: Optional[Exception] = None
    weld_error: Optional[Exception] = None

    try:
        df = _fetch_dossiers(contractor=contractor, week=week)
    except Exception as exc:
        dossiers_error = exc
        df = pd.DataFrame()

    try:
        weld_metrics = _fetch_weld_metrics(contractor=contractor)
    except Exception as exc:
        weld_error = exc
        weld_metrics = {}

    filtered = _apply_local_filters(df, discipline=discipline, system=system)
    contractor_options = _safe_options(df, ["CONTRATISTA"])
    discipline_options = _safe_options(df, ["DISCIPLINA", "ETAPA"])
    system_options = _safe_options(df, ["SISTEMA"])
    week_options = _safe_options(df, ["ENTREGA", "SEMANA"])

    progress_message = "No se pudo cargar la data de dossiers desde la API." if dossiers_error else "Sin datos para mostrar"
    welding_message = "No se pudo cargar la data de soldadura desde la API." if weld_error else "Sin datos para mostrar"

    return (
        contractor_options,
        discipline_options,
        system_options,
        week_options,
        executive_cards(kpi_data),
        quality_cards(kpi_data, weld_metrics),
        progress_figure(filtered) if not filtered.empty else empty_figure("Progreso de entrega", progress_message),
        welding_figure(weld_metrics) if weld_metrics else empty_figure("Inspecciones de soldadura", welding_message),
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
        --qa-ink: #10222f;
        --qa-accent: #0f7c3f;
        --qa-warning: #f3a712;
        --qa-danger: #b83227;
        --qa-surface: #f3f6f9;
      }
      body {
        margin: 0;
        color: var(--qa-ink);
        font-family: 'IBM Plex Sans', sans-serif;
        background:
          radial-gradient(circle at 90% 10%, rgba(15,124,63,.16), transparent 35%),
          radial-gradient(circle at 10% 20%, rgba(243,167,18,.15), transparent 40%),
          var(--qa-surface);
      }
      h1, h2, h3, h4, h5 {
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: .01em;
      }
      .qa-shell {
        padding: 18px;
      }
      .qa-panel {
        border: 0;
        border-radius: 16px;
        background: rgba(255,255,255,.9);
        box-shadow: 0 10px 28px rgba(16,34,47,.1);
      }
      .qa-kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
      }
      .qa-subtitle {
        color: #5d6b78;
        font-size: .86rem;
      }
      @media (max-width: 900px) {
        .qa-shell {
          padding: 12px;
        }
        .qa-kpi-value {
          font-size: 1.45rem;
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
