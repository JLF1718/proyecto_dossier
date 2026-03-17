"""Main layout for the QA dashboard starter app."""

from __future__ import annotations

from dash import dcc, html

from dashboard.i18n import DEFAULT_LANG
from dashboard.pages.overview import overview_page


def create_layout() -> html.Div:
    return html.Div(
        id="qa-shell-root",
        className="qa-shell",
        children=[
            dcc.Location(id="dashboard-url", refresh=False),
            dcc.Store(id="language-store", storage_type="session", data={"lang": DEFAULT_LANG}),
            overview_page(DEFAULT_LANG),
        ],
    )
