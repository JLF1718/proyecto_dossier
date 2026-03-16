from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.dossier_service import build_weight_kpi_audit_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the current BAYSA KPI and weight audit payload.")
    parser.parse_args()
    print(json.dumps(build_weight_kpi_audit_payload(), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())