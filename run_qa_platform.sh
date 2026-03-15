#!/usr/bin/env bash
# Usage: bash run_qa_platform.sh

set -euo pipefail
IFS=$'\n\t'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${HOME}/workspace/qa_env"
RUNTIME_DIR="${PROJECT_DIR}/.runtime"

BACKEND_PORT=8000
DASHBOARD_PORT=8050
BACKEND_PID_FILE="${RUNTIME_DIR}/backend.pid"
DASHBOARD_PID_FILE="${RUNTIME_DIR}/dashboard.pid"
BACKEND_LOG_FILE="${RUNTIME_DIR}/backend.log"
DASHBOARD_LOG_FILE="${RUNTIME_DIR}/dashboard.log"

is_pid_running() {
    local pid="$1"
    [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

cleanup_stale_pid_file() {
    local label="$1"
    local pid_file="$2"

    if [[ -f "${pid_file}" ]]; then
        local pid
        pid="$(cat "${pid_file}" 2>/dev/null || true)"
        if [[ -z "${pid}" ]] || ! is_pid_running "${pid}"; then
            rm -f "${pid_file}"
            echo "[INFO] Removed stale ${label} PID file."
        fi
    fi
}

is_port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -ltn "( sport = :${port} )" | tail -n +2 | grep -q .
    elif command -v lsof >/dev/null 2>&1; then
        lsof -iTCP:"${port}" -sTCP:LISTEN -t >/dev/null 2>&1
    else
        echo "[ERROR] Neither 'ss' nor 'lsof' is available to check ports."
        exit 1
    fi
}

cd "${PROJECT_DIR}"
mkdir -p "${RUNTIME_DIR}"

if [[ ! -f "${VENV_PATH}/bin/activate" ]]; then
    echo "[ERROR] Virtual environment not found at ${VENV_PATH}"
    exit 1
fi

source "${VENV_PATH}/bin/activate"

if [[ -n "${VIRTUAL_ENV:-}" ]] && [[ -x "${VIRTUAL_ENV}/bin/python" ]]; then
    DASH_PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    DASH_PYTHON_BIN="$(command -v python3)"
else
    echo "[ERROR] No Python interpreter found for dashboard startup."
    exit 1
fi

cleanup_stale_pid_file "backend" "${BACKEND_PID_FILE}"
cleanup_stale_pid_file "dashboard" "${DASHBOARD_PID_FILE}"

backend_running=false
dashboard_running=false

if [[ -f "${BACKEND_PID_FILE}" ]]; then
    backend_pid="$(cat "${BACKEND_PID_FILE}")"
    if is_pid_running "${backend_pid}"; then
        backend_running=true
        echo "[INFO] Backend already running (PID ${backend_pid})."
    fi
fi

if [[ -f "${DASHBOARD_PID_FILE}" ]]; then
    dashboard_pid="$(cat "${DASHBOARD_PID_FILE}")"
    if is_pid_running "${dashboard_pid}"; then
        dashboard_running=true
        echo "[INFO] Dashboard already running (PID ${dashboard_pid})."
    fi
fi

if [[ "${backend_running}" == false ]] && is_port_in_use "${BACKEND_PORT}"; then
    echo "[ERROR] Port ${BACKEND_PORT} is already in use. Backend was not started."
    exit 1
fi

if [[ "${dashboard_running}" == false ]] && is_port_in_use "${DASHBOARD_PORT}"; then
    echo "[ERROR] Port ${DASHBOARD_PORT} is already in use. Dashboard was not started."
    exit 1
fi

if [[ "${backend_running}" == false ]]; then
    nohup uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port "${BACKEND_PORT}" \
        --log-level info \
        >"${BACKEND_LOG_FILE}" 2>&1 &
    backend_pid=$!
    echo "${backend_pid}" > "${BACKEND_PID_FILE}"
    echo "backend started (PID ${backend_pid})"

    sleep 3

    if ! is_pid_running "${backend_pid}"; then
        echo "[ERROR] Backend failed to start. Check ${BACKEND_LOG_FILE}"
        rm -f "${BACKEND_PID_FILE}"
        exit 1
    fi
fi

if [[ "${dashboard_running}" == false ]]; then
    nohup env \
        QA_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}" \
        DASH_HOST="0.0.0.0" \
        DASH_PORT="${DASHBOARD_PORT}" \
        "${DASH_PYTHON_BIN}" dashboard/app.py \
        >"${DASHBOARD_LOG_FILE}" 2>&1 &
    dashboard_pid=$!
    echo "${dashboard_pid}" > "${DASHBOARD_PID_FILE}"
    echo "dashboard started (PID ${dashboard_pid})"

    if ! is_pid_running "${dashboard_pid}"; then
        echo "[ERROR] Dashboard failed to start. Check ${DASHBOARD_LOG_FILE}"
        rm -f "${DASHBOARD_PID_FILE}"
        exit 1
    fi
fi

echo
echo "Logs:"
echo "- Backend:   ${BACKEND_LOG_FILE}"
echo "- Dashboard: ${DASHBOARD_LOG_FILE}"
echo
echo "To stop services: bash stop_qa_platform.sh"
echo
echo "URLs:"
echo "- http://127.0.0.1:${BACKEND_PORT}"
echo "- http://127.0.0.1:${DASHBOARD_PORT}"
echo "- http://64.23.232.48:${DASHBOARD_PORT}"
