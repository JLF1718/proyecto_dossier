# QA Platform v0.7 Closeout

Release objetivo: plataforma ejecutiva cerrada para control de dossiers BAYSA.

Fuente activa y unica de verdad:

- `data/processed/baysa_dossiers_clean.csv`

No se cargan contratistas alternos ni loaders legacy para el flujo activo.

## Que incluye v0.7

- Dashboard ejecutivo con flujo de lectura global a particular:
  1. Executive Status
  2. Weekly Movement
  3. Risk / Exceptions
  4. Trend / History
  5. Actionable Detail
  6. Supporting Detail
- Comparacion historica real contra snapshots persistidos.
- Modo ejecutivo de exportacion con orden estable para presentacion y PDF.
- Soporte EN/ES en pantalla y en export mode.
- Branding oficial INPROS.

## Arranque rapido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make db-init
make dev
```

Servicios locales:

- Backend: `http://localhost:8000/api/docs`
- Dashboard: `http://localhost:8050`

## Operacion diaria (closeout)

```bash
make snapshot
make audit-kpis
make inspect-management
make smoke
```

Comandos CLI equivalentes:

```bash
python cli.py snapshot-build --week 194
python cli.py audit-kpis
python cli.py inspect-management --payload executive --week 194 --comparison-week 193 --lang es
python cli.py smoke-validate --api-base http://127.0.0.1:8000 --dash-url http://127.0.0.1:8050
```

## Validacion compacta de release

Ruta minima recomendada antes de cerrar una entrega:

1. `make qa-start`
2. `make smoke`
3. `pytest tests/ -v --tb=short`
4. `make qa-stop`

El smoke cubre:

- Salud backend (opcional por URL)
- Salud dashboard (opcional por URL)
- Payload semanal
- Payload historico
- Payload ejecutivo

## Scripts operativos clave

- `scripts/audit_kpis.py`: auditoria de KPI y politicas de peso.
- `scripts/build_weekly_snapshot.py`: crea/actualiza snapshot semanal persistido.
- `scripts/inspect_management_payload.py`: inspeccion de payloads weekly/historical/executive.
- `scripts/smoke_validate_release.py`: smoke-test compacto para cierre de version.

## Limites intencionales de esta version

- Dataset activo fijo BAYSA processed CSV.
- Reglas KPI, semantica semanal, semantica historica y politica de peso ya validadas; no se redefinen en v0.7.
- Codigos de negocio PRO / SUE / SHARED preservados.

## Artefactos operativos y limpieza

- Base SQLite: `database/qa_platform.db`
- Archivos temporales SQLite: `*.db-shm`, `*.db-wal` (ignorados en git)
- Runtime local: `.runtime/` (logs y pid files)

## Referencias

- Arquitectura actual: `docs/ARQUITECTURA_V2.md`
- Deploy Ubuntu: `docs/DEPLOY_UBUNTU.md`
