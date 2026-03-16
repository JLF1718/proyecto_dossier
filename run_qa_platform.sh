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
HEALTH_TIMEOUT_SECONDS=45

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

http_is_healthy() {
    local url="$1"

    if command -v curl >/dev/null 2>&1; then
        curl --silent --fail --max-time 2 "${url}" >/dev/null
        return $?
    fi

    if command -v wget >/dev/null 2>&1; then
        wget --quiet --tries=1 --timeout=2 --output-document=/dev/null "${url}"
        return $?
    fi

    echo "[ERROR] Neither 'curl' nor 'wget' is available for HTTP health checks."
    return 1
}

wait_for_http_health() {
    local label="$1"
    local url="$2"
    local timeout_seconds="$3"
    local pid="${4:-}"

    echo "[INFO] Waiting for ${label} health at ${url} (timeout: ${timeout_seconds}s)..."

    local elapsed=0
    while (( elapsed < timeout_seconds )); do
        if [[ -n "${pid}" ]] && ! is_pid_running "${pid}"; then
            echo "[ERROR] ${label} process exited before health check succeeded."
            return 1
        fi

        if http_is_healthy "${url}"; then
            echo "[INFO] ${label} is healthy."
            return 0
        fi

        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo "[ERROR] Timed out waiting for ${label} health at ${url}."
    return 1
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

    if ! wait_for_http_health "backend" "http://127.0.0.1:${BACKEND_PORT}" "${HEALTH_TIMEOUT_SECONDS}" "${backend_pid}"; then
        echo "[ERROR] Backend failed health check. Check ${BACKEND_LOG_FILE}"
        rm -f "${BACKEND_PID_FILE}"
        exit 1
    fi
else
    backend_pid="$(cat "${BACKEND_PID_FILE}" 2>/dev/null || true)"
    if ! wait_for_http_health "backend" "http://127.0.0.1:${BACKEND_PORT}" "${HEALTH_TIMEOUT_SECONDS}" "${backend_pid}"; then
        echo "[ERROR] Backend is running but not healthy. Check ${BACKEND_LOG_FILE}"
        exit 1
    fi
fi

if [[ "${dashboard_running}" == false ]]; then
    nohup env \
        QA_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}" \
        DASH_HOST="0.0.0.0" \
        DASH_PORT="${DASHBOARD_PORT}" \
        PYTHONPATH="${PROJECT_DIR}" \
        "${DASH_PYTHON_BIN}" -m dashboard.app \
        >"${DASHBOARD_LOG_FILE}" 2>&1 &
    dashboard_pid=$!
    echo "${dashboard_pid}" > "${DASHBOARD_PID_FILE}"
    echo "dashboard started (PID ${dashboard_pid})"

    if ! wait_for_http_health "dashboard" "http://127.0.0.1:${DASHBOARD_PORT}" "${HEALTH_TIMEOUT_SECONDS}" "${dashboard_pid}"; then
        echo "[ERROR] Dashboard failed health check. Last dashboard log lines:"
        tail -n 40 "${DASHBOARD_LOG_FILE}" || true
        rm -f "${DASHBOARD_PID_FILE}"
        exit 1
    fi
else
    dashboard_pid="$(cat "${DASHBOARD_PID_FILE}" 2>/dev/null || true)"
    if ! wait_for_http_health "dashboard" "http://127.0.0.1:${DASHBOARD_PORT}" "${HEALTH_TIMEOUT_SECONDS}" "${dashboard_pid}"; then
        echo "[ERROR] Dashboard process exists but health check failed. Last dashboard log lines:"
        tail -n 40 "${DASHBOARD_LOG_FILE}" || true
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
