# Control de Dossieres

Repositorio para captura, edición y reporte de dossieres de BAYSA y JAMAR.

## Inicio rápido

```bash
python cli.py run
python cli.py run-web
```

Comandos principales:

```bash
python cli.py --help
python cli.py validate
python cli.py status
python cli.py generate S186
python cli.py backup
python cli.py run-web
python cli.py prune
```

## Estructura vigente

```text
app/                  App Streamlit
core/                 Lógica de métricas
generators/           Dashboards y exportes
scripts/              Utilidades y normalización
scripts/maintenance/  Validación, estado y backups
data/                 CSVs fuente y normalizados
output/               Dashboards, tablas, exports y caché
docs/                 Documentación canónica
```

## Documentación útil

- `docs/README.md`: visión general y flujo operativo.
- `docs/GUIA_USUARIO.md`: uso diario de la app.
- `docs/PROCEDIMIENTOS.md`: tareas operativas y comandos.
- `docs/ARQUITECTURA.md`: estructura técnica y responsabilidades.
- `docs/HISTORICO.md`: contexto de cambios y refactorizaciones.
- `docs/WEB_APP.md`: app web profesional (Fase 1) y enlace público en vivo.

## Datos y salidas

- CSV activos en `data/contratistas/BAYSA/` y `data/contratistas/JAMAR/`.
- Dashboards HTML en `output/dashboards/`.
- Exportes históricos por semana en `output/exports/`.
- El export válido de bloques liberados vive en `output/exports/bloques_liberados.html` y `output/exports/bloques_liberados.json`.

## Notas operativas

- Los cambios hechos en la tabla de la app se persisten al pulsar `Guardar Cambios`.
- Antes de normalizar o tocar CSVs manualmente, usa `python validar_pre_operacion.py`.
- La documentación estable vive en `docs/`; los reportes Markdown históricos del root fueron retirados para evitar instrucciones contradictorias.
