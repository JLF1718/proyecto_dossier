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
make snapshot                 # Build and persist weekly KPI snapshot to SQLite
make audit-kpis               # Print current KPI audit payload
make inspect-management       # Print weekly management payload
make qa-start                 # Start backend + dashboard with health checks
make qa-stop                  # Stop backend + dashboard processes
```

### Piece Signal
```bash
python -m scripts.build_piece_signal_outputs   # Build parquet outputs from raw Excel
```

## Architecture

### Data Flow
`data/processed/baysa_dossiers_clean.csv` is the single source of truth for dossier KPIs. It is never edited directly — changes flow through the `make edit` → `make validate` → `make apply` path with auto-backup to `data/processed/backups/`.

Piece-level progress data flows from `data/raw/avance_acumulado_global.xlsm` → `piece_signal_service` → parquet files in `data/processed/`.

### Request Flow
```
Browser → Dash (port 8050) → FastAPI (port 8000) → dossier_service.py → CSV (in-memory cache) / SQLite
```

Dash components call FastAPI REST endpoints via `requests` library; the dashboard does not access the database or CSV directly.

### Key Modules

- **[backend/services/dossier_service.py](backend/services/dossier_service.py)** — Core logic: CSV loading/caching, status normalization, KPI computation, and all payload builders (`build_executive_report_payload`, `build_weekly_management_payload`, `build_historical_comparison_payload`, `build_snapshot_payload`, `build_weight_kpi_audit_payload`).
- **[backend/services/piece_signal_service.py](backend/services/piece_signal_service.py)** — Piece-level progress signal: parses raw Excel, derives block/family/stage, writes parquet outputs (`piece_clean`, `block_summary`, `week_summary`, `exceptions`).
- **[backend/routers/](backend/routers/)** — FastAPI route handlers (dossiers, metrics, welds, concrete, ncforms).
- **[dashboard/app.py](dashboard/app.py)** — Dash entry point; imports from `dossier_service` directly for SSR data.
- **[dashboard/pages/overview.py](dashboard/pages/overview.py)** — Main overview page layout with scope selector (PRO / SUE / all) and filter dropdowns.
- **[dashboard/callbacks/dossier_callbacks.py](dashboard/callbacks/dossier_callbacks.py)** — All interactive Dash callbacks; fetches data from FastAPI `/api/dossiers`.
- **[dashboard/layouts/](dashboard/layouts/)** — `main_layout.py` (shell), `dossier_layout.py` (dossier control page).
- **[dashboard/components/](dashboard/components/)** — Dash UI components:
  - `cards.py` — KPI cards, summary tables, management/comparison cards, risk/insight panels.
  - `figures.py` — Plotly charts (progress, stage/block status, weekly trends, cumulative growth).
  - `kpi_cards.py` — Compact KPI row widget.
  - `executive_header.py` — Top status bar.
  - `export_shell.py` — Export shell component.
- **[dashboard/i18n.py](dashboard/i18n.py)** — Centralized UI label translations (EN/ES).
- **[database/models.py](database/models.py)** — SQLAlchemy ORM: `Dossier`, `WeldJoint`, `ConcreteTest`, `NCForm`, `AuditLog`, `WeeklySnapshot`.
- **[tools/csv_guard.py](tools/csv_guard.py)** — CSV schema validation and safe patch application.
- **[scripts/maintenance/](scripts/maintenance/)** — Operational scripts: `backup_helper.py`, `prune_storage.py`, `validar_integridad.py`, `estado_sistema.py`.

### KPI Scope Rules

Blocks where `N° == "--"` have `in_contract_scope = False` and are **excluded from all KPI counts**. They remain in the dataset for traceability only.

Status normalization in `dossier_service._normalise_status()` maps raw contractor statuses to canonical values:
- `approved` / `liberado` / `aprobado` → `APPROVED`
- `pending` / `observado` → `PENDING`
- `in_review` / `revisión inpros` → `IN_REVIEW` (internal review, not a rejection)
- `fuera de alcance` → `OUT_OF_SCOPE` (excluded from KPIs)

### Contract Groups

`apply_contract_scope_rules()` derives a `contract_group` column:
- `"new_contract"` — SUE Stage 4 blocks not released by the cutoff week (`_NEW_CONTRACT_CUTOFF_WEEK`).
- `"original"` — all other in-scope rows.

The dashboard overview page exposes a scope-selector radio to filter views by contract group.

### Weekly Snapshots

Snapshots are persisted to SQLite `weekly_snapshots` table on demand (`make snapshot`). The `build_weekly_management_payload()` and `build_historical_comparison_payload()` functions read from these snapshots to compute deltas and trends.

### Legacy Code

`app/` (Streamlit), `analytics/`, `core/`, `generators/`, `modules/`, `webapp/` are legacy modules. The active system is `backend/` + `dashboard/`.

### Runtime Artifacts

`.runtime/` holds ephemeral PID files and logs for `make qa-start` / `make qa-stop`. Do not commit files from this directory.

## Known Issues & Fixes

### make dev fails when port 8000 is busy (run_dev.sh)
**Date resolved:** 2026-04-01
**Affected script:** `run_dev.sh`

| Issue | Root cause | Fix |
|---|---|---|
| `make dev` aborted if `8000`/`8050` was used by another project | `run_dev.sh` treated non-project listeners as fatal | Added automatic fallback to next free port (scan forward), while still stopping project-owned stale listeners |
| Dash could point to wrong API when FastAPI port changed | Dash callbacks default to `QA_API_BASE=http://127.0.0.1:8000` | `run_dev.sh` now exports `QA_API_BASE` with the resolved FastAPI port when starting Dash |

**Rule going forward:** For local development launchers, external port conflicts must not be fatal by default. Resolve to a free local port and print the effective URLs.

### Stacked bar label rendering (figures.py)
**Date resolved:** 2026-04-01
**Affected functions:** `status_by_stage_figure`, `status_by_block_figure`

| Issue | Root cause | Fix |
|---|---|---|
| Labels escape above bar when stack near 100% | `textposition="auto"` + `cliponaxis=False` | `textposition="inside"` + `cliponaxis=True` + `uniformtext_mode="hide"` |
| Labels cram into narrow segments | `constraintext="none"` overrides layout hide rule | `constraintext="both"` + 8% data-level guard |
| Text cut mid-character / misaligned | No `insidetextanchor`, clip boundary drift | `insidetextanchor="middle"` + `constraintext="both"` |

**Rule going forward:** Never use `textposition="auto"` or `constraintext="none"` in stacked bar traces. Always pair `uniformtext_mode="hide"` with `constraintext="both"`.

### Dashboard UX & Performance — Batch 2 (commit e124caf)

| Priority | Change | File |
|---|---|---|
| P1 | Empty state guard: "Sin datos para el filtro seleccionado" | figures.py:276, :327 |
| P2 | Color fix: snapshot_approval_trend_figure aligned to _STATUS_COLORS | figures.py:688 |
| P3 | Stage axis: tickangle=-35, automargin=True, bottom margin 26→80 | figures.py:307 |
| P4 | Rich tooltips: Status / Dossiers / % del total | figures.py:293, :343 |
| P5 | _classify_status vectorized with np.select() | figures.py:38 |
| P6 | Callback memoization: 30s TTL, invalidates on CSV mtime change | dossier_callbacks.py |
| Bonus | _historical_frame: isinstance(payload, dict) guard | figures.py |

**Rules going forward:**
- Always test empty dataframe edge case when adding new figure functions
- Status colors must reference _STATUS_COLORS dict — never hardcode hex values
- New callbacks that read CSV must use the memoization pattern from _fetch_dossiers

### Nuevo Alcance — Block classification & status sync (session 2026-04-01)

#### Scope math (single source of truth)
```
  200  total blocks in progress.csv
  - 7  blocks with False in active column (fuera de alcance)
  ───
  193  alcance vigente
  - 16  _NUEVO_ALCANCE_BLOCKS (moved to nuevo contrato)
  ───
  177  contrato principal  ←  what all main KPIs must use
   16  nuevo contrato      ←  separate chart and KPIs
```

#### _NUEVO_ALCANCE_BLOCKS (frozenset — do not derive dynamically)
```
  SUE_70, SUE_72, SUE_73, SUE_74, SUE_75, SUE_78,
  SUE_80, SUE_81, SUE_86, SUE_87, SUE_88, SUE_89,
  SUE_91, SUE_94, SUE_95, SUE_96
```

#### Status of nuevo alcance blocks (authoritative)
```
  LIBERADO (approved):            SUE_78, SUE_91
  ATENCIÓN COMENTARIOS (pending): remaining 14
```

#### Status normalization
Raw Spanish values are mapped via `_STATUS_MAP` before any KPI or chart logic:
```
  LIBERADO             → approved
  ATENCIÓN COMENTARIOS → pending
```
Schema accepts both raw and normalized values.

#### Traceability
Blocks that changed status during reclassification are logged in:
`data/status_change_log.csv`
Columns: `bloque, status_anterior, status_nuevo, motivo, fecha`
Motivo: `"Reclasificación nuevo alcance PVRC24-021"`

#### Bugs fixed this session
| Bug | Root cause | Fix |
|---|---|---|
| KPI showed 183 instead of 177 | Dynamic SUE/W195 heuristic matched only 10 blocks | Replaced with `_NUEVO_ALCANCE_BLOCKS` frozenset |
| New Contract chart showed only SUE etapa 4 | Hardcoded etapa filter | Filter now uses `_NUEVO_ALCANCE_BLOCKS` membership |
| Status mismatch between CSV and contract ref | No sync mechanism existed | Synced via `NUEVO_ALCANCE_REF` + `status_change_log.csv` |

#### Rules going forward
- **NEVER** derive nuevo alcance dynamically from etapa/week heuristics
- **NEVER** hardcode hex colors — always reference `_STATUS_COLORS`
- **NEVER** use `textposition="auto"` or `constraintext="none"` in stacked bars
- Always use `_NUEVO_ALCANCE_BLOCKS` as single source of truth
- Any scope change must update the frozenset **AND** log to `status_change_log.csv`
