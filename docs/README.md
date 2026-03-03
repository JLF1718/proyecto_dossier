# 📊 Control de Dossieres - Sistema de Gestión de Entregas

**Estado: ✅ REFACTORIZADO Y LISTO PARA PRODUCCIÓN**

---

## 🎯 ¿QUÉ ES ESTE PROYECTO?

Sistema integrado para gestionar, visualizar y consolidar datos de entregas de contratistas (BAYSA y JAMAR):

- 🌐 **App Web (Streamlit)** - Interfaz visual para ingresar y editar datos
- 📊 **Dashboards Interactivos** - Reportes ejecutivos en HTML con Plotly  
- 💾 **CSVs Normalizados** - Almacenamiento consistente y versionado
- ✅ **Validación Automática** - Chequeos de integridad continua
- ⏱️ **Histórico de Cortes** - Cada corte semanal se almacena en `output/exports/`

---

## 🚀 EMPEZAR (2 OPCIONES)

### ✅ OPCIÓN A: Usar la App (RECOMENDADO)

```bash
cd "C:\Users\Jose Luis\proyecto_dossier"

# Método 1: Directo (más rápido)
python cli.py run

# Método 2: Detallado
streamlit run app/streamlit_app.py
```

Se abrirá en tu navegador automáticamente. **Flujo típico:**

1. Selecciona contratista (BAYSA o JAMAR)
2. Ve resumen de dossieres  
3. Ingresa un nuevo dossier en la tabla
4. **Ingresa SEMANA de corte** (ej: S186)
5. Presiona "Generar Dashboards"
6. Los archivos se guardan en `output/exports/` con timestamp

---

### ✅ OPCIÓN B: Desde Terminal (CLI)

```bash
# Ver todas las opciones
python cli.py --help

# Generar dashboards para semana específica
python cli.py generate S186

# Validar integridad del proyecto
python cli.py validate

# Ver estado rápido
python cli.py status
```

---

## 📁 ESTRUCTURA DEL PROYECTO (DESPUÉS DE REFACTORIZACIÓN)

```
proyecto_dossier/
│
├── 📁 app/                          
│   └── streamlit_app.py             ← LA APP PRINCIPAL
│       (antes: app_ingreso_datos.py)
│
├── 📁 core/                         
│   ├── metricas.py                  ← Cálculos de números
│   └── __init__.py                  (antes: metricas_core.py)
│
├── 📁 generators/                   
│   ├── dashboard_generator.py        ← Genera dashboards BAYSA/JAMAR
│   ├── consolidado_generator.py      ← Genera consolidado
│   ├── utils_generator.py            ← Funciones compartidas
│   └── __init__.py
│
├── 📁 scripts/                      
│   ├── cli_generar.py               ← Script CLI
│   ├── normalizar_baysa.py           ← Normalizar datos BAYSA
│   ├── normalizar_jamar.py           ← Normalizar datos JAMAR
│   ├── exportar_bloques_liberados.py
│   └── maintenance/
│       ├── validar_integridad.py    ← Validar proyecto
│       ├── estado_sistema.py         ← Ver status
│       ├── backup_helper.py          ← Respaldo automático
│       └── __init__.py
│
├── 📁 docs/                         ← 🎯 DOCUMENTACIÓN CONSOLIDADA
│   ├── README.md                    ← Estás aquí
│   ├── GUIA_USUARIO.md              ← Paso a paso (nivel kinder)
│   ├── ARQUITECTURA.md              ← Cómo funciona internamente
│   ├── PROCEDIMIENTOS.md            ← Tareas específicas
│   └── HISTORICO.md                 ← Cambios realizados
│
├── 📁 data/                         ← 💾 DATOS (NO SE TOCA)
│   ├── contratistas/
│   │   ├── BAYSA/
│   │   │   ├── ctrl_dosieres_BAYSA_normalizado.csv     ← ACTIVO
│   │   │   └── ctrl_dosieres.csv (respaldo)
│   │   └── JAMAR/
│   │       ├── ctrl_dosieres_JAMAR_normalizado.csv     ← ACTIVO
│   │       └── ctrl_dosieres.csv (respaldo)
│   └── historico/
│       ├── BAYSA/
│       ├── JAMAR/
│       └── consolidado/
│
├── 📁 output/                       ← 📊 RESULTADOS
│   ├── dashboards/                  ← todos los HTML generados
│   ├── tablas/                      ← tablas consolidadas
│   ├── exports/                     ← 🔴 HISTÓRICO DE CORTES SEMANALES (IMPORTANTE)
│   ├── cache/                       ← caché de cálculos
│   └── historico/                   ← archivos viejos (para audit)
│
├── 📁 tests/
│   ├── test_metricas.py
│   ├── test_generators.py
│   └── test_integridad.py
│
├── config.yaml                      ← Estilos y colores
├── requirements.txt                 ← Dependencias
├── cli.py                           ← 🎯 ARCHIVO PRINCIPAL (NUEVO)
├── .streamlit/config.toml           ← Tema de Streamlit
│
└── .git/                            ← Control de versiones
```

---

## 📊 DATOS ACTUALES

```
BAYSA (Normalizado)
├── Registros: 191 ✅
├── Ruta: data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv
└── Último corte: variable (ingresado por usuario)

JAMAR (Normalizado)
├── Registros: 259 ✅
├── Ruta: data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv
└── Último corte: variable (ingresado por usuario)
```

---

## ⚠️ IMPORTANTE: HISTÓRICO DE CORTES SEMANALES

Cada vez que generas un dashboard, el sistema:

1. **Recibe la SEMANA** del usuario (ej: S186)
2. **Genera los dashboards** para esa semana
3. **Almacena en:** `output/exports/bloques_liberados_S186_TIMESTAMP.json|html`

**Esto es CRÍTICO:** No se pierda nada del histórico. Cada corte es una fotografía del proyecto en ese momento.

---

## 🎯 FLUJO TÍPICO (PASO A PASO)

### 1. Abrir la App
```bash
python cli.py run
```

### 2. Ingresar Datos
- Selecciona BAYSA o JAMAR
- Llena la tabla con nuevos dossieres
- Presiona "Agregar"

### 3. Generar Corte Semanal
- Ingresa SEMANA: `S186`
- Presiona "Generar Dashboards"
- Espera confirmación ✅

### 4. Ver Resultados
- Los dashboards se generan en: `output/dashboards/`
- Se exportan en: `output/exports/` (con timestamp)
- Puedes abrirlos con Live Server o navegador

---

## 📚 DOCUMENTACIÓN DETALLADA

| Archivo | Para Qué | Lee si... |
|---------|----------|-----------|
| **GUIA_USUARIO.md** | Instrucciones paso a paso | Quieres saber cómo usarlo |
| **ARQUITECTURA.md** | Diseño técnico completo | Quieres entender el código |
| **PROCEDIMIENTOS.md** | Tareas específicas | Tienes una tarea particular |
| **HISTORICO.md** | Cambios realizados | Quieres ver qué cambió |

---

## ✅ COMANDOS ÚTILES

```bash
# Abrir la app (RECOMENDADO)
python cli.py run

# Generar dashboards sin abrir app
python cli.py generate S186

# Validar que todo funciona
python cli.py validate

# Ver estado rápido
python cli.py status

# Normalizar datos BAYSA
python scripts/normalizar_baysa.py

# Normalizar datos JAMAR
python scripts/normalizar_jamar.py

# Ver respaldo automático
python scripts/maintenance/backup_helper.py
```

---

## 🛠️ REQUISITOS

- Python 3.9+
- Streamlit
- Pandas
- Plotly
- PyYAML

**Instalar:**
```bash
pip install -r requirements.txt
```

---

## ✨ CARACTERÍSTICAS PRINCIPALES

### 🌐 App Streamlit
- Interfaz limpia e intuitiva
- Edición inline de datos
- Resumen ejecutivo con métricas
- Tabla de próximas entregas

### 📊 Dashboards Interactivos  
- Gráficos de estatus por contratista
- Comparativa consolidada
- Tablas con histórico
- Exportables a HTML

### 💾 Almacenamiento
- CSVs normalizados y consistentes
- Histórico automático de cambios
- Respaldos en `data/historico/`
- Exportaciones con timestamp

### ✅ Validación
- Verificación de integridad del proyecto
- Chequeos de inconsistencias
- Alertas automáticas

---

## 🔒 SEGURIDAD (RESPALDOS)

Automaticamente se crean respaldos:
- 📁 `data/historico/BAYSA/` - Histórico BAYSA
- 📁 `data/historico/JAMAR/` - Histórico JAMAR
- 📁 `output/historico/` - Exporte viejos

**Manual:** `python scripts/maintenance/backup_helper.py`

---

## 🎨 PERSONALIZACIÓN

Edita `config.yaml` para:
- Cambiar colores de estatus
- Ajustar tamaños de gráficos
- Modificar fuentes tipográficas
- Configurar entregas esperadas

---

## 🆘 AYUDA

¿No funciona algo?

1. **Valida el proyecto:** `python cli.py validate`
2. **Ve el estado:** `python cli.py status`
3. **Lee:** [GUIA_USUARIO.md](GUIA_USUARIO.md)
4. **Lee:** [PROCEDIMIENTOS.md](PROCEDIMIENTOS.md)

---

## 📞 INFORMACIÓN

- **Última actualización:** 3 de Marzo de 2026
- **Versión:** 2.0 (Refactorización Opción 1)
- **Estado:** ✅ PRODUCCIÓN
- **Respaldo:** ✅ C:\Users\Jose Luis\proyecto_dossier_BACKUP_20260303_162442

---

## 🚀 LISTO PARA USAR

¡El proyecto está totalmente refactorizado y listo para producción!

**Próximo paso:** Abre una terminal y ejecuta:

```bash
python cli.py run
```

¡Disfrutalo! 🎉
