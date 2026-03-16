#!/usr/bin/env bash
# Usage: bash stop_qa_platform.sh

set -euo pipefail
IFS=$'\n\t'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${PROJECT_DIR}/.runtime"
BACKEND_PID_FILE="${RUNTIME_DIR}/backend.pid"
DASHBOARD_PID_FILE="${RUNTIME_DIR}/dashboard.pid"

is_pid_running() {
    local pid="$1"
    [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

stop_from_pid_file() {
    local label="$1"
    local pid_file="$2"

    if [[ ! -f "${pid_file}" ]]; then
        echo "[INFO] ${label}: PID file not found."
        return
    fi

    local pid
    pid="$(cat "${pid_file}" 2>/dev/null || true)"

    if [[ -z "${pid}" ]]; then
        rm -f "${pid_file}"
        echo "[INFO] ${label}: Empty PID file removed."
        return
    fi

    if ! is_pid_running "${pid}"; then
        rm -f "${pid_file}"
        echo "[INFO] ${label}: Process not running, stale PID file removed."
        return
    fi

    echo "[INFO] Stopping ${label} (PID ${pid})..."
    kill "${pid}" 2>/dev/null || true

    for _ in {1..10}; do
        if ! is_pid_running "${pid}"; then
            break
        fi
        sleep 1
    done

    if is_pid_running "${pid}"; then
        echo "[WARN] ${label} did not stop gracefully, sending SIGKILL."
        kill -9 "${pid}" 2>/dev/null || true
    fi

    rm -f "${pid_file}"
    echo "[OK] ${label} stopped."
}

cd "${PROJECT_DIR}"
mkdir -p "${RUNTIME_DIR}"

stop_from_pid_file "dashboard" "${DASHBOARD_PID_FILE}"
stop_from_pid_file "backend" "${BACKEND_PID_FILE}"

echo "[OK] QA platform stop sequence completed."
