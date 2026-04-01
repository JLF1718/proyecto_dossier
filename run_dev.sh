#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  QA Platform — local development launcher
#  Usage:  bash run_dev.sh   (or: make dev)
# ─────────────────────────────────────────────────────────────
set -euo pipefail

IFS=$'\n\t'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

RUNTIME_DIR="${PROJECT_DIR}/.runtime"
BACKEND_PID_FILE="${RUNTIME_DIR}/backend.pid"
DASHBOARD_PID_FILE="${RUNTIME_DIR}/dashboard.pid"

# ── Python / venv resolution ──────────────────────────────────
# Prefer the project venv if it exists and is functional,
# then fall back to any python3 in PATH.
VENV_PY="${PROJECT_DIR}/.venv/bin/python"
VENV_UVICORN="${PROJECT_DIR}/.venv/bin/uvicorn"

if [[ -f "$VENV_PY" ]] && "$VENV_PY" -c "import sys" >/dev/null 2>&1; then
    PYTHON_BIN="$VENV_PY"
    UVICORN_BIN="$VENV_UVICORN"
    echo "[ENV] Using project venv: $VENV_PY"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    UVICORN_BIN="uvicorn"
    echo "[ENV] Venv not usable — falling back to system python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
    UVICORN_BIN="uvicorn"
    echo "[ENV] Venv not usable — falling back to system python"
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

mkdir -p "$RUNTIME_DIR"

is_pid_running() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

cleanup_stale_pid_file() {
    local pid_file="$1"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid="$(cat "$pid_file" 2>/dev/null || true)"
        if [[ -z "$pid" ]] || ! is_pid_running "$pid"; then
            rm -f "$pid_file"
        fi
    fi
}

stop_pid() {
    local pid="$1"
    local label="$2"

    if ! is_pid_running "$pid"; then
        return 0
    fi

    echo "[CLEANUP] Stopping ${label} (PID ${pid})"
    kill "$pid" 2>/dev/null || true

    for _ in {1..10}; do
        if ! is_pid_running "$pid"; then
            return 0
        fi
        sleep 1
    done

    kill -9 "$pid" 2>/dev/null || true
}

pid_command() {
    local pid="$1"
    ps -p "$pid" -o command= 2>/dev/null || true
}

is_project_owned_pid() {
    local pid="$1"
    local command_line
    command_line="$(pid_command "$pid")"

    [[ -n "$command_line" ]] && [[
        "$command_line" == *"$PROJECT_DIR"* ||
        "$command_line" == *"backend.main:app"* ||
        "$command_line" == *"dashboard/app.py"* ||
        "$command_line" == *"-m dashboard.app"*
    ]]
}

port_listener_pids() {
    local port="$1"

    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | sort -u
        return 0
    fi

    return 1
}

cleanup_project_listener_on_port() {
    local label="$1"
    local port="$2"

    local found=false
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        found=true

        if is_project_owned_pid "$pid"; then
            stop_pid "$pid" "$label"
        fi
    done < <(port_listener_pids "$port" || true)

    if [[ "$found" == true ]]; then
        sleep 1
    fi
}

ensure_port_available() {
    local label="$1"
    local port="$2"

    cleanup_project_listener_on_port "$label" "$port"

    local remaining
    remaining="$(port_listener_pids "$port" || true)"
    if [[ -n "$remaining" ]]; then
        echo "[ERROR] Port ${port} is already in use by a non-project process."
        echo "$remaining" | while IFS= read -r pid; do
            [[ -z "$pid" ]] && continue
            echo "[ERROR] PID ${pid}: $(pid_command "$pid")"
        done
        exit 1
    fi
}

cleanup_stale_pid_file "$BACKEND_PID_FILE"
cleanup_stale_pid_file "$DASHBOARD_PID_FILE"
ensure_port_available "FastAPI" "$FASTAPI_PORT"
ensure_port_available "Dash" "$DASH_PORT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  QA Platform — Development Mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FastAPI  → http://127.0.0.1:${FASTAPI_PORT}/api/docs"
echo "  Dash     → http://127.0.0.1:${DASH_PORT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Quick sanity check: verify dash is importable before committing
if ! "$PYTHON_BIN" -c "import dash" >/dev/null 2>&1; then
    echo ""
    echo "Error: 'dash' not found in the selected Python environment."
    echo "Run:  source .venv/bin/activate && pip install -r requirements.txt"
    echo ""
    exit 1
fi

# Initialise database tables (idempotent)
"$PYTHON_BIN" -c "from database.session import init_db; init_db(); print('[DB] Tables initialised.')"

# Start FastAPI in background
"$UVICORN_BIN" backend.main:app \
    --host 0.0.0.0 \
    --port "$FASTAPI_PORT" \
    --reload \
    --reload-dir backend \
    --reload-dir database \
    --reload-exclude '.runtime/*' \
    --reload-exclude 'output/*' \
    --reload-exclude 'data/processed/backups/*' \
    --log-level info &
FASTAPI_PID=$!
echo "$FASTAPI_PID" > "$BACKEND_PID_FILE"
echo "[API] FastAPI started (PID ${FASTAPI_PID})"

# Give FastAPI a moment to start before Dash tries to connect
sleep 2

# Start Dash in foreground
"$PYTHON_BIN" dashboard/app.py &
DASH_PID=$!
echo "$DASH_PID" > "$DASHBOARD_PID_FILE"
echo "[DASH] Dash started (PID ${DASH_PID})"

# Trap Ctrl+C to stop both services
cleanup() {
    echo
    echo "Stopping services..."
    stop_pid "$DASH_PID" "Dash"
    stop_pid "$FASTAPI_PID" "FastAPI"
    rm -f "$BACKEND_PID_FILE" "$DASHBOARD_PID_FILE"
}

trap 'cleanup; exit 0' INT TERM EXIT

wait
