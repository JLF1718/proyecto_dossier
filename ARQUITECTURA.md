# Arquitectura del Sistema de Dashboards

## 📋 Descripción General

Este sistema genera dashboards interactivos para control de dossieres de múltiples contratistas (JAMAR y BAYSA). La arquitectura está diseñada con un **módulo padre común** para evitar inconsistencias en los cálculos de métricas.

## 🏗️ Estructura de Archivos

### Archivos Principales (Padre → Hijos)

```
proyecto_dossier/
├── metricas_core.py              ← 🎯 MÓDULO PADRE (Única Fuente de Verdad)
├── utils_archivos.py             ← Utilidades comunes de archivos
├── dashboard.py                  ← Dashboard individual (hijo)
├── dashboard_consolidado.py      ← Dashboard consolidado (hijo)
└── generar_todos_dashboards.py   ← Orquestador
```

## 🎯 Módulo Padre: `metricas_core.py`

**IMPORTANTE:** Este es el ÚNICO archivo donde se deben modificar las reglas de cálculo de métricas.

### Funciones Principales:

1. **`calcular_peso_liberado(df)`**
   - Calcula el peso liberado usando `PESO` completo de dossieres con `ESTATUS='LIBERADO'`
   - **NO** usa `PESO_LIBERADO` (que puede ser parcial)

2. **`calcular_metricas_basicas(df)`**
   - Métricas fundamentales: total, liberados, peso total, peso liberado
   - Usada por todos los dashboards

3. **`calcular_metricas_individuales(df)`**
   - Para dashboards de un solo contratista
   - Incluye métricas adicionales: % ejecución real, brechas

4. **`calcular_metricas_consolidadas(df)`**
   - Para dashboard consolidado
   - Combina métricas globales + métricas por contratista

5. **`validar_consistencia_metricas(metricas)`**
   - Valida que las métricas calculadas sean lógicamente correctas

## 🔄 Flujo de Trabajo

### Opción 1: Generar Todo (Recomendado)
```bash
python generar_todos_dashboards.py
```
- Genera dashboards individuales (JAMAR y BAYSA)
- Genera dashboard consolidado
- Usa `metricas_core.py` para todos los cálculos

### Opción 2: Dashboard Individual
```bash
python dashboard.py
```
- Genera dashboard para un solo contratista
- Usa `metricas_core.calcular_metricas_individuales()`

### Opción 3: Dashboard Consolidado
```bash
# Con variable de entorno
$env:SEMANA_PROYECTO="S186"
python dashboard_consolidado.py

# O con entrada manual
python dashboard_consolidado.py
```
- Genera dashboard consolidado de todos los contratistas
- Usa `metricas_core.calcular_metricas_consolidadas()`

## ⚠️ REGLAS CRÍTICAS

### 1. Modificaciones a Métricas
❌ **NUNCA** modificar directamente `dashboard.py` o `dashboard_consolidado.py` para cambiar cálculos  
✅ **SIEMPRE** modificar `metricas_core.py`

### 2. Consistencia de Datos
- **Datos en CSV**: Los valores de `PESO` están almacenados en **kilogramos (kg)**
- **Conversión Automática**: `metricas_core.py` convierte automáticamente kg → ton (divide por 1000)
- **Visualización**: Todos los dashboards y tablas muestran pesos en **toneladas (ton)**
- **Peso Liberado** = Suma del `PESO` completo (convertido a ton) de dossieres con `ESTATUS='LIBERADO'`
- **NO** usar `PESO_LIBERADO` del CSV para métricas generales
- `PESO_LIBERADO` solo se usa para cálculos de ejecución real vs planificado

### 3. Estructura de Métricas
Todas las funciones de `metricas_core.py` retornan diccionarios con keys estandarizadas:
```python
{
    'total_dossiers': int,
    'dossiers_liberados': int,
    'pct_liberado': float,
    'peso_total': float,
    'peso_liberado': float,
    'pct_peso_liberado': float
}
```

## 🐛 Debugging

Si encuentras inconsistencias en las métricas:

1. **Verifica el módulo core:**
   ```bash
   python -c "from metricas_core import *; print('✅ Core OK')"
   ```

2. **Usa la función de impresión:**
   ```python
   from metricas_core import imprimir_metricas, calcular_metricas_basicas
   metricas = calcular_metricas_basicas(df)
   imprimir_metricas(metricas, "DEBUG")
   ```

3. **Valida consistencia:**
   ```python
   from metricas_core import validar_consistencia_metricas
   es_valido, mensaje = validar_consistencia_metricas(metricas)
   if not es_valido:
       print(f"⚠️ Error: {mensaje}")
   ```

## 📊 Archivos Generados

```
output/
├── dashboards/
│   ├── dashboard_BAYSA_[timestamp].html
│   ├── dashboard_JAMAR_[timestamp].html
│   └── dashboard_consolidado_[timestamp].html
├── tablas/
│   ├── analisis_completo_baysa_[timestamp].html  ← Integra 3 visualizaciones
│   ├── tabla_baysa_[timestamp].html
│   ├── tabla_jamar_[timestamp].html
│   └── tabla_resumen_ibcs_[timestamp].html
└── historico/
    ├── BAYSA/S###_YYYYMMDD/
    ├── JAMAR/S###_YYYYMMDD/
    └── S###_YYYYMMDD/  ← Consolidado
```

## 🔧 Mantenimiento

### Agregar Nueva Métrica

1. Editar `metricas_core.py`:
```python
def calcular_metricas_basicas(df: pd.DataFrame) -> Dict:
    # ... código existente ...
    
    # Nueva métrica
    metricas['nueva_metrica'] = df['COLUMNA'].sum()
    
    return metricas
```

2. Los dashboards automáticamente usarán la nueva métrica

### Cambiar Regla de Cálculo

1. Editar la función correspondiente en `metricas_core.py`
2. Regenerar todos los dashboards:
```bash
python generar_todos_dashboards.py
```

## ✅ Ventajas de Esta Arquitectura

1. **Única Fuente de Verdad**: Un solo lugar para lógica de métricas
2. **Consistencia Garantizada**: Todos los dashboards usan el mismo código
3. **Fácil Mantenimiento**: Un cambio se propaga a todos los dashboards
4. **Debugging Simplificado**: Funciones de validación y debugging centralizadas
5. **Escalabilidad**: Fácil agregar nuevos contratistas o métricas

## 📝 Historial de Cambios

- **2026-01-12**: Estandarización de unidades de peso
  - Conversión automática kg → ton en todas las métricas
  - CSV almacena pesos en kg, dashboards muestran en ton
  - Actualización de metricas_core.py y dashboard_consolidado.py
- **2026-01-12**: Creación del módulo `metricas_core.py`
  - Unificación de lógica de métricas
  - Corrección de inconsistencia en peso liberado (PESO vs PESO_LIBERADO)
  - Integración en dashboard.py y dashboard_consolidado.py
