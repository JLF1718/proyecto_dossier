# QA Platform v0.7 - Arquitectura de Cierre

## 1. Alcance activo

Esta version cierra el flujo ejecutivo de dossiers sobre una sola fuente activa:

- `data/processed/baysa_dossiers_clean.csv`

Reglas preservadas sin cambios:

- KPI business rules validadas
- Semantica weekly management validada
- Semantica historical snapshot validada
- Politica contractual de pesos validada
- Codigos de negocio PRO / SUE / SHARED
- Soporte EN/ES
- Modo exportacion ejecutiva
- Branding INPROS

## 2. Topologia operativa

```text
Browser
  -> Dash dashboard (dashboard/app.py) on :8050
  -> FastAPI backend (backend/main.py) on :8000
      -> dossier_service (backend/services/dossier_service.py)
          -> data/processed/baysa_dossiers_clean.csv
          -> SQLite snapshots (database/qa_platform.db)
```

## 3. Capas y responsabilidades

- `backend/main.py`
  - App FastAPI, health check, middlewares, routers, startup DB init.
- `backend/routers/dossiers.py`
  - Endpoints de dossieres y payloads de gestion.
- `backend/services/dossier_service.py`
  - Fuente de verdad de normalizacion, KPI, weekly, historical y executive payload.
- `dashboard/pages/overview.py`
  - Orden visual final de secciones ejecutivas.
- `dashboard/components/cards.py`
  - KPIs, capa de riesgo/excepcion, tablas ejecutivas, pack de reporte.
- `dashboard/i18n.py`
  - Etiquetas EN/ES para UI, export y reporte.

## 4. Flujo final del dashboard (global -> particular)

1. Executive Status
2. Weekly Movement
3. Risk / Exceptions
4. Trend / History
5. Actionable Detail
6. Supporting Detail

Notas:

- Modo export mantiene el mismo orden.
- Secciones secundarias se de-enfatizan para bajar carga cognitiva.
- Riesgo/Excepcion prioriza atencion inmediata (antiguedad, estancamiento, backlog y brecha de aprobacion).

## 5. Payloads de gestion

### Weekly management

Endpoint:

- `GET /api/dossiers/weekly-management`

Campos clave:

- `delta_kpis`
- `weekly_comparison`
- `backlog_aging_summary`
- `stagnant_groups_summary`
- `risk_exception_summary` (v0.7)

### Historical comparison

Endpoint:

- `GET /api/dossiers/historical-comparison`

Campos clave:

- `current_vs_previous`
- `current_vs_selected`
- `history_series`
- `snapshot_status`

### Executive report

Endpoint:

- `GET /api/dossiers/executive-report`

Campos clave:

- `weekly_highlights`
- `risk_exception_summary` (v0.7)
- `high_value_insights` (v0.7)
- `executive_summary_table`

## 6. Persistencia historica

Snapshots semanales en SQLite (`database/qa_platform.db`) con:

- semana de analisis
- hash de fuente activa
- KPIs de snapshot
- payload semanal serializado
- resumen ejecutivo serializado

Comando recomendado:

- `python -m scripts.build_weekly_snapshot --week <N>`

## 7. Operacion y hardening

Comandos principales:

- `make qa-start` / `make qa-stop`
- `make snapshot`
- `make audit-kpis`
- `make inspect-management`
- `make smoke`

Artefactos runtime no versionables:

- `.runtime/`
- `*.db-shm`
- `*.db-wal`

## 8. Validacion de release (ruta minima)

1. Levantar plataforma: `make qa-start`
2. Smoke compacto: `make smoke`
3. Tests: `pytest tests/ -v --tb=short`
4. Cierre: `make qa-stop`

El smoke valida:

- Salud backend y dashboard (si se pasan URLs)
- Payload weekly
- Payload historical
- Payload executive

## 9. Fuera de alcance intencional

- Integraciones de nuevos datasets en esta version.
- Reescritura de reglas KPI o semantica historica ya aprobadas.
- Reintroduccion de loaders legacy o contratistas adicionales en el flujo activo.
