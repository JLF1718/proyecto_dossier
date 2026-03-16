# QA Platform - Construction Quality Management

Plataforma modular para gestion QA/QC en construccion:

- Control de dossieres
- Control de soldadura
- Control de concreto
- Gestion de no conformidades (NC)

La logica analitica historica del proyecto se mantiene en `core/` y `generators/`.
La nueva arquitectura la envuelve en servicios modulares con FastAPI + Dash.

---

## Arquitectura v2 (nueva)

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| API Backend | `backend/` | Endpoints REST (`/api/dossiers`, `/api/welds`, `/api/metrics`, `/api/ncforms`) |
| Dashboard | `dashboard/` | Dash app interactiva con filtros y KPIs |
| Modulos QA | `modules/` | Logica por disciplina (loader, metricas, dashboard) |
| Analytics | `analytics/` | Procesamiento pandas y adaptadores de metricas |
| Base de Datos | `database/` | Modelos SQLAlchemy + SQLite inicial |
| Logica existente | `core/`, `generators/` | Fuente de verdad de metricas y reportes HTML |

Documentacion tecnica completa: `docs/ARQUITECTURA_V2.md`

Despliegue en Ubuntu (produccion): `docs/DEPLOY_UBUNTU.md`

---

## Ejecucion local (FastAPI + Dash)

### 1) Instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configurar variables de entorno

```bash
cp .env.example .env
```

### 3) Inicializar base SQLite

```bash
make db-init
# o
python3 -c "from database.session import init_db; init_db()"
```

### 4) Levantar plataforma completa

```bash
make dev
# o
bash run_dev.sh
```

Servicios:

- FastAPI docs: `http://localhost:8000/api/docs`
- Dash app: `http://localhost:8050`

---

## Endpoints API principales

- `GET /api/dossiers`
- `GET /api/welds`
- `GET /api/metrics`
- `GET /api/ncforms`
- `GET /api/dossiers/snapshots`
- `GET /api/dossiers/weekly-management`
- `GET /api/dossiers/historical-comparison`
- `GET /api/dossiers/executive-report`

Tambien disponibles: rutas por contratista, metricas por etapa/contratista y `POST /api/ncforms`.

---

## Operacion v0.6

La plataforma puede persistir snapshots semanales del dataset activo `data/processed/baysa_dossiers_clean.csv` en SQLite (`database/qa_platform.db`) para comparaciones historicas reales.

Comandos utiles:

```bash
make snapshot
python cli.py snapshot-build --week 194
python cli.py snapshot-build --week 194 --force

make audit-kpis
python cli.py audit-kpis

make inspect-management
python cli.py inspect-management --payload executive --week 194 --comparison-week 193 --lang es
```

Notas:

- No se crean snapshots duplicados para la misma semana salvo con `--force`.
- El dashboard sigue leyendo el dataset activo BAYSA y usa los snapshots persistidos solo para comparacion historica y reporte ejecutivo.

---

## Modo legado (se mantiene)

El flujo anterior sigue disponible para operacion actual y compatibilidad.

### Interfaces originales

## ¿Cómo funciona?

El proyecto tiene **dos interfaces** con propósitos distintos:

| Interfaz | Comando | Para quién | Qué permite |
|---|---|---|---|
| **App Streamlit** | `python cli.py run` | Uso interno (tú) | Editar, agregar y guardar datos en los CSV |
| **Web App profesional** | `python cli.py run-web` | Terceros (clientes, supervisores) | Solo lectura — vista ejecutiva del avance |

La web app sirve en `http://localhost:8000` y muestra siempre el poster HTML más reciente de `output/tablas/`.

---

## Flujo de trabajo diario

```bash
# 1. Editar datos (uso interno)
python cli.py run

# 2. Generar reporte para una semana de corte
python cli.py generate S194

# 3. Ver estado general del sistema
python cli.py status
```

---

## Compartir avance con terceros (enlace público)

1. Levanta la web app:
   ```bash
   python cli.py run-web
   ```

2. En otra terminal, crea el túnel público con Cloudflare:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. Cloudflare devuelve una URL pública temporal (ej. `https://algo-unico.trycloudflare.com`). Compártela.

> **Limitaciones:** la URL cambia cada vez que reinicias el túnel, y deja de funcionar si cierras la app o la terminal.

### Proteger el acceso con clave (opcional)

```powershell
$env:DOSSIER_WEB_ACCESS_KEY="tu_clave_segura"
python cli.py run-web
```

El portal pedirá la clave a cualquier visitante externo.

---

## Comandos principales

```bash
python cli.py run              # App Streamlit (edición interna)
python cli.py run-web          # Web app de solo lectura (puerto 8000)
python cli.py generate S186    # Generar dashboards para semana S186
python cli.py validate         # Validar integridad del proyecto
python cli.py status           # Ver estado rápido
python cli.py backup           # Hacer backup de los CSV activos
python cli.py prune            # Limpiar archivos acumulados
python cli.py --help           # Ver todas las opciones
```

---

## Estructura vigente

```text
app/                  App Streamlit (edición interna)
webapp/               Web app FastAPI (solo lectura para terceros)
core/                 Lógica de métricas compartida
generators/           Generación de dashboards y exportes HTML
scripts/              Utilidades y normalización de CSV
scripts/maintenance/  Validación, estado y backups
data/                 CSVs fuente y normalizados
output/               Dashboards, tablas, exports y caché
docs/                 Documentación canónica
```

---

## Datos y salidas

- CSV activos en `data/contratistas/BAYSA/` y `data/contratistas/JAMAR/`.
- Dashboards HTML en `output/dashboards/`.
- Exportes históricos por semana en `output/historico/`.
- Poster principal BAYSA (el más reciente) en `output/tablas/` — es el que muestra la web app.
- Bloques liberados en `output/exports/bloques_liberados.html` y `.json`.

---

## Notas operativas

- Los cambios en la tabla de Streamlit se persisten al pulsar `Guardar Cambios`.
- Antes de normalizar o tocar CSVs manualmente, ejecuta `python validar_pre_operacion.py`.
- La web app siempre muestra el HTML más reciente de `output/tablas/`; al generar uno nuevo, se actualiza automáticamente en el próximo refresco.
- La documentación completa vive en `docs/`.
