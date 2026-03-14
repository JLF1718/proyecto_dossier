# Documentación del Proyecto

Esta carpeta concentra la documentación vigente del sistema.

## Orden recomendado

1. `GUIA_USUARIO.md` para el uso diario.
2. `PROCEDIMIENTOS.md` para tareas puntuales.
3. `ARQUITECTURA.md` para entender el código.
4. `HISTORICO.md` para contexto de cambios previos.

## Resumen operativo

- Entrada principal: `python cli.py run`
- App web: `app/streamlit_app.py`
- CLI: `cli.py`
- Métricas compartidas: `core/metricas.py`
- Dashboards y exportes: `generators/`
- Validaciones y backups: `scripts/maintenance/`

## Flujos principales

### Uso diario

```bash
python cli.py run
```

Desde la app puedes:

- consultar los CSV normalizados de BAYSA y JAMAR,
- agregar registros,
- editar filas existentes,
- guardar cambios con `Guardar Cambios`,
- generar dashboards y tablas para una semana de corte.

### Operación por terminal

```bash
python cli.py generate S186
python cli.py validate
python cli.py status
python cli.py backup
```

### Validación previa sobre datos

```bash
python validar_pre_operacion.py
```

Úsalo antes de normalizar o tocar CSVs manualmente; verifica integridad y backups de archivos críticos.

## Datos y resultados

- CSV activos: `data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv` y `data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv`
- Dashboards HTML: `output/dashboards/`
- Exportes históricos por semana: `output/exports/`
- Salidas auxiliares: `output/cache/` y `output/tablas/`

## Criterio documental

- La documentación estable vive en `docs/`.
- El export válido de bloques liberados se genera en `output/exports/`.
- Los reportes Markdown antiguos de despliegue, limpieza o protección fueron absorbidos por estas guías y por el historial.
