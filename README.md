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

## Como echar a volar el proyecto

### Requisitos previos

- Python 3.10+.
- `pip` y `venv` disponibles en tu equipo.
- Puertos locales libres: `8000` para FastAPI y `8050` para Dash.

### Preparacion inicial

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
make db-init
```

Configuracion base en `.env`:

- `FASTAPI_PORT=8000`
- `DASH_PORT=8050`
- `QA_API_BASE=http://127.0.0.1:8000`

Si no necesitas cambiar puertos ni rutas, puedes dejar `.env` tal como viene del ejemplo.

### Opcion 1: desarrollo local interactivo

Levanta backend y dashboard en la misma terminal:

```bash
make dev
```

Equivale a ejecutar:

```bash
bash run_dev.sh
```

Que hace este modo:

- Inicializa la base SQLite si hace falta.
- Levanta FastAPI en segundo plano.
- Levanta Dash y deja la terminal ocupada.
- Al cerrar con `Ctrl+C`, apaga ambos procesos.

Servicios locales:

- Backend: `http://localhost:8000/api/docs`
- Dashboard: `http://localhost:8050`
- Healthcheck API: `http://localhost:8000/api/health`

### Opcion 2: arranque desacoplado con logs y PID files

Si quieres dejar la plataforma corriendo y liberar la terminal:

```bash
make qa-start
```

Equivale a:

```bash
bash run_qa_platform.sh
```

Este flujo:

- Activa `.venv` automaticamente si existe en el proyecto.
- Arranca backend y dashboard con `nohup`.
- Guarda logs y PID files en `.runtime/`.
- Espera a que ambos servicios respondan antes de dar el arranque por bueno.

Para detenerlo:

```bash
make qa-stop
```

Equivale a:

```bash
bash stop_qa_platform.sh
```

Logs utiles:

- Backend: `.runtime/backend.log`
- Dashboard: `.runtime/dashboard.log`

### Verificacion rapida

Con la plataforma arriba, valida asi:

```bash
curl -f http://127.0.0.1:8000/api/health
curl -I http://127.0.0.1:8050
```

Si todo esta bien, abre:

- Dashboard: `http://127.0.0.1:8050`
- Swagger / OpenAPI: `http://127.0.0.1:8000/api/docs`

## Exponer el dashboard con Cloudflare Quick Tunnel

Quick Tunnel sirve para pruebas y demos, no para produccion.

### 1. Instala `cloudflared`

Verifica primero si ya lo tienes:

```bash
cloudflared --version
```

Si no esta instalado, usa la guia oficial de Cloudflare para Linux:

- Package repository / binarios: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/

### 2. Levanta la plataforma localmente

La forma mas estable para compartirla suele ser:

```bash
make qa-start
```

### 3. Abre el tunel publico

En otra terminal, publica el dashboard Dash en `8050`:

```bash
cloudflared tunnel --url http://localhost:8050
```

`cloudflared` va a imprimir una URL publica parecida a:

- `https://algo-unico.trycloudflare.com`

Comparte esa URL para que otros vean el dashboard.

### 4. Consideraciones importantes

- Deja abierta la terminal donde corre `cloudflared`; si la cierras, el enlace deja de funcionar.
- El backend FastAPI sigue corriendo localmente en `8000`; el dashboard lo consume internamente a traves de `QA_API_BASE`, por eso basta con exponer `8050`.
- Si `cloudflared` falla porque ya existe una configuracion local en `~/.cloudflared/config.yml`, renombrala temporalmente y vuelve a intentar el Quick Tunnel.
- Quick Tunnel tiene limites de uso y no tiene SLA; para algo permanente usa un Cloudflare Tunnel administrado o un proxy formal con dominio propio.

### 5. Cerrar todo

Primero detiene el tunel con `Ctrl+C` en la terminal de `cloudflared`.

Luego apaga la plataforma:

```bash
make qa-stop
```

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
