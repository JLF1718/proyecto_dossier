from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.piece_signal_service import build_piece_signal_outputs


def main() -> int:
    outputs = build_piece_signal_outputs(write_outputs=True)
    summary = {
        "status": "ok",
        "piece_rows": int(len(outputs["piece_clean"])),
        "blocks": int(len(outputs["block_summary"])),
        "weeks": int(len(outputs["week_summary"])),
        "exceptions": int(len(outputs["exceptions"])),
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
