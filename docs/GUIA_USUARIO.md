# Guía de Usuario

Guía corta para operar la app sin entrar al detalle técnico.

## Abrir la app

```bash
python cli.py run
```

También puedes lanzarla directamente con:

```bash
streamlit run app/streamlit_app.py
```

## Flujo normal de trabajo

1. Selecciona el contratista: `BAYSA` o `JAMAR`.
2. Revisa el resumen ejecutivo y la tabla actual.
3. Agrega un registro nuevo o edita filas existentes.
4. Si editaste la tabla, pulsa `Guardar Cambios`.
5. Ingresa la semana de corte, por ejemplo `S186`.
6. Genera dashboards o tablas.

## Agregar un registro

Completa estos campos:

- `BLOQUE`
- `ETAPA`
- `ESTATUS`
- `PESO (kg)`
- `ENTREGA`, solo para BAYSA
- `No. REVISIÓN`, opcional

Después pulsa `Agregar Registro`.

## Editar registros existentes

1. Busca la sección `Editar / Actualizar Registros`.
2. Filtra si hace falta por bloque, etapa, estatus o entrega.
3. Modifica las celdas necesarias.
4. Pulsa `Guardar Cambios`.

Al guardar, la app crea un backup automático antes de escribir el CSV normalizado.

## Generar reportes

Antes de generar, escribe una semana válida en formato `S###` o `S####`.

Resultados:

- dashboards HTML en `output/dashboards/`
- exportes históricos en `output/exports/`

## Comandos útiles

```bash
python cli.py status
python cli.py validate
python cli.py generate S186
python cli.py backup
python validar_pre_operacion.py
```

## Buenas prácticas

- No edites los CSV manualmente si puedes hacerlo desde la app.
- No borres `output/exports/`; ahí queda el histórico semanal.
- Ejecuta `python validar_pre_operacion.py` antes de normalizar o hacer cambios delicados.

## Si algo falla

1. Ejecuta `python cli.py validate`.
2. Revisa `python cli.py status`.
3. Si vas a tocar datos, valida primero con `python validar_pre_operacion.py`.
4. Si necesitas más detalle técnico, consulta `PROCEDIMIENTOS.md` y `ARQUITECTURA.md`.
