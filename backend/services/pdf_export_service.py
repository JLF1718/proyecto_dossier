"""Deterministic server-side executive PDF export using Playwright."""

from __future__ import annotations

import os
import time
from typing import Optional
from urllib.parse import urlencode

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

_DASHBOARD_BASE_URL = os.getenv("QA_DASHBOARD_EXPORT_URL", "http://127.0.0.1:8050")
_PAGE_TIMEOUT_MS = int(os.getenv("QA_EXPORT_PAGE_TIMEOUT_MS", "120000"))
_CHART_WAIT_TIMEOUT_MS = int(os.getenv("QA_EXPORT_CHART_WAIT_TIMEOUT_MS", "45000"))


def _is_enabled(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_dashboard_url(
    *,
    lang: Optional[str],
    contractor: Optional[str],
    discipline: Optional[str],
    system: Optional[str],
    week: Optional[str],
    compare_week: Optional[str],
    history_mode: bool,
) -> str:
    params: dict[str, str] = {
        "export": "1",
        "presentation": "1",
    }

    if lang:
        params["lang"] = str(lang)
    if contractor:
        params["contractor"] = str(contractor)
    if discipline:
        params["discipline"] = str(discipline)
    if system:
        params["system"] = str(system)
    if week:
        params["week"] = str(week)
    if compare_week:
        params["compare_week"] = str(compare_week)
    if history_mode:
        params["history"] = "1"

    base = _DASHBOARD_BASE_URL.rstrip("/") + "/"
    return f"{base}?{urlencode(params)}"


def _wait_for_plotly_stability(page) -> None:
    page.wait_for_selector("#qa-shell-root.qa-export-ready", timeout=_CHART_WAIT_TIMEOUT_MS)

    try:
        page.wait_for_selector(".js-plotly-plot", timeout=_CHART_WAIT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        # Some low-value exports may hide chart sections; allow PDF generation to continue.
        return

    # Trigger repeated resize passes so Plotly fills final print layout width before capture.
    page.evaluate(
        """
        async () => {
            const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
            for (let i = 0; i < 5; i += 1) {
                const plots = document.querySelectorAll('.js-plotly-plot');
                plots.forEach((el) => {
                    try {
                        if (window.Plotly && window.Plotly.Plots) {
                            window.Plotly.Plots.resize(el);
                        }
                    } catch (err) {
                        // Ignore individual chart resize failures and continue.
                    }
                });
                await sleep(140);
            }
            await sleep(220);
        }
        """
    )


def generate_executive_pdf(
    *,
    lang: Optional[str],
    contractor: Optional[str],
    discipline: Optional[str],
    system: Optional[str],
    week: Optional[str],
    compare_week: Optional[str],
    history_mode: Optional[str],
) -> bytes:
    export_url = _build_dashboard_url(
        lang=lang,
        contractor=contractor,
        discipline=discipline,
        system=system,
        week=week,
        compare_week=compare_week,
        history_mode=_is_enabled(history_mode, default=False),
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US")
        page = context.new_page()

        try:
            page.goto(export_url, wait_until="networkidle", timeout=_PAGE_TIMEOUT_MS)
            _wait_for_plotly_stability(page)
            time.sleep(0.2)

            pdf_bytes = page.pdf(
                landscape=True,
                print_background=True,
                display_header_footer=False,
                prefer_css_page_size=True,
                scale=0.92,
                margin={
                    "top": "8mm",
                    "right": "8mm",
                    "bottom": "8mm",
                    "left": "8mm",
                },
            )
            return pdf_bytes
        finally:
            context.close()
            browser.close()
