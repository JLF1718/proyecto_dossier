# 👶 GUÍA DE USUARIO - NIVEL KINDER

## ¡HOLA! Bienvenido al Sistema de Dossieres 👋

Esta guía te explica **super simple** cómo usar el proyecto.

### 📖 NO NECESITAS SABER PROGRAMACIÓN. Solo sigue los pasos.

---

## 🎯 INICIO RÁPIDO (3 PASOS)

### PASO 1: Abre una Terminal

En Windows:
- Presiona `Windows + R`
- Escribe: `cmd`
- Presiona Enter

Deberías ver algo como:
```
C:\Users\Jose Luis\proyecto_dossier>
```

### PASO 2: Escribe Este Comando

```bash
python cli.py run
```

Y presiona Enter.

### PASO 3: ¡LISTO!

Se abrirá tu navegador automáticamente con la app. 

---

## 🌐 DENTRO DE LA APP (PASO A PASO)

### PANTALLA PRINCIPAL

Verás algo así:

```
┌─────────────────────────────────────────────┐
│  📊 Control de Dossieres - Ingreso de Datos │
└─────────────────────────────────────────────┘

Contratista: [ BAYSA ▼ ]

RESUMEN EJECUTIVO
├── Total: 191
├── Liberados: 100
├── En Revisión: 2
└── Planeados: 19

[TABLA CON DOSSIERES]
[BOTONES]
```

---

## 📋 TAREAS COMUNES

### TAREA 1: VER LOS DOSSIERES ACTUALES

1. Abre la app: `python cli.py run`
2. En "Contratista", selecciona **BAYSA** o **JAMAR**
3. Desplázate hacia abajo
4. ¡Ve la tabla con todos los dossieres!

---

### TAREA 2: AGREGAR UN NUEVO DOSSIER

1. En la app, busca la sección **"INGRESAR DATOS"**
2. Completa los campos:
   - **BLOQUE:** Ej: `BLOQUE-001`
   - **ETAPA:** Ej: `DISEÑO`
   - **ESTATUS:** Ej: `EN_REVISIÓN`
   - **PESO (kg):** Ej: `100`
   - **ENTREGA (solo BAYSA):** Ej: `S186`

3. Presiona el botón **"Agregar Fila"** 🟢

4. ¡LISTO! Los datos se guardan automáticamente.

---

### TAREA 3: CAMBIAR UN DOSSIER EXISTENTE

1. En la tabla, haz **CLICK en cualquier celda**
2. Se resaltará y puedes editar
3. Escribe el nuevo valor
4. Presiona **Enter**
5. ¡GUARDADO! ✅

---

### TAREA 4: GENERAR UN REPORTE (DASHBOARD)

**IMPORTANTE:** Antes de generar, debes completar estos datos:

1. Aquí está el secreto: **DEBES INGRESAR LA SEMANA PRIMERO**

   En la app, busca: **"SEMANA DE CORTE"**
   
   Escribe: `S186` (o la semana actual)

2. Presiona el botón **"Generar Dashboards"** 🟢

3. ¡Espera! (Tarda 30-60 segundos)

4. Verás: "✅ Dashboards generados correctamente"

5. Los archivos están en: `output/dashboards/` y `output/exports/`

---

## 🎨 LOS CAMPOS EXPLICADOS

### BLOQUE
- Ej: `BLOQUE-001`, `BASTIDOR-A`, `PLN-123`
- Simplemente un nombre único para el dossier

### ETAPA
- Opciones comunes:
  - `INGENIERÍA`
  - `DISEÑO`
  - `FABRICACIÓN`
  - `MONTAJE`
  - `PRUEBAS`
  - `ENTREGA`

### ESTATUS
- 🟢 **LIBERADO** - ¡Completado y entregado!
- 🟡 **EN_REVISIÓN** - En revisión, verificando
- 🔴 **OBSERVADO** - Tiene problemas, necesita atención
- ⚫ **PLANEADO** - Aún no inicia

### PESO (kg)
- Peso en **kilogramos**
- Ej: `100` = 100 kg
- Los dashboards lo mostrarán en **toneladas** (automático)

### ENTREGA (solo BAYSA)
- Formato: `S###`
- Ej: `S186`, `S1`, `S1020`
- La "S" de "Semana"

---

## 💚 LA SEMANA MÁS IMPORTANTE

### ¿QUÉ ES "SEMANA DE CORTE"?

Imagina que disparas una foto del proyecto en ese momento:

- Hoy tomaste datos de los dossieres
- Dices: "Foto de la semana **S186**"
- El sistema genera un reporte con esa información
- Lo guarda con timestamp (fecha y hora)

### EJEMPLO REAL:

```
Usuario: "Voy a generar un reporte"
Sistema: "¿Para qué semana?"
Usuario: "Para S186"
Sistema: "Perfecto. Tomando foto..."
Sistema: "✅ Listo: bloques_liberados_S186_20260303_143022.html"
```

### ¿POR QUÉ ES IMPORTANTE?

- Histórico: Puedes ver cómo estaba el proyecto en S185, S186, S187, etc.
- Auditoria: Saber exactamente cuándo cambiaron los datos
- Reportes: Un reporte "oficial" para esa semana

---

## 📂 DÓNDE ESTÁN LOS ARCHIVOS

### Mis datos están en:
```
📁 data/
   ├── 📁 contratistas/
   │   ├── 📁 BAYSA/
   │   │   └── ctrl_dosieres_BAYSA_normalizado.csv
   │   └── 📁 JAMAR/
   │       └── ctrl_dosieres_JAMAR_normalizado.csv
```

### Los reportes están en:
```
📁 output/
   ├── 📁 dashboards/  ← Los archivos HTML (abre con navegador)
   └── 📁 exports/     ← Histórico de semanas (no toques, es backup)
```

---

## 🔧 OTROS COMANDOS (TERMINAL)

Si necesitas hacer cosas más avanzadas:

```bash
# Ver estado del proyecto
python cli.py status

# Validar que todo funciona
python cli.py validate

# Generar reporte desde terminal (sin app)
python cli.py generate S186

# Crear respaldo
python cli.py backup
```

---

## ✅ CHECKLIST DE COSAS QUE VALEN LA PENA

- ✅ La app funciona sin internet
- ✅ Los datos se guardan automáticamente
- ✅ Los reportes se exportan con timestamp (no se pierden)
- ✅ Puedes editar cualquier dato en la tabla
- ✅ El proyecto valida datos automáticamente
- ✅ Cada semana es una "foto" del proyecto

---

## ❌ COSAS QUE NO HAGAS

- ❌ No edites manualmente los archivos CSV (usa la app)
- ❌ No elimines la carpeta `output/exports/` (es tu histórico)
- ❌ No cambies los nombres de las carpetas principales
- ❌ No toques `config.yaml` si no sabes qué haces

---

## 🚨 ALGO NO FUNCIONA? AQUÍ ESTÁN LAS RESPUESTAS

### "La app no abre"
Valida con:
```bash
python cli.py validate
```

### "No me aparecen los datos"
- Verifica que hayas seleccionado el contratista correcto (BAYSA/JAMAR)
- Recarga la página en el navegador

### "El reporte tardó mucho"
- Es normal (30-60 segundos la primera vez)
- Calcula métricas complejas

### "¿Dónde guardé mi trabajo?"
```
📁 data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv
o
📁 data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv
```

---

## 📚 LECTURA ADICIONAL

Si necesitas entender mejor cómo funciona:

- 📖 [README.md](README.md) - Descripción general
- 🏗️ [ARQUITECTURA.md](ARQUITECTURA.md) - Cómo está hecho
- 📋 [PROCEDIMIENTOS.md](PROCEDIMIENTOS.md) - Procesos específicos

---

## 🎉 ¡LISTO!

Ya sabes todo lo necesario para usar el proyecto.

**Próximo paso:**

Abre una terminal y escribe:

```bash
python cli.py run
```

¡Disfrutalo! 🚀
