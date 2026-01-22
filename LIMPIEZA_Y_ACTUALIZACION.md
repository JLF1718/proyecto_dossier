# 📋 Limpieza y Actualización del Proyecto

## Estado Actual (17/01/2026)

### ✅ Módulos Activos (Verificados)
- **app_ingreso_datos.py**: App Streamlit principal (ingreso, edición, resumen ejecutivo, generación de dashboards)
- **dashboard.py**: Genera dashboard individual por contratista
- **dashboard_consolidado.py**: Genera dashboard consolidado y tablas IBCS
- **generar_todos_dashboards.py**: Orquesta la generación de dashboards JAMAR + BAYSA + consolidado
- **metricas_core.py**: Cálculo centralizado de métricas (fuente única de verdad)
- **utils_archivos.py**: Utilidades de guardado de archivos
- **scripts/normalizar_baysa.py**: Normalización CSV BAYSA
- **scripts/normalizar_jamar.py**: Normalización CSV JAMAR
- **validar_proyecto.py**: Script de validación integral (NUEVO)

### 📊 CSVs de Datos

#### Requeridos (en uso):
- `data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv` (191 registros)
- `data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv` (259 registros)

#### Fuente (opcionales, backup):
- `data/contratistas/BAYSA/ctrl_dosieres.csv` (178 registros)
- `data/ctrl_dosieres_JAMAR.csv` (NO EXISTE, no crítico)

### 🔧 Archivos de Configuración

- **config.yaml**: Configuración global (colores, tipografía, rutas)
- **.streamlit/config.toml**: Tema Streamlit corporativo
- **requirements.txt**: Dependencias (actualizado con Streamlit 1.30.0)

### ✅ Validación Realizada

```
Total: 5/5 checks pasados
✅ Dependencias (pandas, plotly, yaml, openpyxl, streamlit)
✅ Módulos (todos importan sin error)
✅ CSVs (191 BAYSA, 259 JAMAR normalizados)
✅ Directorios (output, tablas, historico, .streamlit)
✅ App Streamlit (sintaxis válida)
```

## Archivos Obsoletos o Innecesarios

Después de auditoría, todos los archivos Python están en uso. No hay duplicados obsoletos.

Los únicos archivos opcionales/de respaldo:
- `data/contratistas/BAYSA/ctrl_dosieres.csv` (fuente sin normalizar)
- `data/ctrl_dosieres_JAMAR.csv` (fuente JAMAR, no existe)

## Mejoras Implementadas

### 1. App Streamlit (app_ingreso_datos.py)
- ✅ Lectura robusta de CSVs con fallback de encoding (UTF-8, latin-1, cp1252)
- ✅ Selector "Origen de datos" (Normalizado vs Fuente)
- ✅ Panel "Editar / Actualizar Registros" con tabla editable
- ✅ Resumen Ejecutivo con métricas actualizadas en tiempo real
- ✅ Generación de dashboards desde la app
- ✅ Tabla de próximas entregas (BAYSA) con totales

### 2. Normalización de Estatus
- ✅ Mapeo automático de estatus canonizado (PLANEADO, OBSERVADO, EN_REVISIÓN, LIBERADO)
- ✅ Consistencia entre app y dashboards

### 3. Tema Corporativo
- ✅ Colores IBCS integrados (verde #0F7C3F)
- ✅ Ocultar menú/encabezado de Streamlit para look ejecutivo
- ✅ Botones destacados

### 4. Validación del Proyecto
- ✅ Script `validar_proyecto.py` para verificar integridad pre-deployment
- ✅ Chequeos: dependencias, módulos, CSVs, directorios, app Streamlit

## Instrucciones de Uso Post-Limpieza

### Iniciar la App
```bash
streamlit run app_ingreso_datos.py
```

### Validar Proyecto (antes de actualizaciones)
```bash
python validar_proyecto.py
```

### Generar Dashboards Manualmente
```bash
python generar_todos_dashboards.py
# O desde la app: selecciona semana y pulsa "📄 Generar Dashboards"
```

### Normalizar Datos Nuevos
```bash
python scripts/normalizar_baysa.py
python scripts/normalizar_jamar.py
```

## Estructura Final del Proyecto

```
proyecto_dossier/
├── app_ingreso_datos.py              ✅ App principal Streamlit
├── dashboard.py                       ✅ Dashboard individual
├── dashboard_consolidado.py           ✅ Dashboard consolidado
├── generar_todos_dashboards.py       ✅ Orquestador
├── metricas_core.py                  ✅ Cálculos centralizados
├── utils_archivos.py                 ✅ Utilidades
├── validar_proyecto.py               ✅ Validación (NUEVO)
├── config.yaml                       ✅ Configuración
├── requirements.txt                  ✅ Dependencias
│
├── .streamlit/
│   └── config.toml                   ✅ Tema Streamlit
│
├── scripts/
│   ├── normalizar_baysa.py          ✅ Normalización BAYSA
│   └── normalizar_jamar.py          ✅ Normalización JAMAR
│
├── data/
│   ├── contratistas/
│   │   ├── BAYSA/
│   │   │   ├── ctrl_dosieres.csv (fuente)
│   │   │   └── ctrl_dosieres_BAYSA_normalizado.csv (191 registros) ✅
│   │   └── JAMAR/
│   │       └── ctrl_dosieres_JAMAR_normalizado.csv (259 registros) ✅
│   └── historico/
│
├── output/
│   ├── dashboards/              ✅ HTML generados
│   ├── tablas/                  ✅ Tablas IBCS HTML
│   └── historico/               ✅ Backup por semana
│
└── README.md                     (En caso de necesario)
```

## Checklist de Verificación

- [x] Todas las dependencias instaladas (validar_proyecto.py ✅)
- [x] Todos los módulos importan sin error
- [x] CSVs normalizados accesibles y legibles
- [x] Directorios de salida creados
- [x] App Streamlit compilable
- [x] Encoding robusto en todas las lecturas CSV
- [x] Estatus canonizado en app y dashboards
- [x] Streamlit theme aplicado
- [x] Script de validación disponible

## Notas

- **JAMAR fuente**: No existe `data/ctrl_dosieres_JAMAR.csv` pero no es crítico (el normalizado existe)
- **Encoding**: Todos los CSVs se leen con fallback automático (UTF-8 → latin-1 → cp1252)
- **Respaldos**: Los cambios desde la app se guardan con backup automático en `_backup/`

---

**Última actualización**: 17/01/2026 | **Estado**: ✅ PRODUCCIÓN LISTA
