# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Construction QA management platform (v2.0.0) for tracking dossiers, KPIs, welding/concrete quality, and non-conformances. Built with FastAPI (port 8000) + Dash (port 8050) + SQLite.

## Commands

### Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make db-init
cp .env.example .env
```

### Development
```bash
make dev        # Start FastAPI + Dash concurrently
make api        # FastAPI only (port 8000)
make dash       # Dash only (port 8050)
```

### Testing & Linting
```bash
make test       # Run pytest suite
make lint       # Run ruff linter with --fix
make smoke      # Compact release smoke tests
```

Run a single test file:
```bash
pytest tests/test_dossier_service.py -v
```

### Data Management (use these instead of editing CSV directly)
```bash
make edit       # Interactive TUI editor for CSV
make validate   # Validate CSV against data/schema.json
make apply      # Apply patch from data/patches/patch.csv (auto-backups)
```

### Operational
```bash
make snapshot           # Build and persist weekly KPI snapshot to SQLite
make audit-kpis         # Print current KPI audit payload
make inspect-management # Print weekly management payload
```

## Architecture

### Data Flow
`data/processed/baysa_dossiers_clean.csv` is the single source of truth. It is never edited directly—changes flow through the `make edit` → `make validate` → `make apply` path with auto-backup to `data/processed/backups/`.

### Request Flow
```
Browser → Dash (port 8050) → FastAPI (port 8000) → dossier_service.py → CSV (in-memory cache) / SQLite
```

Dash components call FastAPI REST endpoints via `requests` library; the dashboard does not access the database or CSV directly.

### Key Modules

- **[backend/services/dossier_service.py](backend/services/dossier_service.py)** — Core logic: CSV loading/caching, status normalization, KPI computation, and all payload builders (`build_executive_report_payload`, `build_weekly_management_payload`, `build_historical_comparison_payload`).
- **[backend/routers/](backend/routers/)** — FastAPI route handlers (dossiers, metrics, welds, concrete, ncforms).
- **[dashboard/components/](dashboard/components/)** — Dash UI: `cards.py` (tables/summaries), `figures.py` (Plotly charts), `executive_header.py` (status bar).
- **[database/models.py](database/models.py)** — SQLAlchemy ORM: `Dossier`, `WeldJoint`, `ConcreteTest`, `NCForm`, `AuditLog`, `WeeklySnapshot`.
- **[tools/csv_guard.py](tools/csv_guard.py)** — CSV schema validation and safe patch application.

### KPI Scope Rules

Blocks where `N° == "--"` have `in_contract_scope = False` and are **excluded from all KPI counts**. They remain in the dataset for traceability only.

Status normalization in `dossier_service._normalise_status()` maps raw contractor statuses to canonical values:
- `approved` / `liberado` / `aprobado` → `APPROVED`
- `pending` / `observado` → `PENDING`
- `in_review` / `revisión inpros` → `IN_REVIEW` (internal review, not a rejection)
- `fuera de alcance` → `OUT_OF_SCOPE` (excluded from KPIs)

### Weekly Snapshots

Snapshots are persisted to SQLite `weekly_snapshots` table on demand (`make snapshot`). The `build_weekly_management_payload()` and `build_historical_comparison_payload()` functions read from these snapshots to compute deltas and trends.

### Legacy Code

`app/` (Streamlit), `analytics/`, `core/`, `generators/`, `modules/`, `webapp/` are legacy modules. The active system is `backend/` + `dashboard/`.

### Runtime Artifacts

`.runtime/` holds ephemeral PID files and logs for `make qa-start` / `make qa-stop`. Do not commit files from this directory.
