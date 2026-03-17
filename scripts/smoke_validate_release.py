from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.dossier_service import (  # noqa: E402
    build_executive_report_payload,
    build_historical_comparison_payload,
    load_dossiers,
    weekly_management_payload,
)


def _http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urlopen(url, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            return (200 <= int(status) < 400, f"HTTP {status}")
    except URLError as exc:
        return (False, str(exc.reason))
    except Exception as exc:  # pragma: no cover - defensive
        return (False, str(exc))


def _assert_has_keys(payload: dict, keys: list[str], label: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise AssertionError(f"{label} missing keys: {missing}")


def run_smoke(api_base: str | None, dash_url: str | None) -> dict:
    summary: dict[str, object] = {
        "checks": {},
        "status": "ok",
    }

    if api_base:
        ok, detail = _http_ok(f"{api_base.rstrip('/')}/api/health")
        summary["checks"]["backend_health"] = {"ok": ok, "detail": detail}
        if not ok:
            summary["status"] = "failed"

    if dash_url:
        ok, detail = _http_ok(dash_url)
        summary["checks"]["dashboard_health"] = {"ok": ok, "detail": detail}
        if not ok:
            summary["status"] = "failed"

    load_dossiers("BAYSA")

    weekly = weekly_management_payload("BAYSA")
    _assert_has_keys(weekly, ["analysis_week", "delta_kpis", "risk_exception_summary"], "weekly payload")
    summary["checks"]["weekly_payload"] = {
        "ok": True,
        "analysis_week": weekly.get("analysis_week"),
        "open_backlog": weekly.get("backlog_aging_summary", {}).get("total_open_backlog", 0),
    }

    historical = build_historical_comparison_payload()
    _assert_has_keys(historical, ["analysis_week", "current_vs_previous", "history_series"], "historical payload")
    summary["checks"]["historical_payload"] = {
        "ok": True,
        "analysis_week": historical.get("analysis_week"),
        "snapshots": historical.get("snapshot_status", {}).get("snapshot_count", 0),
    }

    executive = build_executive_report_payload(language="en")
    _assert_has_keys(
        executive,
        ["report_meta", "weekly_highlights", "risk_exception_summary", "high_value_insights"],
        "executive payload",
    )
    summary["checks"]["executive_payload"] = {
        "ok": True,
        "analysis_week": executive.get("report_meta", {}).get("analysis_week"),
        "insights": len(executive.get("high_value_insights", [])),
    }

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a compact release smoke validation for backend/dashboard health and management payloads."
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("QA_PUBLIC_API_BASE_URL") or None,
        help=(
            "Optional API base URL (for example http://127.0.0.1:8000). "
            "Defaults to QA_PUBLIC_API_BASE_URL when set."
        ),
    )
    parser.add_argument(
        "--dash-url",
        default=os.getenv("QA_PUBLIC_DASHBOARD_URL") or None,
        help=(
            "Optional dashboard URL (for example http://127.0.0.1:8050). "
            "Defaults to QA_PUBLIC_DASHBOARD_URL when set."
        ),
    )
    args = parser.parse_args()

    try:
        result = run_smoke(api_base=args.api_base, dash_url=args.dash_url)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, ensure_ascii=True))
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
