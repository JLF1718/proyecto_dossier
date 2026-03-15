"""Card components for KPI sections."""

from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
from dash import html


def _kpi_card(
    title: str,
    value: Any,
    subtitle: str,
    tone: str,
    *,
    xs: int = 12,
    md: int = 6,
    lg: int = 3,
    xl: int | None = None,
) -> dbc.Col:
    col_kwargs: Dict[str, Any] = {
        "xs": xs,
        "md": md,
        "lg": lg,
        "className": "mb-3",
    }
    if xl is not None:
        col_kwargs["xl"] = xl

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
        **col_kwargs,
    )


def executive_cards(kpis: Dict[str, Any]) -> html.Div:
    """Render Executive Overview KPI cards in two rows.

    Accepts the payload returned by ``/api/dossiers/kpis``
    or the legacy ``{total, pending, rejected, approved}`` dict for backward
    compatibility.
    """
    total = kpis.get("total_dossiers", kpis.get("total", 0))
    approved = kpis.get("approved_dossiers", kpis.get("approved", 0))
    pending = kpis.get("pending_dossiers", kpis.get("pending", 0))
    in_review = kpis.get("in_review_dossiers", 0)

    out_of_scope = kpis.get("rows_out_of_scope", 0)
    pct_liberado = kpis.get("pct_liberado", 0)
    peso_total_ton = kpis.get("peso_total_ton", 0)
    peso_liberado_ton = kpis.get("peso_liberado_ton", 0)
    pct_peso_liberado = kpis.get("pct_peso_liberado", 0)

    pct_approved = f"{approved / total * 100:.1f}% del total" if total else "—"

    return html.Div(
        [
            dbc.Row(
                [
                    _kpi_card("Total dossieres", total, "En alcance contractual", "primary"),
                    _kpi_card("Aprobados", approved, pct_approved, "success"),
                    _kpi_card("Pendientes", pending, "Por revisar o completar", "warning"),
                    _kpi_card("En revisión", in_review, "Revisión interna INPROS", "info"),
                ]
            ),
            dbc.Row(
                [
                    _kpi_card("Fuera de alcance", out_of_scope, "Bloques excluidos del alcance", "secondary", lg=4, xl=2),
                    _kpi_card("% liberado", f"{float(pct_liberado):.1f}%", "Avance contractual", "success", lg=4, xl=2),
                    _kpi_card("Peso total (ton)", f"{float(peso_total_ton):.2f}", "Peso en alcance contractual", "primary", lg=4, xl=2),
                    _kpi_card("Peso liberado (ton)", f"{float(peso_liberado_ton):.2f}", "Peso con estatus liberado", "info", lg=4, xl=2),
                    _kpi_card("% peso liberado", f"{float(pct_peso_liberado):.1f}%", "Progreso por peso", "warning", lg=4, xl=2),
                ],
                className="mt-1",
            ),
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
