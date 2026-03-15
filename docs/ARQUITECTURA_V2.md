# QA Platform — Architecture v2.0
> Construction Quality Management System

## Overview

The repository is organised into a layered, modular architecture.  
The original analytics logic (`core/`, `generators/`) is **preserved**; it is wrapped by the new layers—not replaced.

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser / Client                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP
          ┌────────────▼────────────┐
          │    Nginx Reverse Proxy   │  :80 / :443
          │    (production only)     │
          └────┬───────────────┬────┘
               │               │
     ┌─────────▼─────┐  ┌──────▼───────┐
     │  Dash App      │  │  FastAPI API  │
     │  :8050         │  │  :8000        │
     │  dashboard/    │  │  backend/     │
     └────────┬───────┘  └──────┬───────┘
              │   HTTP /api/*    │
              └──────────────────┘
                       │
          ┌────────────▼────────────┐
          │        modules/          │  QA discipline modules
          │  dossier_control/        │
          │  welding_control/        │
          │  concrete_control/       │
          │  nc_management/          │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │        analytics/        │  pandas processing layer
          │  data_processing.py      │
          │  metrics.py              │  ← wraps core/metricas.py
          │  reports.py              │  ← wraps generators/
          └────────────┬────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │          EXISTING MODULES            │  (preserved, not modified)
    │  core/metricas.py   ◄── source of   │
    │  generators/dashboard_generator.py   │     truth for KPIs
    │  generators/consolidado_generator.py │
    │  generators/utils_generator.py       │
    └──────────────────┬──────────────────┘
                       │
          ┌────────────▼────────────┐
          │        database/         │
          │  models.py   (SQLAlchemy)│
          │  session.py              │
          │  qa_platform.db (SQLite) │
          └─────────────────────────┘
```

---

## Directory Structure

```
proyecto_dossier/
│
├── backend/                    ← FastAPI application
│   ├── main.py                 ← App entry point
│   ├── config.py               ← Settings (pydantic-settings)
│   ├── dependencies.py         ← Auth-ready dependency injection
│   └── routers/
│       ├── dossiers.py         ← GET /api/dossiers
│       ├── metrics.py          ← GET /api/metrics
│       ├── welds.py            ← GET /api/welds
│       └── ncforms.py          ← GET/POST /api/ncforms
│
├── dashboard/                  ← Plotly Dash application
│   ├── app.py                  ← Dash entry point + page routing
│   ├── layouts/
│   │   ├── main_layout.py      ← Shell: sidebar + navbar
│   │   └── dossier_layout.py   ← Dossier Control page
│   ├── callbacks/
│   │   └── dossier_callbacks.py← Interactive filter callbacks
│   └── components/
│       ├── kpi_cards.py        ← Bootstrap KPI card components
│       └── charts.py           ← dcc.Graph wrappers
│
├── modules/                    ← One module per QA discipline
│   ├── dossier_control/
│   │   ├── data_loader.py      ← CSV loading for dossiers
│   │   ├── metrics.py          ← Dossier KPI API
│   │   └── dashboard.py        ← Plotly figure factories
│   ├── welding_control/
│   │   ├── data_loader.py
│   │   ├── metrics.py
│   │   └── dashboard.py
│   ├── concrete_control/
│   │   ├── data_loader.py
│   │   ├── metrics.py
│   │   └── dashboard.py
│   └── nc_management/
│       ├── data_loader.py
│       ├── metrics.py
│       └── dashboard.py
│
├── analytics/                  ← pandas processing + metrics adapter
│   ├── data_processing.py      ← CSV normalisation, pivoting
│   ├── metrics.py              ← Adapter over core/metricas.py
│   └── reports.py              ← Wrapper over generators/
│
├── database/                   ← SQLAlchemy ORM
│   ├── models.py               ← Dossier, WeldJoint, ConcreteTest, NCForm, AuditLog
│   └── session.py              ← Engine + session factory + init_db()
│
├── core/                       ← PRESERVED — canonical metrics
│   └── metricas.py
│
├── generators/                 ← PRESERVED — HTML dashboard generators
│   ├── dashboard_generator.py
│   ├── consolidado_generator.py
│   └── utils_generator.py
│
├── data/                       ← PRESERVED — CSV data files
├── scripts/                    ← PRESERVED — normalisation scripts
├── output/                     ← Generated HTML dashboards
│
├── .env.example                ← Environment variable template
├── run_dev.sh                  ← One-command dev launcher
├── Makefile                    ← Development task runner
├── nginx.conf                  ← Production reverse proxy config
└── requirements.txt            ← All Python dependencies
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/dossiers` | List all dossiers (paginated, filterable) |
| GET | `/api/dossiers/{contractor}` | Dossiers for a single contractor |
| GET | `/api/dossiers/contractors` | Available contractor keys |
| GET | `/api/metrics` | Global KPIs |
| GET | `/api/metrics/by-contractor` | KPIs per contractor |
| GET | `/api/metrics/by-stage` | KPIs per construction stage |
| GET | `/api/metrics/{contractor}` | KPIs for one contractor |
| GET | `/api/welds` | Weld inspection records |
| GET | `/api/welds/metrics` | Welding KPIs |
| GET | `/api/ncforms` | NC reports list |
| GET | `/api/ncforms/metrics` | NC KPIs |
| POST | `/api/ncforms` | Create new NC report |

Interactive docs: **http://localhost:8000/api/docs**

---

## Running Locally

### 1. Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set API_ACCESS_KEY if you want auth
```

### 3. Initialise the database

```bash
make db-init
# or: python -c "from database.session import init_db; init_db()"
```

### 4. Start both services

```bash
make dev
# or: bash run_dev.sh
```

| Service | URL |
|---------|-----|
| Dash Dashboard | http://localhost:8050 |
| FastAPI Swagger UI | http://localhost:8000/api/docs |

### 5. Development tips

```bash
make api    # FastAPI only
make dash   # Dash only
make test   # Run pytest
make lint   # Run ruff linter
```

---

## Adding a New QA Module

1. Create `modules/your_module/` with `data_loader.py`, `metrics.py`, `dashboard.py`
2. Add a router in `backend/routers/your_module.py`
3. Register the router in `backend/main.py`
4. Add a layout in `dashboard/layouts/your_layout.py`
5. Add callbacks in `dashboard/callbacks/your_callbacks.py`
6. Register the new route in `dashboard/app.py` → `render_page()`

---

## Production Deployment (Linux/Nginx)

```bash
# 1. Install Nginx
sudo apt install nginx

# 2. Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/qa_platform
sudo ln -s /etc/nginx/sites-available/qa_platform /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 3. Run with gunicorn (production-grade WSGI)
# FastAPI
gunicorn backend.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 &

# Dash
gunicorn dashboard.app:server -w 2 --bind 0.0.0.0:8050 &
```

---

## Design Principles

- **Single source of truth**: All KPI maths live in `core/metricas.py`. The analytics layer adapts output format; it never shadows the logic.
- **Module isolation**: Each QA discipline (`dossier_control`, `welding_control` …) owns its data loading, metrics, and chart factories.
- **API-first**: The Dash dashboard communicates with FastAPI via HTTP. If the API is down, callbacks fall back to direct module imports.
- **Security by default**: Security headers are applied at the middleware level. API-key auth is opt-in (set `API_ACCESS_KEY`).
- **Zero lock-in**: CSV files remain the primary data store. SQLite is additive (audit log, NC forms). Existing scripts are untouched.
