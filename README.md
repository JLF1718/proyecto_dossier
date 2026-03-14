# Control de Dossieres

Repositorio para captura, edición y reporte de dossieres de BAYSA y JAMAR.

---

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
