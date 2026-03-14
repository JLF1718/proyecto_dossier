# 📋 PROCEDIMIENTOS - TAREAS ESPECÍFICAS

**Guía de cómo hacer cosas concretas en el proyecto.**

---

## 🎯 TAREA 1: INGRESAR UN NUEVO DOSSIER

### Opción A: Usar la App (RECOMENDADO)

```bash
python cli.py run
```

1. Se abre en navegador
2. Selecciona BAYSA o JAMAR
3. Busca sección "INGRESAR DATOS"
4. Completa:
   - BLOQUE: `BLOQUE-001`
   - ETAPA: `DISEÑO`
   - ESTATUS: `EN_REVISIÓN`
   - PESO: `100` (kg)
   - ENTREGA (BAYSA): `S186`
5. Presiona "Agregar Fila" 🟢
6. ¡LISTO! Se guarda automáticamente

### Opción B: Editar CSV Manualmente

```bash
# Abre Windows Explorer:
C:\Users\Jose Luis\proyecto_dossier\data\contratistas\BAYSA\ctrl_dosieres_BAYSA_normalizado.csv
```

**PERO:** No recomendado. Usa la app en su lugar.

---

## 🎨 TAREA 2: CAMBIAR COLORES O ESTILOS

1. Abre archivo: `config.yaml`
2. Busca sección: `colores:`
3. Modifica códigos hexadecimales:

```yaml
colores:
  LIBERADO: '#0F7C3F'      # Verde
  OBSERVADO: '#D0021B'    # Rojo
  EN_REVISIÓN: '#F5A623'  # Naranja
  PLANEADO: '#808080'     # Gris
```

4. **Guardar y regenerar dashboards:**

```bash
python cli.py generate S186
```

---

## 📊 TAREA 3: GENERAR REPORTE PARA UNA SEMANA

### Opción A: Desde la App

1. `python cli.py run`
2. Ingresa SEMANA: `S186`
3. Presiona "Generar Dashboards" 🟢
4. Espera 30-60 segundos
5. ✅ Listo

**Archivos generados:**
- `output/dashboards/dashboard_BAYSA_...html`
- `output/dashboards/dashboard_JAMAR_...html`
- `output/dashboards/dashboard_consolidado_...html`
- `output/exports/bloques_liberados_S186_...html` (respaldo)

### Opción B: Desde Terminal

```bash
python cli.py generate S186
```

Mismo resultado pero sin interfaz gráfica.

---

## 📂 TAREA 4: VER HISTÓRICO DE SEMANAS

Los reportes viejos están aquí:

```
output/exports/
├── bloques_liberados_S184_20260301_...html
├── bloques_liberados_S185_20260302_...html
├── bloques_liberados_S186_20260303_...html
└── ...
```

**Para abrir un reporte antiguo:**

1. Ve a `output/exports/`
2. Busca el archivo de la semana que quieras
3. Haz doble-click para abrir en navegador
4. ¡Ves los datos de esa semana!

---

## 🔄 TAREA 5: NORMALIZAR DATOS (IMPORTAR CSV NUEVO)

Si tienes un CSV fuente nuevo para BAYSA:

```bash
python scripts/normalizar_baysa.py
```

Convierte el CSV fuente (original desordenado) al formato normalizado que usa el proyecto.

Lo mismo para JAMAR:

```bash
python scripts/normalizar_jamar.py
```

---

## ✅ TAREA 6: VALIDAR QUE TODO FUNCIONA

```bash
python cli.py validate
```

Realiza 5 chequeos:
1. ✅ Dependencias instaladas
2. ✅ Módulos Python cargables
3. ✅ CSVs accesibles
4. ✅ Directorios de salida creados
5. ✅ App Streamlit compila

**Si todo está bien:**
```
5/5 checks pasados ✅
```

**Si hay problema:**
```
❌ Error en [sección]
Recomendación: [solución]
```

---

## 💾 TAREA 7: HACER UN RESPALDO MANUAL

```bash
python cli.py backup
```

Crea carpeta:
```
proyecto_dossier_BACKUP_20260303_143022/
```

Con copia completa del proyecto.

---

## 📈 TAREA 8: VER ESTADO RÁPIDO

```bash
python cli.py status
```

Muestra:
- ✅ Archivos principales encontrados
- 📊 Cantidad de registros (BAYSA, JAMAR)
- 📊 Dashboards generados
- 📊 Exportes (histórico de cortes)

---

## 🔧 TAREA 9: MODIFICAR MÉTRICAS

**REGLA:** Siempre modificar en `core/metricas.py`

Ejemplo: Cambiar cómo se calcula "peso liberado"

1. Abre: `core/metricas.py`
2. Busca: `def calcular_peso_liberado(df):`
3. Modifica la lógica
4. Guarda y regenera dashboards

```bash
python cli.py generate S186
```

---

## 🌐 TAREA 10: AGREGAR UNA NUEVA CONTRATISTA

### PASO 1: Crear Carpeta de Datos
```bash
mkdir data/contratistas/NUEVA_CONTRATISTA
```

### PASO 2: Crear CSV Normalizado
Crear archivo: `data/contratistas/NUEVA_CONTRATISTA/ctrl_dosieres_NUEVA_normalizado.csv`

Con columnas:
```
BLOQUE, ETAPA, ESTATUS, PESO, No. REVISIÓN
```

### PASO 3: Agregar a la App
Editar `app/streamlit_app.py`:

```python
# Busca esta línea:
contratista = st.selectbox("Contratista", ["BAYSA", "JAMAR", "NUEVA_CONTRATISTA"], index=0)

# Y actualiza CSV_PATHS:
CSV_PATHS = {
    "BAYSA": BASE / "data/contratistas/BAYSA/...",
    "JAMAR": BASE / "data/contratistas/JAMAR/...",
    "NUEVA_CONTRATISTA": BASE / "data/contratistas/NUEVA_CONTRATISTA/...",
}
```

### PASO 4: Listo!
```bash
python cli.py run
```

Ya aparecerá la nueva contratista.

---

## 📡 TAREA 11: CAMBIAR HOST/PUERTO DE STREAMLIT

Editar `.streamlit/config.toml`:

```toml
# Cambiar puerto
[server]
port = 8502  # Por defecto es 8501

# Cambiar host
[server]
headless = true
address = "0.0.0.0"
```

---

## 🎯 TAREA 12: EXPORTAR A EXCEL

El proyecto genera HTML. Para convertir a Excel:

1. Abre el HTML en navegador
2. Selecciona la tabla
3. Copia (Ctrl+C)
4. Abre Excel
5. Pega (Ctrl+V)

O usa herramientas como `selenium` + `openpyxl` en un script.

---

## 🔐 TAREA 13: AGREGAR CONTRASEÑA A LA APP

Streamlit tiene autenticación integrada. Pero requiere cuenta en Streamlit Cloud.

Para contraseña local simple:

1. Editar `app/streamlit_app.py`
2. Agregar al inicio:

```python
import streamlit as st

password = st.text_input("Contraseña:", type="password")
if password != "mi_password_secreto":
    st.error("Contraseña incorrecta")
    st.stop()
```

---

## 🐛 TAREA 14: DEBUGGEAR UN PROBLEMA

Use el status:

```bash
python cli.py status
```

Valide:

```bash
python cli.py validate
```

Revise logs:

1. En terminal donde corre Streamlit, busca errores
2. En navegador, abre "Developer Tools" (F12)
3. Ve la pestaña "Console" para errores JavaScript

---

## 📚 TAREA 15: ENTENDER UN ARCHIVO ESPECÍFICO

```python
# Para entender qué hace una función:
from core.metricas import calcular_peso_liberado

# Lee su docstring:
help(calcular_peso_liberado)
```

O revisa [ARQUITECTURA.md](ARQUITECTURA.md) para explicación.

---

¡Listo! Aquí están los procedimientos más comunes. 🚀
