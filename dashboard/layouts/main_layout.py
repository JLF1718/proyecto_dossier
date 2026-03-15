"""
Dashboard Layout — Main Shell
==============================
Defines the top-level Dash page layout: sidebar navigation + content area.
Uses dash-bootstrap-components (DBC) with Bootstrap 5.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

# ── Sidebar navigation ────────────────────────────────────────────────────────

NAV_LINKS = [
    {"href": "/", "icon": "bi bi-house-door", "label": "Inicio"},
    {"href": "/dossiers", "icon": "bi bi-folder2-open", "label": "Control Dossieres"},
    {"href": "/soldadura", "icon": "bi bi-fire", "label": "Control Soldadura"},
    {"href": "/concreto", "icon": "bi bi-buildings", "label": "Control Concreto"},
    {"href": "/nc", "icon": "bi bi-exclamation-triangle", "label": "No Conformidades"},
]


def sidebar() -> html.Div:
    nav_items = [
        dbc.NavLink(
            [html.I(className=f"{link['icon']} me-2"), link["label"]],
            href=link["href"],
            active="exact",
            className="sidebar-link",
        )
        for link in NAV_LINKS
    ]
    return html.Div(
        [
            html.Div(
                [
                    html.I(className="bi bi-shield-check me-2 text-success", style={"fontSize": "1.4rem"}),
                    html.Span("QA Platform", className="fw-bold fs-5"),
                ],
                className="sidebar-brand d-flex align-items-center p-3 border-bottom",
            ),
            dbc.Nav(nav_items, vertical=True, pills=True, className="p-2"),
        ],
        className="sidebar bg-white border-end shadow-sm",
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "220px",
            "zIndex": 100,
            "overflowY": "auto",
        },
    )


# ── Header bar ────────────────────────────────────────────────────────────────

def navbar() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container(
            [
                html.Span(id="page-title", className="navbar-text fw-semibold text-white"),
                dbc.Button(
                    [html.I(className="bi bi-arrow-clockwise me-1"), "Actualizar"],
                    id="btn-refresh",
                    color="light",
                    size="sm",
                    outline=True,
                    className="ms-auto",
                ),
            ],
            fluid=True,
        ),
        color="#1a1a2e",
        dark=True,
        style={"marginLeft": "220px"},
    )


# ── Root layout ───────────────────────────────────────────────────────────────

def main_layout() -> html.Div:
    """Assemble the full app shell (sidebar + navbar + page content)."""
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="store-filters", storage_type="session"),
            sidebar(),
            navbar(),
            # Page content area
            html.Div(
                id="page-content",
                style={
                    "marginLeft": "220px",
                    "marginTop": "56px",  # navbar height
                    "padding": "1.5rem",
                    "backgroundColor": "#F8F9FA",
                    "minHeight": "100vh",
                },
            ),
        ]
    )
