from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.dossier_service import (
    build_executive_report_payload,
    build_historical_comparison_payload,
    weekly_management_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect management payloads produced from the active BAYSA dataset.")
    parser.add_argument("--week", type=int, default=None, help="Analysis week to evaluate. Defaults to latest week available in the active CSV.")
    parser.add_argument("--comparison-week", type=int, default=None, help="Stored snapshot week to compare against.")
    parser.add_argument("--lang", default="en", choices=["en", "es"], help="Language hint for the executive report payload.")
    parser.add_argument(
        "--payload",
        default="weekly",
        choices=["weekly", "historical", "executive"],
        help="Payload shape to print.",
    )
    args = parser.parse_args()

    if args.payload == "weekly":
        payload = weekly_management_payload("BAYSA", selected_week=args.week)
    elif args.payload == "historical":
        payload = build_historical_comparison_payload(selected_week=args.week, comparison_week=args.comparison_week)
    else:
        payload = build_executive_report_payload(selected_week=args.week, comparison_week=args.comparison_week, language=args.lang)

    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())