# 🏗️ ARQUITECTURA - CÓMO FUNCIONA INTERNAMENTE

**Para:** Desarrolladores y personas técnicas  
**Nivel:** Intermedio

---

## 📊 VISIÓN GENERAL

El proyecto sigue una **arquitectura modular y escalable**:

```
┌─────────────────────────────────────────┐
│  CLI Principal (cli.py)                 │
│  ↓                                      │
├─────────────────────────────────────────┤
│  APP STREAMLIT (app/streamlit_app.py)  │
│  Interfaz para usuario                  │
│  ↓                                      │
├─────────────────────────────────────────┤
│  CORE (core/metricas.py)               │
│  Lógica de cálculos (ÚNICA FUENTE DE    │
│  VERDAD para métricas)                  │
│  ↓                                      │
├─────────────────────────────────────────┤
│  GENERATORS                             │
│  ├── dashboard_generator.py             │
│  ├── consolidado_generator.py           │
│  └── utils_generator.py                 │
│  ↓                                      │
├─────────────────────────────────────────┤
│  OUTPUT                                 │
│  ├── dashboards/ (HTML con Plotly)     │
│  ├── exports/ (Histórico con timestamp)│
│  └── cache/ (Caché para optimización)   │
│  ↓                                      │
├─────────────────────────────────────────┤
│  DATA                                   │
│  ├── contratistas/BAYSA/ (CSV)         │
│  ├── contratistas/JAMAR/ (CSV)         │
│  └── historico/ (Backup automático)     │
└─────────────────────────────────────────┘
```

---

## 🎯 MÓDULO CORE - ÚNICA FUENTE DE VERDAD

### `core/metricas.py`

**REGLA CRÍTICA:** Aquí se hacen TODOS los cálculos de métricas.

Los generadores (`dashboard_generator.py`, `consolidado_generator.py`) **NUNCA** hacen cálculos directamente. Siempre llaman a `core.metricas`.

### Funciones Principales

```python
# Cálculo de peso liberado
def calcular_peso_liberado(df) -> float:
    """
    Suma el PESO completo de dossieres con ESTATUS='LIBERADO'
    (NO usa PESO_LIBERADO que puede ser parcial)
    
    Retorna: kilogramos (la conversión a toneladas es en calcular_metricas_basicas)
    """

# Métricas básicas (fundamentales)
def calcular_metricas_basicas(df) -> dict:
    """
    Retorna:
    {
        'total_dossiers': int,
        'dossiers_liberados': int,
        'pct_liberado': float,
        'peso_total': float (en toneladas),
        'peso_liberado': float (en toneladas),
        'pct_peso_liberado': float
    }
    """

# Métricas por etapa
def calcular_metricas_por_etapa(df) -> dict:
    """Agrupa métricas por etapa de trabajo"""

# Métricas consolidadas (varias contratistas)
def calcular_metricas_consolidadas(df) -> dict:
    """Combina datos de múltiples contratistas"""
```

### IMPORTANTE: Conversión de Pesos

```
CSV guardan en: KILOGRAMOS (kg)
Dashboards muestran: TONELADAS (ton)

Conversión automática:
peso_en_toneladas = peso_en_kg / 1000
```

---

## 🌐 APP STREAMLIT - LA INTERFAZ

### `app/streamlit_app.py`

**Responsabilidad:** Interfaz visual

1. **Mostrar datos** de CSVs
2. **Capturar entrada** del usuario
3. **Validar datos** antes de guardar
4. **Guardar en CSV**
5. **Generar dashboards** (llamando a generadores)

### Flujo de Datos

```
Usuario ingresa datos
       ↓
Streamlit valida (validar_entrada)
       ↓
¿Válido? SÍ → Guardar en CSV
         NO  → Mostrar error
       ↓
Si presiona "Generar"
       ↓
Ejecuta: generators.dashboard_generator.generar_dashboard()
       ↓
Genera HTML y almacena en output/
```

### Manejo de SEMANA

```python
# El usuario ingresa la semana
semana_corte = st.text_input("Semana de corte (formato S###)", value="S186")

# Al generar, se pasa como variable de entorno
env["SEMANA_CORTE"] = semana_corte

# Los generadores la reciben
semana = os.getenv("SEMANA_CORTE", "S186")

# Se usa para nombrar archivos de exportación
output_file = f"bloques_liberados_{semana}_{timestamp}.html"
```

---

## 📊 GENERATORS - CREADORES DE REPORTES

### `generators/dashboard_generator.py`

Genera dashboards individuales (por contratista).

**Flujo:**

```
1. Leer CSV (data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv)
2. Normalizar estatus
3. Llamar a core.metricas.calcular_metricas_basicas()
4. Crear gráficos con Plotly
5. Construir layout con subplots
6. Guardar como HTML
7. Opcionalmente: Exportar a output/exports/ con timestamp
```

### `generators/consolidado_generator.py`

Genera dashboards consolidados (todas las contratistas juntas).

**Diferencia:** Lee múltiples CSVs y llama a `core.metricas.calcular_metricas_consolidadas()`

### `generators/utils_generator.py`

Funciones compartidas:

```python
def leer_csv_robusto(ruta):
    """Lee CSV con fallback automático de encoding"""
    # Intenta: utf-8-sig, utf-8, latin-1, iso-8859-1, cp1252

def obtener_estructura_directorios(output_dir):
    """Retorna paths estandarizados para outputs"""

def crear_timestamp():
    """Genera timestamp para archivos (yyyyMMdd_HHMMSS)"""
```

---

## 💾 ALMACENAMIENTO - DATOS Y OUTPUTS

### CSVs (Datos)

```
data/contratistas/BAYSA/
├── ctrl_dosieres_BAYSA_normalizado.csv  ← ACTIVO (editado por usuario)
└── ctrl_dosieres.csv                    ← Respaldo (original)

data/contratistas/JAMAR/
├── ctrl_dosieres_JAMAR_normalizado.csv  ← ACTIVO
└── ctrl_dosieres.csv                    ← Respaldo
```

**Estructura de Columnas (normalizada):**
```
BLOQUE, ETAPA, ESTATUS, PESO, No. REVISIÓN, ENTREGA (solo BAYSA)
```

### Dashboards (Outputs)

```
output/dashboards/
├── dashboard_BAYSA_20260303_143022_xxxxx.html
├── dashboard_JAMAR_20260303_143022_xxxxx.html
├── dashboard_consolidado_20260303_143022_xxxxx.html
└── ... (histórico de generaciones)

output/exports/
├── bloques_liberados_S185_20260302_123456.json
├── bloques_liberados_S185_20260302_123456.html
├── bloques_liberados_S186_20260303_143022.json  ← Último
├── bloques_liberados_S186_20260303_143022.html  ← Último
└── ... (ARCHIVO CRÍTICO - No eliminar!)
```

**IMPORTANTE:** `output/exports/` es el **histórico de semanas**.  
Cada corte semanal genera un json + html con timestamp.  
**Nunca elimines estos archivos.**

### Caché (Optimización)

```
output/cache/
├── metricas_BAYSA_20260303.pkl
├── metricas_JAMAR_20260303.pkl
└── ... (se regenera automáticamente si expira)
```

Optimiza si los CSVs no cambiaron. Válido por 24 horas.

---

## 🔄 FLUJO COMPLETO - USUARIO INGRESA DATOS

```
1. Usuario abre app: python cli.py run
   ↓
2. Streamlit carga app/streamlit_app.py
   ↓
3. Usuario selecciona contratista (BAYSA/JAMAR)
   ↓
4. App lee CSV con generators.utils_generator.leer_csv_robusto()
   ↓
5. Muestra tabla de datos existentes
   ↓
6. Usuario completa campos: BLOQUE, ETAPA, ESTATUS, PESO, ENTREGA
   ↓
7. Usuario presiona "Agregar Fila"
   ↓
8. Streamlit valida con validar_entrada()
   ↓
9. ¿Válido? SÍ → Crea nueva fila y agrega a DataFrame
   ↓
10. Guarda CSV con DataFrame.to_csv()
   ↓
11. Muestra confirmación ✅
   ↓
12. Usuario ingresa SEMANA: S186
   ↓
13. Usuario presiona "Generar Dashboards"
   ↓
14. Streamlit ejecuta:
    - subprocess.run(["python", "dashboard.py", "--no-cache"])
    - subprocess.run(["python", "dashboard_consolidado.py"])
   ↓
15. Generadores leen CSV
   ↓
16. Llaman a core.metricas.calcular_metricas_basicas()
   ↓
17. Crean gráficos con Plotly
   ↓
18. Guardan HTML en output/dashboards/
   ↓
19. Exportan también a output/exports/bloques_liberados_S186_TIMESTAMP.html
   ↓
20. Mostrar "✅ Dashboards generados correctamente"
   ↓
21. Usuario abre archivos HTML con navegador
```

---

## 🗝️ REGLAS CRÍTICAS

### 1. Modificaciones a Métricas
```
❌ NUNCA modificar dashboard_generator.py para cambiar cálculos
✅ SIEMPRE modificar core/metricas.py
```

### 2. Consistencia de Peso
```
CSV: Kilogramos (kg)
Código: Convierte a toneladas en calcular_metricas_basicas()
Dashboards: Mostrar en toneladas (ton)
```

### 3. Histórico de Semanas
```
CRÍTICO: output/exports/ contiene cada corte semanal con timestamp
NO eliminar, NO mover, NO renombrar estos archivos
```

### 4. CSVs
```
NUNCA editar manualmente los CSVs de datos
SIEMPRE usar la app Streamlit
Excepto: Backup en data/contratistas/*/ctrl_dosieres.csv
```

## 🔌 INTEGRACIONES

### Streamlit
- Framework web para la interfaz
- Auto-refresh al detectar cambios
- Caching integrado

### Plotly
- Gráficos interactivos
- Exportables a HTML
- Auto-responsive

### Pandas
- Manipulación de DataFrames
- Lectura/escritura de CSVs
- Cálculos vectorizados

### PyYAML
- Configuración en config.yaml
- Estilos y colores
- Tipografía

---

## 📈 ESCALABILIDAD

### Para agregar una nueva contratista:

1. Crear carpeta: `data/contratistas/NUEVA/`
2. Agregar CSV: `ctrl_dosieres_NUEVA_normalizado.csv`
3. Actualizar: `app/streamlit_app.py` (selectbox contratista)
4. Crear: `scripts/normalizar_nueva.py` (si existe CSV fuente)
5. Listo! Todo lo demás escala automáticamente

### Para agregar nuevos campos:

1. Actualizar estructura CSV
2. Actualizar: `app/streamlit_app.py` (campos de entrada)
3. Actualizar: `app/streamlit_app.py` (tabla de edición)
4. Opcionalmente: `core/metricas.py` (si necesita cálculos)
5. Opcionalmente: Generadores (si necesita gráficos nuevos)

### Para cambiar gráficos:

1. Editar: `generators/dashboard_generator.py`
2. O: `generators/consolidado_generator.py`
3. Siempre llamar a: `core/metricas.py` para cálculos
4. Usar: `config.yaml` para estilos

---

## 🧪 TESTING

Ver archivos en `tests/`:

```python
# tests/test_metricas.py
def test_calcular_peso_liberado():
    """Verifica cálculo correcto"""

# tests/test_generators.py
def test_dashboard_generator():
    """Verifica generación de HTML"""

# tests/test_integridad.py
def test_proyecto_completo():
    """End-to-end"""
```

---

## 📝 RESUMEN DE ARCHIVOS

| Archivo | Responsabilidad |
|---------|-----------------|
| **cli.py** | Punto de entrada principal |
| **app/streamlit_app.py** | Interfaz web |
| **core/metricas.py** | Cálculos (ÚNICA VERDAD) |
| **generators/dashboard_generator.py** | Dashboards individuales |
| **generators/consolidado_generator.py** | Dashboards consolidados |
| **generators/utils_generator.py** | Funciones compartidas |
| **scripts/cli_generar.py** | Generador desde CLI |
| **scripts/maintenance/** | Validación, backup, estado |
| **config.yaml** | Estilos y configuración |
| **data/** | CSVs (datos) |
| **output/** | Resultados finales |

---

¡Así funciona internamente el proyecto! 🚀
