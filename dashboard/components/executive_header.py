"""Executive decision header components.

Public API
----------
    compute_executive_status(weekly_payload, kpi_payload) -> dict
        Compute RED / YELLOW / GREEN traffic-light status and key metrics.

    compute_priority_score(backlog_count, max_age_weeks) -> int
        Return the backlog priority score using count x age.

    classify_priority(rank) -> str
        Map rank to HIGH | MEDIUM | LOW.

    generate_recommended_actions(status_data, weekly_payload, kpi_payload) -> list[dict]
        Auto-generate directive actions based on live data.

    executive_status_header(status_data, lang) -> html.Div
        Render the EXECUTIVE STATUS hero panel (traffic-light + key KPIs).

    recommended_actions_block(actions, lang) -> html.Div
        Render the RECOMMENDED ACTIONS directive panel.
"""

from __future__ import annotations

from typing import Any, Dict, List

import dash_bootstrap_components as dbc
from dash import html

from dashboard.i18n import t

# ── Colour palettes ──────────────────────────────────────────────────────────

_STATUS_PALETTE: Dict[str, Dict[str, str]] = {
    "RED": {
        "bg": "#fff5f5",
        "border": "#dc2626",
        "badge_bg": "#dc2626",
        "badge_text": "#ffffff",
        "kpi_border": "#fca5a5",
    },
    "YELLOW": {
        "bg": "#fffbeb",
        "border": "#d97706",
        "badge_bg": "#d97706",
        "badge_text": "#ffffff",
        "kpi_border": "#fcd34d",
    },
    "GREEN": {
        "bg": "#f0fdf4",
        "border": "#16a34a",
        "badge_bg": "#16a34a",
        "badge_text": "#ffffff",
        "kpi_border": "#86efac",
    },
}

_PRIORITY_COLORS: Dict[str, str] = {
    "HIGH": "#dc2626",
    "MEDIUM": "#d97706",
    "LOW": "#1f4e79",
}


# -- Core computation functions -----------------------------------------------


def compute_executive_status(
    weekly_payload: Dict[str, Any],
    kpi_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute traffic-light executive status from live payload data.

    Rules
    -----
        RED    : max_age > 15 weeks
        YELLOW : 10 <= max_age <= 15 weeks
        GREEN  : max_age < 10 weeks
    """
    risk = weekly_payload.get("risk_exception_summary", {}) or {}
    signals: Dict[str, Any] = {
        item.get("key"): item.get("value")
        for item in (risk.get("signals", []) or [])
        if item.get("key")
    }

    max_age = int(signals.get("oldest_backlog_age", 0) or 0)
    stagnant_groups = int(signals.get("stagnant_groups", 0) or 0)

    aging_summary = weekly_payload.get("backlog_aging_summary", {}) or {}
    total_backlog = int(aging_summary.get("total_open_backlog", 0) or 0)

    oldest_groups: List[Dict[str, Any]] = risk.get("oldest_backlog_groups", []) or []
    top_risk_area = "-"
    if oldest_groups:
        top = oldest_groups[0] or {}
        stage = str(top.get("stage_category") or top.get("stage") or "")
        family = str(top.get("building_family") or top.get("family") or "")
        top_risk_area = f"{stage} | {family}" if stage and family else stage or family or "-"

    peso_total = float(kpi_payload.get("peso_total_ton", 0) or 0)
    peso_liberado = float(kpi_payload.get("peso_liberado_ton", 0) or 0)
    unreleased_weight_t = round(max(0.0, peso_total - peso_liberado), 1)

    if max_age > 15:
        status = "RED"
    elif max_age >= 10:
        status = "YELLOW"
    else:
        status = "GREEN"

    return {
        "status": status,
        "max_age": max_age,
        "total_backlog": total_backlog,
        "stagnant_groups": stagnant_groups,
        "top_risk_area": top_risk_area,
        "unreleased_weight_t": unreleased_weight_t,
        "oldest_backlog_groups": oldest_groups,
        "largest_backlog_groups": risk.get("largest_backlog_groups", []) or [],
        "stagnant_groups_list": risk.get("stagnant_groups", []) or [],
        "largest_approval_gaps": risk.get("largest_approval_gaps", []) or [],
        "_signals": signals,
    }


def compute_priority_score(backlog_count: int, max_age_weeks: int) -> int:
    """Return score = backlog_count * max_age_weeks.

    # 10 dossiers, 20 weeks -> score = 200
    """
    return int(backlog_count or 0) * int(max_age_weeks or 0)


def classify_priority(score: int) -> str:
    """Classify score into HIGH / MEDIUM / LOW."""
    if score >= 150:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    return "LOW"


def generate_recommended_actions(
    status_data: Dict[str, Any],
    weekly_payload: Dict[str, Any],
    kpi_payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate scored executive actions with defensive payload handling."""
    risk = (
        status_data.get("risk_exception_summary", {})
        or weekly_payload.get("risk_exception_summary", {})
        or {}
    )
    largest = risk.get("largest_backlog_groups", []) or status_data.get("largest_backlog_groups", []) or []
    oldest = risk.get("oldest_backlog_groups", []) or status_data.get("oldest_backlog_groups", []) or []
    stagnant = risk.get("stagnant_groups", []) or status_data.get("stagnant_groups_list", []) or []
    signals = risk.get("signals", []) or []

    global_max_age = int(status_data.get("max_age", 0) or 0)
    if global_max_age <= 0:
        for s in signals:
            if (s or {}).get("key") == "oldest_backlog_age":
                global_max_age = int((s or {}).get("value") or 0)
                break

    physical = kpi_payload or {}
    total = float(physical.get("peso_total_ton", 0) or 0)
    released = float(physical.get("peso_liberado_ton", 0) or 0)
    unreleased = max(total - released, 0.0)

    group_map: Dict[tuple, Dict[str, Any]] = {}

    def _upsert_group(g: Dict[str, Any]) -> None:
        item = g or {}
        stage = str(item.get("stage") or item.get("stage_category") or "UNKNOWN")
        family = str(item.get("family") or item.get("building_family") or "UNKNOWN")
        count = int(item.get("backlog_count") or item.get("open_backlog") or 0)
        age = int(item.get("max_age_weeks") or item.get("max_age") or global_max_age or 0)
        key = (stage, family)

        current = group_map.get(key)
        if not current:
            group_map[key] = {
                "stage": stage,
                "family": family,
                "count": count,
                "age": age,
            }
            return

        current["count"] = max(int(current.get("count", 0) or 0), count)
        current["age"] = max(int(current.get("age", 0) or 0), age)

    for group in largest:
        _upsert_group(group)
    for group in oldest:
        _upsert_group(group)

    scored_groups: List[Dict[str, Any]] = []
    for item in group_map.values():
        count = int(item.get("count", 0) or 0)
        age = int(item.get("age", 0) or 0)
        score = compute_priority_score(count, age)
        scored_groups.append(
            {
                "stage": item.get("stage", "UNKNOWN"),
                "family": item.get("family", "UNKNOWN"),
                "count": count,
                "age": age,
                "score": score,
            }
        )

    scored_groups.sort(key=lambda x: x.get("score", 0), reverse=True)

    actions: List[Dict[str, Any]] = []
    for g in scored_groups:
        score = int(g.get("score", 0) or 0)
        priority = classify_priority(score)
        stage = str(g.get("stage", "UNKNOWN"))
        family = str(g.get("family", "UNKNOWN"))
        count = int(g.get("count", 0) or 0)
        age = int(g.get("age", 0) or 0)
        text = (
            f"[{priority}] Prioritize {stage} {family} backlog "
            f"({count} dossiers, {age} weeks aging)"
        )
        actions.append({"priority": priority, "score": score, "text": text})

    total_stagnant_groups = len(stagnant)
    if total_stagnant_groups > 0:
        effective_age = max(global_max_age, 10)
        stagnation_score = max(50, compute_priority_score(total_stagnant_groups, effective_age))
        group_word = "group" if total_stagnant_groups == 1 else "groups"
        actions.append(
            {
                "priority": classify_priority(stagnation_score),
                "score": stagnation_score,
                "text": (
                    "Assign review capacity to "
                    f"{total_stagnant_groups} stagnant {group_word} (no weekly movement)"
                ),
            }
        )

    if unreleased > 0:
        financial_score = int(unreleased)
        actions.append(
            {
                "priority": classify_priority(financial_score),
                "score": financial_score,
                "text": (
                    f"Accelerate release of {int(unreleased)} t at risk "
                    "(unreleased weight impacting cash flow)"
                ),
            }
        )

    tier_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    actions.sort(
        key=lambda a: (
            -int(a.get("score", 0) or 0),
            tier_order.get(str(a.get("priority", "LOW")), 2),
        )
    )

    return actions


# ── Render functions ──────────────────────────────────────────────────────────


def executive_status_header(
    status_data: Dict[str, Any],
    lang: str = "en",
) -> html.Div:
    """Render the EXECUTIVE STATUS hero panel."""
    status = status_data.get("status", "GREEN")
    palette = _STATUS_PALETTE.get(status, _STATUS_PALETTE["GREEN"])

    max_age = status_data.get("max_age", 0)
    total_backlog = status_data.get("total_backlog", 0)
    stagnant = status_data.get("stagnant_groups", 0)
    top_risk_area = status_data.get("top_risk_area", "—")
    unreleased = status_data.get("unreleased_weight_t", 0.0)

    status_badge = html.Span(
        t(lang, f"exec.status.{status.lower()}"),
        style={
            "backgroundColor": palette["badge_bg"],
            "color": palette["badge_text"],
            "padding": "3px 14px",
            "borderRadius": "4px",
            "fontWeight": "700",
            "fontSize": "0.95rem",
            "letterSpacing": "0.08em",
            "marginLeft": "10px",
            "verticalAlign": "middle",
        },
    )

    kpi_items = [
        (t(lang, "exec.kpi.backlog"), f"{total_backlog:,}"),
        (t(lang, "exec.kpi.max_age"), f"{max_age} {t(lang, 'exec.kpi.weeks')}"),
        (t(lang, "exec.kpi.stagnant"), f"{stagnant}"),
        (t(lang, "exec.kpi.top_risk"), top_risk_area),
    ]

    kpi_cols = [
        dbc.Col(
            html.Div(
                [
                    html.Div(
                        label,
                        style={
                            "fontSize": "10px",
                            "fontWeight": "600",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.07em",
                            "color": "#64748b",
                            "marginBottom": "3px",
                        },
                    ),
                    html.Div(
                        value,
                        style={
                            "fontWeight": "700",
                            "fontSize": "1.05rem",
                            "color": "#10222f",
                        },
                    ),
                ],
                style={
                    "borderLeft": f"3px solid {palette['kpi_border']}",
                    "paddingLeft": "10px",
                },
            ),
            xs=6,
            md=3,
            className="mb-2",
        )
        for label, value in kpi_items
    ]

    unreleased_row = (
        html.Div(
            [
                html.Span(
                    f"{t(lang, 'exec.unreleased_weight')}: ",
                    style={"fontWeight": "600", "color": "#b45309"},
                ),
                html.Span(
                    f"{unreleased:,.1f} t",
                    style={"fontWeight": "700", "color": "#b45309", "marginRight": "10px"},
                ),
                html.Span(
                    f"→  {t(lang, 'exec.unreleased_at_risk')}",
                    style={"color": "#64748b", "fontSize": "0.85rem"},
                ),
            ],
            style={
                "marginTop": "10px",
                "paddingTop": "10px",
                "borderTop": "1px solid #e5e7eb",
            },
        )
        if unreleased > 0
        else html.Div()
    )

    return html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Span(
                                t(lang, "exec.status_label"),
                                style={
                                    "fontWeight": "700",
                                    "fontSize": "0.78rem",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.12em",
                                    "color": "#475569",
                                    "verticalAlign": "middle",
                                },
                            ),
                            status_badge,
                        ],
                        style={"marginBottom": "14px"},
                    ),
                    dbc.Row(kpi_cols, className="gy-1"),
                    unreleased_row,
                ]
            ),
            style={
                "borderLeft": f"6px solid {palette['border']}",
                "backgroundColor": palette["bg"],
            },
            className="qa-panel mb-3",
        )
    )


def recommended_actions_block(
    actions: List[Dict[str, str]],
    lang: str = "en",
) -> html.Div:
    """Render the RECOMMENDED ACTIONS directive panel."""
    if not actions:
        return html.Div(className="d-none")

    priority_label_map = {
        "HIGH": t(lang, "exec.priority.high"),
        "MEDIUM": t(lang, "exec.priority.medium"),
        "LOW": t(lang, "exec.priority.low"),
    }

    rows = []
    for action in actions:
        priority = action.get("priority", "LOW")
        text = action.get("text", "")
        border_color = _PRIORITY_COLORS.get(priority, _PRIORITY_COLORS["LOW"])
        priority_label = priority_label_map.get(priority, priority)

        rows.append(
            html.Div(
                [
                    html.Span(
                        priority_label,
                        style={
                            "display": "inline-block",
                            "minWidth": "72px",
                            "backgroundColor": border_color,
                            "color": "#ffffff",
                            "padding": "2px 8px",
                            "borderRadius": "3px",
                            "fontSize": "10px",
                            "fontWeight": "700",
                            "letterSpacing": "0.06em",
                            "marginRight": "12px",
                            "verticalAlign": "middle",
                        },
                    ),
                    html.Span(
                        f"→  {text}",
                        style={"fontSize": "0.9rem", "color": "#10222f"},
                    ),
                ],
                style={
                    "padding": "10px 14px",
                    "borderLeft": f"4px solid {border_color}",
                    "backgroundColor": "#f8fafc",
                    "marginBottom": "6px",
                    "borderRadius": "0 4px 4px 0",
                },
            )
        )

    return html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        t(lang, "exec.recommended_actions_title"),
                        style={
                            "fontWeight": "700",
                            "fontSize": "0.78rem",
                            "textTransform": "uppercase",
                            "letterSpacing": "0.1em",
                            "color": "#475569",
                            "marginBottom": "12px",
                        },
                    ),
                    html.Div(rows),
                ]
            ),
            className="qa-panel mb-3",
        )
    )
