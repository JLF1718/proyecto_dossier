from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.dossier_service import build_or_update_weekly_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or update a persisted weekly snapshot from the active BAYSA dataset.")
    parser.add_argument("--week", type=int, default=None, help="Analysis week to snapshot. Defaults to the latest week available in the active CSV.")
    parser.add_argument("--force", action="store_true", help="Replace an existing snapshot for the selected week.")
    args = parser.parse_args()

    snapshot = build_or_update_weekly_snapshot(selected_week=args.week, force=args.force)
    print(json.dumps(snapshot, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())