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

## Compartir Dashboard de forma segura (HTTPS + Nginx)

Objetivo: exponer QA Platform para terceros con una URL limpia, sin acceso directo a puertos internos.

Estructura publica recomendada:

- `https://qa.example.com/` -> Dashboard Dash (interno `127.0.0.1:8050`)
- `https://qa.example.com/api/` -> Backend FastAPI (interno `127.0.0.1:8000`)
- `https://qa.example.com/api/docs` -> Documentacion FastAPI

### 1) Configurar Nginx reverse proxy

Plantilla incluida:

- `deploy/nginx/qa_platform.conf`

Instalacion en Ubuntu:

```bash
sudo cp deploy/nginx/qa_platform.conf /etc/nginx/sites-available/qa_platform
sudo ln -sf /etc/nginx/sites-available/qa_platform /etc/nginx/sites-enabled/qa_platform
sudo nginx -t
sudo systemctl reload nginx
```

Nota: cambia `server_name qa.example.com` por tu dominio real.

### 2) HTTPS (Let\'s Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d qa.example.com
```

Verifica:

```bash
curl -I https://qa.example.com/
curl -I https://qa.example.com/api/health
```

### 3) Variables de entorno utiles para entorno publico

Comportamiento local se mantiene por defecto. Para despliegue externo, puedes declarar:

```bash
# URL publica usada por smoke validation (opcional)
export QA_PUBLIC_DASHBOARD_URL="https://qa.example.com/"
export QA_PUBLIC_API_BASE_URL="https://qa.example.com"

# Base path de Dash (opcional; default "/")
# Solo si publicas en subruta, por ejemplo https://qa.example.com/qa/
export DASH_BASE_PATH="/"
```

Uso de smoke con URL publica (si no pasas flags, toma las variables anteriores):

```bash
python3 scripts/smoke_validate_release.py
```

### 4) Opciones de seguridad recomendadas

- Basic Auth en Nginx:
```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd-qa-platform qauser
```
Activa `auth_basic` y `auth_basic_user_file` en `deploy/nginx/qa_platform.conf`.

- IP allowlist en Nginx:
crea un snippet con reglas `allow/deny` y referencialo desde el server block.

- Cloudflare Tunnel (alternativa sin abrir puertos publicos):
publica el dominio via cloudflared hacia `http://127.0.0.1` y mantiene backend/dashboard solo en localhost.

### 5) Notas de systemd

Si usas servicios systemd, revisa:

- `deploy/systemd/qa_backend.service`
- `deploy/systemd/qa_dashboard.service`

Estos servicios mantienen backend y dashboard en puertos internos; Nginx gestiona acceso externo HTTPS.
