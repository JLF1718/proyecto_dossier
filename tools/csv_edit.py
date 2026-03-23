#!/usr/bin/env python3
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.csv_editor.tui import run_tui


if __name__ == "__main__":
    raise SystemExit(run_tui())
