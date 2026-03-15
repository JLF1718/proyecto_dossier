"""Card components for KPI sections."""

from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
from dash import html


def _kpi_card(title: str, value: Any, subtitle: str, tone: str) -> dbc.Col:
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(title, className="text-uppercase qa-subtitle"),
                    html.Div(str(value), className=f"qa-kpi-value text-{tone}"),
                    html.Div(subtitle, className="qa-subtitle"),
                ]
            ),
            className="qa-panel h-100",
        ),
        xs=12,
        md=6,
        lg=3,
        className="mb-3",
    )


def executive_cards(kpis: Dict[str, Any]) -> dbc.Row:
    """Render the four Executive Overview KPI cards.

    Accepts the payload returned by ``/api/dossiers/kpis`` (new canonical keys)
    or the legacy ``{total, pending, rejected, approved}`` dict for backward
    compatibility.
    """
    total = kpis.get("total_dossiers", kpis.get("total", 0))
    approved = kpis.get("approved_dossiers", kpis.get("approved", 0))
    pending = kpis.get("pending_dossiers", kpis.get("pending", 0))
    in_review = kpis.get("in_review_dossiers", 0)

    pct_approved = f"{approved / total * 100:.1f}% del total" if total else "—"

    return dbc.Row(
        [
            _kpi_card("Total dossieres", total, "En alcance contractual", "primary"),
            _kpi_card("Aprobados", approved, pct_approved, "success"),
            _kpi_card("Pendientes", pending, "Por revisar o completar", "warning"),
            _kpi_card("En revisión", in_review, "Revisión interna INPROS", "info"),
        ]
    )


def quality_cards(kpis: Dict[str, Any], weld_metrics: Dict[str, Any]) -> dbc.Row:
    total = max(int(kpis.get("total_dossiers", kpis.get("total", 0))), 1)
    rejected = int(kpis.get("rejected_dossiers", kpis.get("rejected", 0)))
    pending = int(kpis.get("pending_dossiers", kpis.get("pending", 0)))

    rejection_rate = rejected / total * 100
    inspection_coverage = float(weld_metrics.get("acceptance_rate_pct", 0)) + float(
        weld_metrics.get("rejection_rate_pct", 0)
    )
    pending_deliverables = pending

    return dbc.Row(
        [
            _kpi_card("Rejection rate", f"{rejection_rate:.1f}%", "Sobre dossiers filtrados", "danger"),
            _kpi_card("Inspection coverage", f"{inspection_coverage:.1f}%", "Soldaduras inspeccionadas", "info"),
            _kpi_card("Pending deliverables", pending_deliverables, "Entregables por cerrar", "warning"),
        ]
    )
