#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  QA Platform — local development launcher
#  Usage:  bash run_dev.sh
# ─────────────────────────────────────────────────────────────
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Error: Python interpreter not found (python3/python)."
    exit 1
fi

# Load .env if it exists
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

FASTAPI_PORT="${FASTAPI_PORT:-8000}"
DASH_PORT="${DASH_PORT:-8050}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  QA Platform — Development Mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FastAPI  → http://127.0.0.1:${FASTAPI_PORT}/api/docs"
echo "  Dash     → http://127.0.0.1:${DASH_PORT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Initialise database tables (idempotent)
"$PYTHON_BIN" -c "from database.session import init_db; init_db(); print('[DB] Tables initialised.')"

# Start FastAPI in background
uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "$FASTAPI_PORT" \
    --reload \
    --reload-exclude '.venv/*' \
    --reload-exclude '.runtime/*' \
    --reload-exclude 'output/*' \
    --reload-exclude 'data/processed/backups/*' \
    --log-level info &
FASTAPI_PID=$!
echo "[API] FastAPI started (PID ${FASTAPI_PID})"

# Give FastAPI a moment to start before Dash tries to connect
sleep 2

# Start Dash in foreground
"$PYTHON_BIN" dashboard/app.py &
DASH_PID=$!
echo "[DASH] Dash started (PID ${DASH_PID})"

# Trap Ctrl+C to stop both services
trap "echo; echo 'Stopping services...'; kill $FASTAPI_PID $DASH_PID 2>/dev/null; exit 0" INT TERM

wait
