"""Overview page for QA dashboard."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.export_shell import brand_lockup, export_banner
from dashboard.i18n import t


_GRAPH_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "toggleSpikelines",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "autoScale2d",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "qa_platform_chart",
        "height": 1080,
        "width": 1920,
        "scale": 2,
    },
}


def _filter_dropdown(label: str, dropdown_id: str, label_id: str, placeholder: str) -> dbc.Col:
    return dbc.Col(
        [
            html.Label(label, id=label_id, className="qa-subtitle fw-semibold mb-1"),
            dcc.Dropdown(
                id=dropdown_id,
                options=[],
                placeholder=placeholder,
                clearable=True,
            ),
        ],
        xs=12,
        md=6,
        lg=3,
        className="mb-2",
    )


def overview_page(lang: str = "en") -> dbc.Container:
    contractor_label = t(lang, "filter.contractor")
    discipline_label = t(lang, "filter.discipline")
    system_label = t(lang, "filter.system")
    week_label = t(lang, "filter.week")

    return dbc.Container(
        fluid=True,
        children=[
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        brand_lockup(lang),
                                        html.Div(
                                            [
                                                html.Div(t(lang, "hero.kicker"), id="hero-kicker", className="qa-hero-kicker mb-1"),
                                                html.H2(t(lang, "hero.title"), id="hero-title", className="qa-page-title mb-1"),
                                                html.Div(t(lang, "hero.subtitle"), id="hero-subtitle", className="qa-hero-subtitle"),
                                            ],
                                            className="qa-hero-copy",
                                        ),
                                    ],
                                    className="qa-hero-topline",
                                ),
                                export_banner(lang),
                            ]
                        ),
                        className="qa-panel qa-hero mb-3",
                    )
                )
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Label(t(lang, "filter.history_mode"), id="management-history-label", className="qa-subtitle fw-semibold mb-1"),
                                    dbc.Checklist(
                                        id="management-history-toggle",
                                        options=[{"label": t(lang, "history.mode_hint"), "value": "on"}],
                                        value=[],
                                        switch=True,
                                        className="qa-presentation-toggle",
                                    ),
                                ]
                            ),
                            className="qa-panel qa-control-card h-100",
                        ),
                        xs=12,
                        md=6,
                        lg=4,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Label(t(lang, "lang.selector"), className="qa-subtitle fw-semibold mb-1"),
                                    dcc.Dropdown(
                                        id="language-selector",
                                        options=[
                                            {"label": t(lang, "lang.en"), "value": "en"},
                                            {"label": t(lang, "lang.es"), "value": "es"},
                                        ],
                                        value=lang,
                                        clearable=False,
                                        searchable=False,
                                    ),
                                ]
                            ),
                            className="qa-panel qa-control-card h-100",
                        ),
                        xs=12,
                        md=6,
                        lg=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Label(t(lang, "presentation.mode"), id="presentation-mode-label", className="qa-subtitle fw-semibold mb-1"),
                                    dbc.Checklist(
                                        id="presentation-mode-toggle",
                                        options=[{"label": t(lang, "presentation.hint"), "value": "on"}],
                                        value=[],
                                        switch=True,
                                        className="qa-presentation-toggle",
                                    ),
                                ]
                            ),
                            className="qa-panel qa-control-card h-100",
                        ),
                        xs=12,
                        md=6,
                        lg=5,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Label(t(lang, "filter.scope"), id="scope-selector-label", className="qa-subtitle fw-semibold mb-1"),
                                    dbc.RadioItems(
                                        id="scope-selector",
                                        options=[],
                                        value="reduced",
                                        className="qa-scope-radio",
                                    ),
                                ]
                            ),
                            className="qa-panel qa-control-card h-100",
                        ),
                        xs=12,
                        md=6,
                        lg=4,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Label(t(lang, "export.print.label"), className="qa-subtitle fw-semibold mb-1"),
                                    html.Div(
                                        [
                                            html.Button(
                                                [
                                                    html.I(className="bi bi-printer me-2", **{"aria-hidden": "true"}),
                                                    html.Span(t(lang, "export.print.action"), id="print-action-label"),
                                                ],
                                                id="print-action",
                                                n_clicks=0,
                                                className="qa-print-button",
                                            ),
                                            html.Div(id="print-action-status", className="d-none"),
                                        ],
                                        className="qa-export-actions",
                                    ),
                                ]
                            ),
                            className="qa-panel qa-control-card h-100",
                        ),
                        xs=12,
                        lg=4,
                        className="mb-2",
                    ),
                ],
                className="mb-2 qa-export-controls qa-shell-toolbar",
            ),
            dbc.Row(
                [
                    _filter_dropdown(
                        contractor_label,
                        "filter-contractor",
                        "filter-contractor-label",
                        t(lang, "filter.placeholder", label=contractor_label.lower()),
                    ),
                    _filter_dropdown(
                        discipline_label,
                        "filter-discipline",
                        "filter-discipline-label",
                        t(lang, "filter.placeholder", label=discipline_label.lower()),
                    ),
                    _filter_dropdown(
                        system_label,
                        "filter-system",
                        "filter-system-label",
                        t(lang, "filter.placeholder", label=system_label.lower()),
                    ),
                    _filter_dropdown(
                        week_label,
                        "filter-week",
                        "filter-week-label",
                        t(lang, "filter.placeholder", label=week_label.lower()),
                    ),
                    _filter_dropdown(
                        t(lang, "filter.compare_week"),
                        "filter-compare-week",
                        "filter-compare-week-label",
                        t(lang, "filter.placeholder", label=t(lang, "filter.compare_week").lower()),
                    ),
                ],
                className="mb-3 qa-filter-row",
            ),
            # ── TOP: Executive Status ──────────────────────────────────────────
            html.Section(
                [
                    html.H5(t(lang, "section.exec_status"), id="section-exec-status", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="exec-status-header", className="mb-2"),
                ],
                id="section-wrap-exec-status",
                className="qa-export-section qa-export-section--exec-status",
            ),
            # ── TOP: Key Risk KPIs ─────────────────────────────────────────────
            html.Section(
                [
                    html.H5(t(lang, "section.risk_exceptions"), id="section-risk-exceptions", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="risk-exception-kpis", className="mb-3 qa-kpi-zone"),
                ],
                id="section-wrap-risk-exceptions",
                className="qa-export-section qa-export-section--risk-kpis",
            ),
            # ── TOP: Recommended Actions ───────────────────────────────────────
            html.Section(
                [
                    html.H5(t(lang, "section.recommended_actions"), id="section-recommended-actions", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="recommended-actions-block", className="mb-3"),
                ],
                id="section-wrap-recommended-actions",
                className="qa-export-section qa-export-section--actions",
            ),
            # ── MIDDLE: Top Backlog Risks ──────────────────────────────────────
            html.Section(
                [
                    html.H5(t(lang, "section.top_backlog_risks"), id="section-top-backlog-risks", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="physical-signal-exceptions", className="mb-3"),
                    dbc.Row(
                        [
                            dbc.Col(html.Div(id="backlog-aging-summary", className="mb-3"), xs=12, lg=6),
                            dbc.Col(html.Div(id="stagnant-groups-summary", className="mb-3"), xs=12, lg=6),
                        ]
                    ),
                ],
                id="section-wrap-top-backlog-risks",
                className="qa-export-section qa-export-section--risk",
            ),
            # ── Executive Overview KPIs ────────────────────────────────────────
            html.Section(
                [
                    html.H5(t(lang, "section.executive_overview"), id="section-executive-overview", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="executive-kpis", className="mb-4 qa-kpi-zone"),
                ],
                id="section-wrap-executive-overview",
                className="qa-export-section qa-export-section--overview",
            ),
            # ── BOTTOM: Trends (1 weekly + 1 cumulative) ──────────────────────
            html.Section(
                [
                    html.H5(t(lang, "section.weekly_management"), id="section-weekly-management", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="weekly-management-kpis", className="mb-3 qa-kpi-zone"),
                    html.H6(t(lang, "section.physical_signal"), id="section-physical-signal", className="qa-section-title qa-section-title-muted mt-1 mb-2"),
                    html.Div(id="physical-signal-kpis", className="mb-3 qa-kpi-zone"),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="physical-signal-weekly-graph", config=_GRAPH_CONFIG, style={"height": "320px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                className="mb-3",
                            ),
                        ]
                    ),
                    # Primary trend charts: 1 weekly dossiers + 1 cumulative
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="weekly-release-count-graph", config=_GRAPH_CONFIG, style={"height": "340px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=6,
                                className="mb-3",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="cumulative-approved-growth-graph", config=_GRAPH_CONFIG, style={"height": "340px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=6,
                                className="mb-3",
                            ),
                        ]
                    ),
                    # Secondary charts kept in DOM (hidden) to satisfy callback outputs
                    html.Div(
                        [
                            dcc.Graph(id="weekly-release-weight-graph", config=_GRAPH_CONFIG),
                            dcc.Graph(id="cumulative-release-weight-graph", config=_GRAPH_CONFIG),
                        ],
                        style={"display": "none"},
                    ),
                ],
                id="section-wrap-weekly-management",
                className="qa-export-section qa-export-section--weekly",
            ),
            html.Section(
                [
                    html.H5(t(lang, "section.historical_comparison"), id="section-historical-comparison", className="qa-section-title mt-1 mb-2"),
                    html.Div(id="historical-comparison-kpis", className="mb-3 qa-kpi-zone"),
                    html.Div(id="physical-signal-comparison-table", className="mb-3"),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="snapshot-release-trend-graph", config=_GRAPH_CONFIG, style={"height": "320px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=6,
                                className="mb-3",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="snapshot-backlog-trend-graph", config=_GRAPH_CONFIG, style={"height": "320px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=6,
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="snapshot-approval-trend-graph", config=_GRAPH_CONFIG, style={"height": "320px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=6,
                                className="mb-3",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="snapshot-weight-trend-graph", config=_GRAPH_CONFIG, style={"height": "320px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=6,
                                className="mb-3",
                            ),
                        ]
                    ),
                ],
                id="section-wrap-historical-comparison",
                className="qa-export-section qa-export-section--historical",
            ),
            html.Section(
                [
                    html.H5(t(lang, "section.dossier_analysis"), id="section-dossier-analysis", className="qa-section-title mt-1 mb-2"),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="weekly-progress-graph", config=_GRAPH_CONFIG, style={"height": "430px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=7,
                                className="mb-3",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="weekly-accum-graph", config=_GRAPH_CONFIG, style={"height": "430px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=5,
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="stage-status-graph", config=_GRAPH_CONFIG, style={"height": "350px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=7,
                                className="mb-3",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="block-status-graph", config=_GRAPH_CONFIG, style={"height": "350px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=5,
                                className="mb-3",
                            ),
                        ]
                    ),
                ],
                id="section-wrap-dossier-analysis",
                className="qa-export-section qa-export-section--analysis",
            ),
            html.Section(
                [
                    html.H5(t(lang, "section.new_contract"), id="section-new-contract", className="qa-section-title mt-1 mb-2"),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="new-contract-progress-graph", config=_GRAPH_CONFIG, style={"height": "400px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=7,
                                className="mb-3",
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(dcc.Graph(id="new-contract-timeline-graph", config=_GRAPH_CONFIG, style={"height": "400px"})),
                                    className="qa-panel qa-chart-card h-100",
                                ),
                                xs=12,
                                lg=5,
                                className="mb-3",
                            ),
                        ]
                    ),
                ],
                id="section-wrap-new-contract",
                className="qa-export-section qa-export-section--new-contract",
            ),
            html.Section(
                [
                    html.H5(t(lang, "section.executive_report_pack"), id="section-executive-report-pack", className="qa-section-title mt-2 mb-2"),
                    html.Div(id="executive-report-pack", className="mb-4"),
                ],
                id="section-wrap-executive-report-pack",
                className="qa-export-section qa-export-section--report",
            ),
            html.Section(
                [
                    html.H5(t(lang, "section.executive_summary"), id="section-executive-summary", className="qa-section-title mt-2 mb-2"),
                    html.Div(id="executive-summary-table", className="mb-4"),
                ],
                id="section-wrap-executive-summary",
                className="qa-export-section qa-export-section--summary",
            ),
            html.Section(
                [
                    html.H5(
                        t(lang, "section.quality_signals"),
                        id="section-quality-signals",
                        className="qa-section-title qa-section-title-muted mt-2 mb-1",
                    ),
                    html.Div(id="quality-kpis", className="mb-1 qa-secondary-kpis"),
                ],
                id="section-wrap-quality-signals",
                className="qa-export-section qa-export-section--secondary",
            ),
        ],
    )
