"""
Dashboard Callbacks — Dossier Control
=======================================
Registers all interactive Dash callbacks for the Dossier Control page.

Data flow:
  Filters (dropdowns) → fetch from FastAPI /api/dossiers → update charts/KPIs

The dashboard calls the FastAPI backend so both services can run independently.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dash import Input, Output, State, callback, dash_table, html
import dash_bootstrap_components as dbc

from dashboard.components.kpi_cards import kpi_row
from modules.dossier_control.dashboard import (
    make_status_bar,
    make_stage_status_bar,
    make_timeline,
    _empty_figure,
)
from modules.dossier_control.metrics import (
    get_kpis,
    get_timeline_data,
)
from analytics.metrics import compute_global_metrics

# Backend base URL — configurable via env so it works behind nginx
_API_BASE = os.getenv("QA_API_BASE", "http://127.0.0.1:8000")
_TIMEOUT = 10  # seconds


def _fetch_dossiers(
    contractor: str = "ALL",
    estatus: str = "ALL",
    etapa: str = "ALL",
    entrega: str = "ALL",
) -> pd.DataFrame:
    """Fetch dossier records from the FastAPI backend and return as DataFrame."""
    params: Dict[str, str] = {"limit": "5000"}
    if contractor != "ALL":
        params["contratista"] = contractor
    if estatus != "ALL":
        params["estatus"] = estatus
    if etapa != "ALL":
        params["etapa"] = etapa
    if entrega != "ALL":
        params["entrega"] = entrega

    try:
        resp = requests.get(f"{_API_BASE}/api/dossiers", params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return pd.DataFrame(items) if items else pd.DataFrame()
    except Exception:
        # Fallback: load directly from modules (useful when backend is not yet started)
        from modules.dossier_control.data_loader import load_consolidated  # noqa: PLC0415
        df = load_consolidated()

        if contractor != "ALL" and "CONTRATISTA" in df.columns:
            df = df[df["CONTRATISTA"] == contractor]
        if estatus != "ALL" and "ESTATUS" in df.columns:
            df = df[df["ESTATUS"] == estatus]
        if etapa != "ALL" and "ETAPA" in df.columns:
            df = df[df["ETAPA"] == etapa]
        if entrega != "ALL" and "ENTREGA" in df.columns:
            df = df[df["ENTREGA"] == entrega]
        return df


def _fetch_metrics(contractor: str = "ALL") -> Dict[str, Any]:
    """Fetch KPI metrics from the FastAPI backend."""
    path = "/api/metrics" if contractor == "ALL" else f"/api/metrics/{contractor}"
    try:
        resp = requests.get(f"{_API_BASE}{path}", timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        df = _fetch_dossiers(contractor)
        return compute_global_metrics(df)


def register_callbacks(app) -> None:
    """Attach all dossier-related callbacks to the Dash app instance."""

    # ── Delivery week options (dynamic from data) ─────────────────────────────

    @app.callback(
        Output("filter-delivery", "options"),
        Input("filter-contractor", "value"),
    )
    def update_delivery_options(contractor: str) -> List[Dict[str, str]]:
        df = _fetch_dossiers(contractor)
        options = [{"label": "Todas", "value": "ALL"}]
        if not df.empty and "ENTREGA" in df.columns:
            semanas = sorted(df["ENTREGA"].dropna().unique().tolist())
            options += [{"label": s, "value": s} for s in semanas]
        return options

    # ── KPI strip ─────────────────────────────────────────────────────────────

    @app.callback(
        Output("kpi-row", "children"),
        [
            Input("filter-contractor", "value"),
            Input("filter-status", "value"),
            Input("filter-stage", "value"),
            Input("filter-delivery", "value"),
            Input("btn-refresh", "n_clicks"),
        ],
    )
    def update_kpis(contractor, estatus, etapa, entrega, _n):
        df = _fetch_dossiers(contractor, estatus, etapa, entrega)
        kpis = compute_global_metrics(df)
        return kpi_row(kpis)

    # ── Status bar chart ──────────────────────────────────────────────────────

    @app.callback(
        Output("chart-status-bar", "figure"),
        [
            Input("filter-contractor", "value"),
            Input("filter-status", "value"),
            Input("filter-stage", "value"),
            Input("filter-delivery", "value"),
            Input("btn-refresh", "n_clicks"),
        ],
    )
    def update_status_bar(contractor, estatus, etapa, entrega, _n):
        df = _fetch_dossiers(contractor, estatus, etapa, entrega)
        return make_status_bar(df)

    # ── Stage × Status grouped bar ────────────────────────────────────────────

    @app.callback(
        Output("chart-stage-status", "figure"),
        [
            Input("filter-contractor", "value"),
            Input("filter-status", "value"),
            Input("filter-stage", "value"),
            Input("filter-delivery", "value"),
            Input("btn-refresh", "n_clicks"),
        ],
    )
    def update_stage_status(contractor, estatus, etapa, entrega, _n):
        df = _fetch_dossiers(contractor, estatus, etapa, entrega)
        return make_stage_status_bar(df, mode="count")

    # ── Weight by stage ───────────────────────────────────────────────────────

    @app.callback(
        Output("chart-weight-stage", "figure"),
        [
            Input("filter-contractor", "value"),
            Input("filter-status", "value"),
            Input("filter-stage", "value"),
            Input("filter-delivery", "value"),
            Input("btn-refresh", "n_clicks"),
        ],
    )
    def update_weight_stage(contractor, estatus, etapa, entrega, _n):
        df = _fetch_dossiers(contractor, estatus, etapa, entrega)
        return make_stage_status_bar(df, mode="weight")

    # ── Timeline chart ────────────────────────────────────────────────────────

    @app.callback(
        Output("chart-timeline", "figure"),
        [
            Input("filter-contractor", "value"),
            Input("filter-status", "value"),
            Input("filter-stage", "value"),
            Input("filter-delivery", "value"),
            Input("btn-refresh", "n_clicks"),
        ],
    )
    def update_timeline(contractor, estatus, etapa, entrega, _n):
        df = _fetch_dossiers(contractor, estatus, etapa, entrega)
        timeline = get_timeline_data(df)
        return make_timeline(timeline)

    # ── Data table ────────────────────────────────────────────────────────────

    @app.callback(
        Output("dossier-table", "children"),
        [
            Input("filter-contractor", "value"),
            Input("filter-status", "value"),
            Input("filter-stage", "value"),
            Input("filter-delivery", "value"),
            Input("btn-refresh", "n_clicks"),
        ],
    )
    def update_table(contractor, estatus, etapa, entrega, _n):
        df = _fetch_dossiers(contractor, estatus, etapa, entrega)
        if df.empty:
            return html.P("Sin datos para los filtros seleccionados.", className="text-muted")

        display_cols = [
            c for c in ["CONTRATISTA", "BLOQUE", "ETAPA", "ESTATUS", "PESO", "ENTREGA"]
            if c in df.columns
        ]
        return dash_table.DataTable(
            data=df[display_cols].head(500).to_dict("records"),
            columns=[{"name": c, "id": c} for c in display_cols],
            page_size=20,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"fontSize": "12px", "padding": "6px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            style_data_conditional=[
                {"if": {"filter_query": '{ESTATUS} = "LIBERADO"'}, "color": "#0F7C3F"},
                {"if": {"filter_query": '{ESTATUS} = "OBSERVADO"'}, "color": "#D0021B"},
                {"if": {"filter_query": '{ESTATUS} = "EN_REVISIÓN"'}, "color": "#F5A623"},
            ],
        )

    # ── Page title update ────────────────────────────────────────────────────

    @app.callback(
        Output("page-title", "children"),
        Input("url", "pathname"),
    )
    def update_page_title(pathname: str) -> str:
        titles = {
            "/": "Inicio — QA Platform",
            "/dossiers": "Control de Dossieres",
            "/soldadura": "Control de Soldadura",
            "/concreto": "Control de Concreto",
            "/nc": "Gestión de No Conformidades",
        }
        return titles.get(pathname, "QA Platform")
