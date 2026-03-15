"""Main layout for the QA dashboard starter app."""

from __future__ import annotations

from dash import html

from dashboard.pages.overview import overview_page


def create_layout() -> html.Div:
    return html.Div(className="qa-shell", children=[overview_page()])
