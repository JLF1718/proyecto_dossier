# ─────────────────────────────────────────────────────────────
#  Makefile — QA Platform development tasks
# ─────────────────────────────────────────────────────────────
.PHONY: help install dev api dash db-init test lint clean snapshot audit-kpis inspect-management smoke qa-start qa-stop

PYTHON ?= python3
PIP    ?= pip3

help:
	@echo ""
	@echo "  QA Platform — Available commands"
	@echo "  ─────────────────────────────────"
	@echo "  make install   Install all Python dependencies"
	@echo "  make dev       Start FastAPI + Dash in development mode"
	@echo "  make api       Start FastAPI only (port 8000)"
	@echo "  make dash      Start Dash only (port 8050)"
	@echo "  make db-init   Initialise SQLite database tables"
	@echo "  make snapshot  Build/update a persisted weekly snapshot"
	@echo "  make audit-kpis  Print current KPI/weight audit payload"
	@echo "  make inspect-management  Print weekly management payload"
	@echo "  make smoke     Run compact release smoke validation"
	@echo "  make qa-start  Start backend + dashboard with health checks"
	@echo "  make qa-stop   Stop backend + dashboard processes"
	@echo "  make test      Run pytest suite"
	@echo "  make lint      Run ruff linter"
	@echo "  make clean     Remove __pycache__ and .pyc files"
	@echo ""

install:
	$(PIP) install -r requirements.txt

dev:
	bash run_dev.sh

api:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dash:
	$(PYTHON) dashboard/app.py

db-init:
	$(PYTHON) -c "from database.session import init_db; init_db(); print('DB initialised.')"

snapshot:
	$(PYTHON) -m scripts.build_weekly_snapshot

audit-kpis:
	$(PYTHON) -m scripts.audit_kpis

inspect-management:
	$(PYTHON) -m scripts.inspect_management_payload --payload weekly

smoke:
	$(PYTHON) -m scripts.smoke_validate_release

qa-start:
	bash run_qa_platform.sh

qa-stop:
	bash stop_qa_platform.sh

test:
	pytest tests/ -v --tb=short

lint:
	ruff check . --fix

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "Clean complete."
