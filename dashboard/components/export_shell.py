"""Export shell helpers for executive dashboard presentation."""

from __future__ import annotations

from pathlib import Path

from dash import html

from dashboard.i18n import t

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOGO_FILENAME = "inpros-logo.png"
_LOGO_ASSET_PATH = _PROJECT_ROOT / "assets" / _LOGO_FILENAME


def _logo_media(lang: str, *, compact: bool = False) -> html.Div:
    badge_class = "qa-logo-badge qa-logo-badge--compact" if compact else "qa-logo-badge"
    if _LOGO_ASSET_PATH.exists():
        media = html.Img(
            src=f"/assets/{_LOGO_FILENAME}",
            alt=t(lang, "brand.logo_alt"),
            className="qa-brand-logo",
        )
    else:
        media = html.Div("IN", className="qa-brand-monogram", **{"aria-hidden": "true"})
    return html.Div(media, className=badge_class)


def brand_lockup(lang: str = "en") -> html.Div:
    """Return a restrained INPROS lockup with a drop-in asset slot."""
    return html.Div(
        [
            html.Div(_logo_media(lang), className="qa-brand-media"),
            html.Div(
                [
                    html.Div("INPROS", className="qa-brand-wordmark"),
                    html.Div(t(lang, "brand.subunit"), id="brand-subunit", className="qa-brand-subunit"),
                ],
                className="qa-brand-copy",
            ),
        ],
        className="qa-brand-lockup",
    )


def export_banner(lang: str = "en") -> html.Div:
    """Return the executive export banner shown in export mode."""
    return html.Div(
        [
            html.Div(
                [
                    html.Div(_logo_media(lang, compact=True), className="qa-export-banner-media"),
                    html.Div(
                        [
                            html.Div(t(lang, "export.banner.kicker"), id="export-banner-kicker", className="qa-export-banner-kicker"),
                            html.Div(t(lang, "export.banner.title"), id="export-banner-title", className="qa-export-banner-title"),
                            html.Div(t(lang, "export.banner.subtitle"), id="export-banner-subtitle", className="qa-export-banner-subtitle"),
                        ],
                        className="qa-export-banner-copy",
                    ),
                ],
                className="qa-export-banner-row",
            ),
        ],
        className="qa-export-banner",
    )