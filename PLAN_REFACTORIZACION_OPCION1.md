# 🎯 PLAN DE REFACTORIZACIÓN - OPCIÓN 1 (EXPLICADO AL NIVEL KINDER)

**Fecha:** 3 de Marzo de 2026  
**Estado:** ⏳ ESPERANDO APROBACIÓN  
**Riesgo:** 🟢 MÍNIMO (Tenemos respaldo completo)

---

## 📖 ¿QUÉ VAMOS A HACER?

Imagina que tu casa está desordenada:
- 📚 Libros en la sala, dormitorio y cocina (todo revuelto)
- 🎮 Juguetes en varios cuartos (no sabes dónde están)
- 👕 Ropa en varios closets (confusión)

**Lo que haremos:** Organizar la casa en **cuartos específicos** para cada cosa:
- 📚 **Biblioteca** → Todos los libros aquí
- 🎮 **Cuarto de juegos** → Todos los juguetes aquí
- 👕 **Armario** → Toda la ropa aquí

Igual con tu proyecto: **Mover los archivos de Python a carpetas lógicas**.

---

## 🗂️ ANTES (AHORA - DESORDENADO)

```
proyecto_dossier/
├── app_ingreso_datos.py              ← App principal
├── dashboard.py                       ← Genera dashboards
├── dashboard_consolidado.py           ← Dashboards juntos
├── metricas_core.py                   ← Cálculo de números
├── generar_todos_dashboards.py        ← Botón para generar
├── utils_archivos.py                  ← Funciones auxiliares
├── validar_proyecto.py                ← Validación
├── estado_proyecto.py                 ← Revisar estado
├── [14 archivos .md aquí abajo]       ← Documentación dispersa
├── scripts/                           ← Más scripts aquí
│   ├── normalizar_baysa.py
│   ├── normalizar_jamar.py
│   └── [otros scripts]
├── data/
├── output/
└── tests/
```

**Problema:** 
- ❌ ¿Cuál es el archivo principal? No está claro
- ❌ Demasiados archivos en root
- ❌ Documentación esparcida (¿cuál leo primero?)
- ❌ Difícil de navegar para nuevas personas

---

## ✅ DESPUÉS (OBJETIVO - ORGANIZADO)

```
proyecto_dossier/
│
├── 📁 app/
│   └── streamlit_app.py              ← LA APP PRINCIPAL (renombrado)
│
├── 📁 core/
│   ├── metricas.py                   ← Cálculos de números
│   └── validadores.py                ← Validaciones
│
├── 📁 generators/
│   ├── dashboard_generator.py         ← Genera dashboards BAYSA
│   ├── consolidado_generator.py       ← Genera dashboards juntos
│   ├── utils_generator.py             ← Funciones compartidas
│   └── generator_base.py              ← Clase padre (sin repetir código)
│
├── 📁 scripts/
│   ├── normalizar_baysa.py            ← Normalizar BAYSA
│   ├── normalizar_jamar.py            ← Normalizar JAMAR
│   ├── cli_generar.py                 ← Generar dashboards desde terminal
│   └── maintenance/
│       ├── validar_integridad.py      ← Validar proyecto
│       ├── limpiar_cache.py           ← Limpiar caché
│       └── backup.py                  ← Hacer respaldos
│
├── 📁 docs/
│   ├── README.md                      ← EMPIEZA AQUÍ (punto de entrada)
│   ├── ARQUITECTURA.md                ← Cómo funciona internamente
│   ├── GUIA_USUARIO.md                ← Cómo usarlo (paso a paso)
│   ├── PROCEDIMIENTOS.md              ← Procesos específicos
│   └── API.md                         ← Referencia técnica
│
├── 📁 data/                           ← IGUAL (no se toca)
│   ├── contratistas/
│   │   ├── BAYSA/
│   │   └── JAMAR/
│   └── historico/
│
├── 📁 output/                         ← IGUAL (no se toca)
│   ├── dashboards/
│   ├── tablas/
│   ├── exports/
│   └── cache/
│
├── 📁 tests/                          ← IGUAL
│   ├── test_metricas.py
│   ├── test_generators.py
│   └── test_integridad.py
│
├── config.yaml                        ← IGUAL
├── requirements.txt                   ← IGUAL
└── .streamlit/config.toml             ← IGUAL
```

**Beneficio:**
- ✅ Estructura clara y profesional
- ✅ Las apps van en `app/`
- ✅ La lógica va en `core/`
- ✅ Los generadores van en `generators/`
- ✅ Los scripts de soporte van en `scripts/`
- ✅ La documentación va en `docs/` (CONSOLIDADA)
- ✅ Fácil para nuevas personas: "Lee README.md en docs/"

---

## 🔄 IMPACTO EN EL USO

### **Antes - Cómo usabas (IGUAL)**
```bash
cd C:\Users\Jose Luis\proyecto_dossier
streamlit run app_ingreso_datos.py    ← Abrir app
```

### **Después - Cómo usarás (MEJORADO)**
```bash
cd C:\Users\Jose Luis\proyecto_dossier
streamlit run app/streamlit_app.py    ← Abrir app (mejor organizado)

# Alternativa: CLI simple
python cli.py run                      ← Abrir app (más fácil)
python cli.py generate                ← Generar dashboards (más fácil)
python cli.py validate                ← Validar proyecto (más fácil)
```

**Importante:** Los datos (`data/`) y resultados (`output/`) **NO CAMBIAN**.

---

## 📝 CAMBIOS TÉCNICOS INTERNOS

### **1. Updates de Imports**

**Antes:**
```python
from metricas_core import calcular_metricas_basicas
from utils_archivos import leer_csv_robusto
```

**Después:**
```python
from core.metricas import calcular_metricas_basicas
from generators.utils_generator import leer_csv_robusto
```

Solo cambio de rutas, **la funcionalidad es IDÉNTICA**.

### **2. Nombres de Archivos**

```
app_ingreso_datos.py    →  app/streamlit_app.py
dashboard.py            →  generators/dashboard_generator.py
dashboard_consolidado.py →  generators/consolidado_generator.py
metricas_core.py        →  core/metricas.py
utils_archivos.py       →  generators/utils_generator.py + core/validadores.py
validar_proyecto.py     →  scripts/maintenance/validar_integridad.py
generar_todos_dashboards.py → scripts/cli_generar.py
```

### **3. Documentación Consolidada**

**Antes:** 14 archivos .md dispersos
```
README.md
QUICK_START.md
GUIA_RAPIDA.md
ARQUITECTURA.md
HISTORIAL_CAMBIOS.md
[y 9 más...]
```

**Después:** 5 archivos en `docs/`
```
docs/
├── README.md          ← Inicio (consolida QUICK_START)
├── ARQUITECTURA.md    ← Explica estructura
├── GUIA_USUARIO.md    ← Paso a paso (consolida GUIA_RAPIDA)
├── PROCEDIMIENTOS.md  ← Tareas específicas
└── API.md             ← Referencia técnica
```

---

## 🛡️ SEGURIDAD: BACK UP Y ROLLBACK

### **Respaldo Creado:**
```
C:\Users\Jose Luis\proyecto_dossier_BACKUP_20260303_[TIMESTAMP]
```

Este es un **clon exacto** del proyecto ANTES de cualquier cambio.

### **¿Y si algo no funciona?**

**Opción 1: Revertir Git**
```bash
git log --oneline                    # Ver commits
git reset --hard <commit_anterior>   # Volver atrás
```

**Opción 2: Usar el respaldo**
```bash
# Eliminar versión nueva
rm -r C:\Users\Jose Luis\proyecto_dossier

# Restaurar backup
cp -r C:\Users\Jose Luis\proyecto_dossier_BACKUP_20260303_* `
      C:\Users\Jose Luis\proyecto_dossier
```

**Garantía:** No perderemos información.

---

## 📋 PLAN DE EJECUCIÓN (5 PASOS)

### **FASE 1: Preparación** (30 min)
- ✅ Git commit del estado actual → **HECHO**
- ✅ Crear respaldo completo → **HECHO**
- ⏳ Crear estructura de carpetas → PRÓXIMO

### **FASE 2: Mover Archivos** (1 hora)
- Crear carpetas `app/`, `core/`, `generators/`, `scripts/`, `docs/`
- Mover archivos Python a sus nuevas carpetas
- Verificar que NO hay errores

### **FASE 3: Actualizar Imports** (1.5 horas)
- `app/streamlit_app.py` → Actualizar imports
- `generators/dashboard_generator.py` → Actualizar imports
- `generators/consolidado_generator.py` → Actualizar imports
- `core/metricas.py` → Verificar imports
- Pruebas: Que los imports funcionen

### **FASE 4: Actualizar Documentación** (1 hora)
- Consolidar en `docs/README.md`
- Crear `docs/GUIA_USUARIO.md`
- Eliminar archivos .md viejos (opcionalmente)

### **FASE 5: Testing y Validación** (1 hora)
- `streamlit run app/streamlit_app.py` → Debe funcionar
- Ingresar datos → Debe guardar
- Generar dashboards → Debe crear HTML
- Verificar que TODO funciona IGUAL que antes

---

## 🎅 ¿NIVEL KINDER? - EXPLICACIÓN SÚPER SIMPLE

**Tu proyecto es como una casa:**

🏠 **Ahora:**
- Sofá, TV, libros en la sala ← Revuelto
- Cama, almohadas, ropa en la sala ← Confusión
- Platos, comida, toallas en la sala ← Desorden
- TODO está en el mismo lugar

🏠 **Después:**
- **Sala:** Sofá, TV, libros
- **Dormitorio:** Cama, almohadas, ropa
- **Cocina:** Platos, comida
- **Baño:** Toallas
- **Biblioteca:** Documentación

**¿Qué cambia en tu uso del proyecto?**
- ❌ Nada que sea importante
- ✅ Todo funciona igual
- ✅ Solo está mejor organizado
- ✅ Más fácil para otros entender cómo funciona

---

## ✋ DETENERNOS AQUÍ

**AHORA:**

1. ✅ Commit hecho
2. ✅ Respaldo creado  
3. ✅ Plan documentado

**PRÓXIMO PASO:** Tú confirmas si estás de acuerdo con este plan.

Si dices **"SÍ, PROCEDE"**, entonces:
- Creo las carpetas
- Muevo los archivos
- Actualizo imports
- Hago pruebas
- Confirmamos que TODO funciona

Si dices **"NO, ESPERA"** o tienes dudas:
- Podemos ajustar el plan
- O cambiar a la OPCIÓN 2 (cambios mínimos)
- Sin problema

---

## ❓ PREGUNTAS ANTES DE PROCEDER

1. **¿Estás de acuerdo con la nueva estructura?**
2. **¿Quieres que consolide la documentación en `docs/`?**
3. **¿Quieres crear un CLI para facilitar el uso? (python cli.py run)**
4. **¿Hay algo que quieras que NO me cambie?**

**Espero tu confirmación.** 🚀
