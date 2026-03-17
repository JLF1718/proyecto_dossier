"""Document-oriented executive PPTX export pipeline for QA Platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from backend.config import get_settings
from backend.services.dossier_service import build_executive_report_payload
from backend.services.piece_signal_service import load_piece_signal_payload

PPTX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@dataclass(frozen=True)
class _Theme:
    navy: tuple[int, int, int] = (11, 45, 78)
    slate: tuple[int, int, int] = (79, 95, 115)
    light_bg: tuple[int, int, int] = (246, 248, 250)
    white: tuple[int, int, int] = (255, 255, 255)
    accent: tuple[int, int, int] = (0, 133, 119)
    warning: tuple[int, int, int] = (185, 28, 28)


def _load_pptx_symbols() -> dict[str, Any]:
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import PP_ALIGN
        from pptx.util import Inches, Pt
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "python-pptx is required for executive pack export. Install dependencies from requirements.txt"
        ) from exc

    return {
        "Presentation": Presentation,
        "RGBColor": RGBColor,
        "MSO_SHAPE": MSO_SHAPE,
        "PP_ALIGN": PP_ALIGN,
        "Inches": Inches,
        "Pt": Pt,
    }


def _load_matplotlib_plt():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "matplotlib is required for executive pack chart rendering. Install dependencies from requirements.txt"
        ) from exc
    return plt


def _rgb(rgb_color, triplet: tuple[int, int, int]):
    return rgb_color(*triplet)


def _fmt_pct(value: Any, ndigits: int = 1) -> str:
    try:
        return f"{float(value):.{ndigits}f}%"
    except Exception:
        return "-"


def _fmt_num(value: Any, ndigits: int = 0) -> str:
    try:
        if ndigits <= 0:
            return f"{int(float(value)):,}"
        return f"{float(value):,.{ndigits}f}"
    except Exception:
        return "-"


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _severity_rank(value: Any) -> int:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return order.get(str(value or "").strip().lower(), 0)


def _render_release_chart(weekly_payload: dict[str, Any]) -> BytesIO:
    plt = _load_matplotlib_plt()
    series = _safe_list(weekly_payload.get("weekly_comparison", {}).get("release_series", []))
    cumulative = _safe_list(weekly_payload.get("weekly_comparison", {}).get("cumulative_series", []))

    weeks = [int(item.get("week")) for item in series if item.get("week") is not None]
    released = [float(item.get("released_dossiers", 0.0) or 0.0) for item in series if item.get("week") is not None]
    cumulative_counts = [
        float(item.get("cumulative_approved_dossiers", 0.0) or 0.0)
        for item in cumulative
        if item.get("week") is not None
    ]
    if len(cumulative_counts) < len(weeks):
        cumulative_counts = cumulative_counts + [0.0] * (len(weeks) - len(cumulative_counts))

    fig, ax = plt.subplots(figsize=(8.2, 3.2), dpi=180)
    if weeks:
        ax.bar(weeks, released, color="#0b2d4e", width=0.75, label="Released dossiers")
        ax2 = ax.twinx()
        ax2.plot(weeks, cumulative_counts[: len(weeks)], color="#008577", linewidth=2.4, label="Cumulative approved")
        ax.set_xlabel("Week")
        ax.set_ylabel("Released")
        ax2.set_ylabel("Cumulative")
        ax.grid(axis="y", alpha=0.24)
    else:
        ax.text(0.5, 0.5, "No weekly release data", ha="center", va="center", fontsize=11)
        ax.set_axis_off()

    fig.tight_layout()
    image = BytesIO()
    fig.savefig(image, format="png", bbox_inches="tight")
    plt.close(fig)
    image.seek(0)
    return image


def _render_signal_alignment_chart(piece_payload: dict[str, Any]) -> BytesIO:
    plt = _load_matplotlib_plt()

    comparison_df = piece_payload.get("comparison")
    if not isinstance(comparison_df, pd.DataFrame):
        comparison_df = pd.DataFrame()

    fig, ax = plt.subplots(figsize=(8.2, 3.2), dpi=180)
    if comparison_df.empty:
        ax.text(0.5, 0.5, "No physical signal comparison data", ha="center", va="center", fontsize=11)
        ax.set_axis_off()
    else:
        work = comparison_df.copy()
        work["gap"] = (work.get("physical_signal_pct", 0.0) - work.get("documented_progress_pct", 0.0)).abs()
        work = work.sort_values("gap", ascending=False).head(8)

        labels = work.get("block", pd.Series(index=work.index, dtype="object")).astype(str).tolist()
        physical = (pd.to_numeric(work.get("physical_signal_pct"), errors="coerce").fillna(0.0) * 100.0).tolist()
        documentary = (
            pd.to_numeric(work.get("documented_progress_pct"), errors="coerce").fillna(0.0) * 100.0
        ).tolist()

        x = list(range(len(labels)))
        width = 0.38
        ax.bar([v - width / 2 for v in x], documentary, width=width, color="#0b2d4e", label="Documented")
        ax.bar([v + width / 2 for v in x], physical, width=width, color="#008577", label="Physical signal")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
        ax.set_ylim(0, 105)
        ax.set_ylabel("Progress %")
        ax.grid(axis="y", alpha=0.24)
        ax.legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    image = BytesIO()
    fig.savefig(image, format="png", bbox_inches="tight")
    plt.close(fig)
    image.seek(0)
    return image


def _add_brand(slide, *, logo_path: Optional[Path], symbols: dict[str, Any], theme: _Theme) -> None:
    Inches = symbols["Inches"]
    Pt = symbols["Pt"]
    RGBColor = symbols["RGBColor"]

    bar = slide.shapes.add_shape(symbols["MSO_SHAPE"].RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.32))
    bar.fill.solid()
    bar.fill.fore_color.rgb = _rgb(RGBColor, theme.navy)
    bar.line.fill.background()

    if logo_path and logo_path.exists():
        slide.shapes.add_picture(str(logo_path), Inches(11.55), Inches(0.02), height=Inches(0.26))

    label = slide.shapes.add_textbox(Inches(0.35), Inches(0.04), Inches(6.5), Inches(0.24))
    tf = label.text_frame
    tf.text = "INPROS | QA Platform"
    tf.paragraphs[0].font.size = Pt(10)
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].font.color.rgb = _rgb(RGBColor, theme.white)


def _add_title(slide, title: str, subtitle: str, *, symbols: dict[str, Any], theme: _Theme) -> None:
    Inches = symbols["Inches"]
    Pt = symbols["Pt"]
    RGBColor = symbols["RGBColor"]

    title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.55), Inches(9.6), Inches(0.7))
    title_frame = title_box.text_frame
    title_frame.text = title
    title_frame.paragraphs[0].font.size = Pt(28)
    title_frame.paragraphs[0].font.bold = True
    title_frame.paragraphs[0].font.color.rgb = _rgb(RGBColor, theme.navy)

    subtitle_box = slide.shapes.add_textbox(Inches(0.62), Inches(1.18), Inches(11.0), Inches(0.4))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.text = subtitle
    subtitle_frame.paragraphs[0].font.size = Pt(12)
    subtitle_frame.paragraphs[0].font.color.rgb = _rgb(RGBColor, theme.slate)


def _add_kpi_card(
    slide,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    label: str,
    value: str,
    symbols: dict[str, Any],
    theme: _Theme,
) -> None:
    Inches = symbols["Inches"]
    Pt = symbols["Pt"]
    RGBColor = symbols["RGBColor"]

    card = slide.shapes.add_shape(symbols["MSO_SHAPE"].ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = _rgb(RGBColor, theme.light_bg)
    card.line.color.rgb = _rgb(RGBColor, (214, 220, 227))

    label_box = slide.shapes.add_textbox(Inches(left + 0.18), Inches(top + 0.10), Inches(width - 0.22), Inches(0.22))
    label_tf = label_box.text_frame
    label_tf.text = label
    label_tf.paragraphs[0].font.size = Pt(10)
    label_tf.paragraphs[0].font.bold = True
    label_tf.paragraphs[0].font.color.rgb = _rgb(RGBColor, theme.slate)

    value_box = slide.shapes.add_textbox(Inches(left + 0.18), Inches(top + 0.36), Inches(width - 0.22), Inches(0.40))
    value_tf = value_box.text_frame
    value_tf.text = value
    value_tf.paragraphs[0].font.size = Pt(22)
    value_tf.paragraphs[0].font.bold = True
    value_tf.paragraphs[0].font.color.rgb = _rgb(RGBColor, theme.navy)


def _add_table(
    slide,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    headers: list[str],
    rows: list[list[str]],
    symbols: dict[str, Any],
    theme: _Theme,
) -> None:
    Inches = symbols["Inches"]
    Pt = symbols["Pt"]
    RGBColor = symbols["RGBColor"]

    table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(left), Inches(top), Inches(width), Inches(height))
    table = table_shape.table

    for idx, header in enumerate(headers):
        cell = table.cell(0, idx)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = _rgb(RGBColor, theme.navy)
        run = cell.text_frame.paragraphs[0].runs[0]
        run.font.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = _rgb(RGBColor, theme.white)

    for ridx, row in enumerate(rows, start=1):
        for cidx, value in enumerate(row):
            cell = table.cell(ridx, cidx)
            cell.text = value
            cell.fill.solid()
            cell.fill.fore_color.rgb = _rgb(RGBColor, theme.white if ridx % 2 else theme.light_bg)
            run = cell.text_frame.paragraphs[0].runs[0]
            run.font.size = Pt(9)
            run.font.color.rgb = _rgb(RGBColor, theme.navy)


def _add_cover_slide(prs, *, report_meta: dict[str, Any], symbols: dict[str, Any], theme: _Theme, logo_path: Optional[Path]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_brand(slide, logo_path=logo_path, symbols=symbols, theme=theme)

    analysis_week = report_meta.get("analysis_week")
    generated_at = report_meta.get("generated_at") or datetime.now(timezone.utc).isoformat()
    subtitle = f"Board Executive Pack | Week {analysis_week if analysis_week is not None else '-'} | Generated {generated_at[:19]}Z"
    _add_title(slide, "QA Platform Executive Pack", subtitle, symbols=symbols, theme=theme)

    body = slide.shapes.add_textbox(symbols["Inches"](0.62), symbols["Inches"](2.0), symbols["Inches"](12.0), symbols["Inches"](1.8))
    tf = body.text_frame
    tf.text = "Executive narrative: performance, weekly execution signal, and material risks."
    tf.paragraphs[0].font.size = symbols["Pt"](15)
    tf.paragraphs[0].font.color.rgb = _rgb(symbols["RGBColor"], theme.slate)


def _add_kpi_slide(
    prs,
    *,
    executive_payload: dict[str, Any],
    symbols: dict[str, Any],
    theme: _Theme,
    logo_path: Optional[Path],
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_brand(slide, logo_path=logo_path, symbols=symbols, theme=theme)
    _add_title(slide, "Executive KPI Overview", "Contract scope performance at a glance", symbols=symbols, theme=theme)

    kpis = executive_payload.get("executive_kpis", {})
    weekly = executive_payload.get("weekly_management", {})

    cards = [
        ("Total Dossiers", _fmt_num(kpis.get("total_dossiers", 0))),
        ("Approved", _fmt_num(kpis.get("approved_dossiers", 0))),
        ("Open Backlog", _fmt_num(weekly.get("backlog_aging_summary", {}).get("total_open_backlog", 0))),
        ("Weight Released (t)", _fmt_num(kpis.get("peso_liberado_ton", 0.0), ndigits=2)),
    ]

    start_left = 0.62
    card_w = 3.06
    for idx, (label, value) in enumerate(cards):
        _add_kpi_card(
            slide,
            left=start_left + idx * 3.18,
            top=1.95,
            width=card_w,
            height=1.05,
            label=label,
            value=value,
            symbols=symbols,
            theme=theme,
        )

    highlights = _safe_list(executive_payload.get("weekly_highlights", []))
    rows = [
        [
            str(item.get("label", "-")).replace("_", " ").title(),
            _fmt_num(item.get("value", 0), ndigits=2 if "weight" in str(item.get("label", "")) else 0),
            _fmt_num(item.get("delta", 0), ndigits=2 if "weight" in str(item.get("label", "")) else 0),
        ]
        for item in highlights[:6]
    ]
    if not rows:
        rows = [["No highlights", "-", "-"]]

    _add_table(
        slide,
        left=0.62,
        top=3.25,
        width=6.26,
        height=2.95,
        headers=["Weekly Highlight", "Value", "Delta vs Prev"],
        rows=rows,
        symbols=symbols,
        theme=theme,
    )

    summary_rows = []
    for row in _safe_list(executive_payload.get("executive_summary_table", []))[:6]:
        summary_rows.append(
            [
                str(row.get("stage_category", "-")),
                str(row.get("building_family", "-")),
                _fmt_num(row.get("open_backlog", 0)),
                _fmt_pct(row.get("approval_pct", 0.0)),
            ]
        )
    if not summary_rows:
        summary_rows = [["-", "-", "-", "-"]]

    _add_table(
        slide,
        left=7.02,
        top=3.25,
        width=5.66,
        height=2.95,
        headers=["Stage", "Family", "Backlog", "Approval"],
        rows=summary_rows,
        symbols=symbols,
        theme=theme,
    )


def _add_weekly_signal_slide(
    prs,
    *,
    executive_payload: dict[str, Any],
    piece_payload: dict[str, Any],
    symbols: dict[str, Any],
    theme: _Theme,
    logo_path: Optional[Path],
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_brand(slide, logo_path=logo_path, symbols=symbols, theme=theme)
    _add_title(slide, "Weekly Management + Physical Execution Signal", "Documentary trend against field signal", symbols=symbols, theme=theme)

    release_chart = _render_release_chart(executive_payload.get("weekly_management", {}))
    signal_chart = _render_signal_alignment_chart(piece_payload)

    slide.shapes.add_picture(release_chart, symbols["Inches"](0.62), symbols["Inches"](1.62), width=symbols["Inches"](6.25))
    slide.shapes.add_picture(signal_chart, symbols["Inches"](6.95), symbols["Inches"](1.62), width=symbols["Inches"](6.1))

    kpis = piece_payload.get("kpis", {}) if isinstance(piece_payload.get("kpis"), dict) else {}
    weekly = executive_payload.get("weekly_management", {})
    delta = weekly.get("delta_kpis", {}) if isinstance(weekly.get("delta_kpis"), dict) else {}

    metric_rows = [
        ["Released this week", _fmt_num(delta.get("released_this_week", 0))],
        ["Released weight this week (t)", _fmt_num(delta.get("released_weight_t_this_week", 0.0), ndigits=2)],
        ["Piece signal coverage", _fmt_pct(float(kpis.get("week_trace_coverage_pct", 0.0) or 0.0) * 100.0, ndigits=1)],
        ["Indexed weight total (kg)", _fmt_num(kpis.get("indexed_weight_total", 0.0), ndigits=0)],
    ]

    _add_table(
        slide,
        left=0.62,
        top=5.65,
        width=5.85,
        height=1.45,
        headers=["Weekly Metric", "Value"],
        rows=metric_rows,
        symbols=symbols,
        theme=theme,
    )


def _add_risk_slide(
    prs,
    *,
    executive_payload: dict[str, Any],
    piece_payload: dict[str, Any],
    symbols: dict[str, Any],
    theme: _Theme,
    logo_path: Optional[Path],
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_brand(slide, logo_path=logo_path, symbols=symbols, theme=theme)
    _add_title(slide, "Risk and Exceptions", "Top-N concentration for board focus", symbols=symbols, theme=theme)

    top_backlog = _safe_list(executive_payload.get("top_backlog_risks", []))[:5]
    backlog_rows = [
        [
            str(item.get("stage_category", "-")),
            str(item.get("building_family", "-")),
            _fmt_num(item.get("open_backlog", 0)),
            _fmt_num(item.get("max_age_weeks", 0)),
        ]
        for item in top_backlog
    ]
    if not backlog_rows:
        backlog_rows = [["-", "-", "-", "-"]]

    approval_gaps = _safe_list(executive_payload.get("risk_exception_summary", {}).get("largest_approval_gaps", []))[:5]
    approval_rows = [
        [
            str(item.get("stage_category", "-")),
            str(item.get("building_family", "-")),
            _fmt_num(item.get("approval_gap", 0)),
            _fmt_pct(item.get("approval_pct", 0.0)),
        ]
        for item in approval_gaps
    ]
    if not approval_rows:
        approval_rows = [["-", "-", "-", "-"]]

    exceptions_df = piece_payload.get("exceptions")
    if not isinstance(exceptions_df, pd.DataFrame):
        exceptions_df = pd.DataFrame(columns=["severity", "exception_type", "block", "details"])
    exception_rows_df = exceptions_df.copy()
    if not exception_rows_df.empty:
        exception_rows_df["_rank"] = exception_rows_df.get("severity", "").apply(_severity_rank)
        exception_rows_df = exception_rows_df.sort_values(["_rank", "exception_type"], ascending=[False, True])
    exception_rows = [
        [
            str(row.get("severity", "-")).upper(),
            str(row.get("exception_type", "-"))[:38],
            str(row.get("block", "-")),
            str(row.get("details", "-"))[:46],
        ]
        for _, row in exception_rows_df.head(6).iterrows()
    ]
    if not exception_rows:
        exception_rows = [["-", "-", "-", "-"]]

    _add_table(
        slide,
        left=0.62,
        top=1.67,
        width=4.15,
        height=2.25,
        headers=["Stage", "Family", "Backlog", "Age w"],
        rows=backlog_rows,
        symbols=symbols,
        theme=theme,
    )

    _add_table(
        slide,
        left=4.92,
        top=1.67,
        width=3.62,
        height=2.25,
        headers=["Stage", "Family", "Gap", "Approval"],
        rows=approval_rows,
        symbols=symbols,
        theme=theme,
    )

    _add_table(
        slide,
        left=8.67,
        top=1.67,
        width=4.52,
        height=2.25,
        headers=["Severity", "Type", "Block", "Details"],
        rows=exception_rows,
        symbols=symbols,
        theme=theme,
    )

    signals = [str(s.get("key", "")).replace("_", " ").title() for s in _safe_list(executive_payload.get("risk_exception_summary", {}).get("signals", []))[:4]]
    notes = "Signals: " + (", ".join(signals) if signals else "No additional board-level signals this cycle")
    notes_box = slide.shapes.add_textbox(symbols["Inches"](0.62), symbols["Inches"](4.15), symbols["Inches"](12.5), symbols["Inches"](1.55))
    tf = notes_box.text_frame
    tf.text = notes
    tf.paragraphs[0].font.size = symbols["Pt"](12)
    tf.paragraphs[0].font.color.rgb = _rgb(symbols["RGBColor"], theme.slate)


def _add_closing_slide(
    prs,
    *,
    executive_payload: dict[str, Any],
    symbols: dict[str, Any],
    theme: _Theme,
    logo_path: Optional[Path],
) -> None:
    insights = _safe_list(executive_payload.get("high_value_insights", []))
    risk_signals = _safe_list(executive_payload.get("risk_exception_summary", {}).get("signals", []))
    if not insights and not risk_signals:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_brand(slide, logo_path=logo_path, symbols=symbols, theme=theme)
    _add_title(slide, "Alignment and Closing Summary", "Action-oriented executive takeaways", symbols=symbols, theme=theme)

    lines: list[str] = []
    for item in insights[:4]:
        key = str(item.get("key", "insight")).replace("_", " ").title()
        value = item.get("value")
        context_bits = []
        for field in ("stage_category", "building_family", "context"):
            raw = item.get(field)
            if raw not in (None, ""):
                context_bits.append(str(raw))
        suffix = f" ({', '.join(context_bits)})" if context_bits else ""
        lines.append(f"- {key}: {value}{suffix}")

    for item in risk_signals[:3]:
        key = str(item.get("key", "signal")).replace("_", " ").title()
        value = item.get("value", "-")
        context = item.get("context", "")
        context_txt = f" {context}" if context else ""
        lines.append(f"- Risk signal: {key} = {value}{context_txt}")

    if not lines:
        return

    box = slide.shapes.add_textbox(symbols["Inches"](0.72), symbols["Inches"](1.9), symbols["Inches"](12.0), symbols["Inches"](4.8))
    tf = box.text_frame
    tf.text = lines[0]
    tf.paragraphs[0].font.size = symbols["Pt"](15)
    tf.paragraphs[0].font.color.rgb = _rgb(symbols["RGBColor"], theme.navy)

    for line in lines[1:]:
        p = tf.add_paragraph()
        p.text = line
        p.font.size = symbols["Pt"](13)
        p.font.color.rgb = _rgb(symbols["RGBColor"], theme.slate)


def generate_executive_pack_pptx(
    *,
    week: Optional[int] = None,
    comparison_week: Optional[int] = None,
    language: str = "en",
) -> bytes:
    symbols = _load_pptx_symbols()
    theme = _Theme()

    executive_payload = build_executive_report_payload(
        selected_week=week,
        comparison_week=comparison_week,
        language=language,
    )

    try:
        piece_payload = load_piece_signal_payload(rebuild_if_missing=False)
    except Exception:
        piece_payload = {
            "kpis": {},
            "comparison": pd.DataFrame(),
            "exceptions": pd.DataFrame(),
        }

    Presentation = symbols["Presentation"]
    prs = Presentation()

    settings = get_settings()
    logo_path = settings.project_root / "assets" / "inpros-logo.png"

    _add_cover_slide(prs, report_meta=executive_payload.get("report_meta", {}), symbols=symbols, theme=theme, logo_path=logo_path)
    _add_kpi_slide(prs, executive_payload=executive_payload, symbols=symbols, theme=theme, logo_path=logo_path)
    _add_weekly_signal_slide(
        prs,
        executive_payload=executive_payload,
        piece_payload=piece_payload,
        symbols=symbols,
        theme=theme,
        logo_path=logo_path,
    )
    _add_risk_slide(
        prs,
        executive_payload=executive_payload,
        piece_payload=piece_payload,
        symbols=symbols,
        theme=theme,
        logo_path=logo_path,
    )
    _add_closing_slide(prs, executive_payload=executive_payload, symbols=symbols, theme=theme, logo_path=logo_path)

    out = BytesIO()
    prs.save(out)
    out.seek(0)
    return out.getvalue()


def executive_pack_filename(analysis_week: Any) -> str:
    week_value = str(analysis_week) if analysis_week not in (None, "") else "NA"
    return f"executive-pack-week-{week_value}.pptx"
