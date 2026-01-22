# 📊 Control de Dossieres - Sistema de Gestión de Entregas

**Estado: ✅ VALIDADO Y LISTO PARA PRODUCCIÓN**

---

## 🎯 ¿Qué es este proyecto?

Sistema integrado para gestionar, visualizar y consolidar datos de entregas de contratistas (BAYSA y JAMAR) con:
- ✅ **App Web Streamlit** - Interfaz visual para ingresar y editar datos
- ✅ **Dashboards Interactivos** - Reportes ejecutivos en HTML con Plotly
- ✅ **CSVs Normalizados** - Almacenamiento consistente de datos
- ✅ **Validación Automática** - Chequeos de integridad del proyecto

---

## 🚀 Empezar Rápidamente (2 minutos)

### Opción A: Usar la App (RECOMENDADO)

```bash
cd "C:\Users\Jose Luis\proyecto_dossier"
streamlit run app_ingreso_datos.py
```

Se abrirá en tu navegador automáticamente. Desde ahí puedes:
- ✅ Ver resumen ejecutivo con métricas
- ✅ Agregar nuevos registros
- ✅ Editar datos existentes
- ✅ Generar dashboards

### Opción B: Validar Proyecto

```bash
python validar_proyecto.py
```

o

```bash
python estado_proyecto.py
```

### Opción C: Generar Dashboards Manualmente

```bash
python generar_todos_dashboards.py S186
```

---

## 📖 Documentación

| Archivo | Contenido |
|---------|-----------|
| **GUIA_RAPIDA.md** | ⭐ Lee esto primero - instrucciones paso a paso |
| **RESUMEN_ACTUALIZACION_FINAL.md** | Cambios y mejoras implementadas |
| **LIMPIEZA_Y_ACTUALIZACION.md** | Detalles técnicos de la limpieza |
| **ARQUITECTURA.md** | Diseño técnico completo |

---

## 📊 Datos

```
BAYSA
├── Normalizado: 191 registros (activo) ✅
└── Fuente: 178 registros (respaldo)

JAMAR
├── Normalizado: 259 registros (activo) ✅
└── Fuente: N/A
```

---

## ✅ Verificaciones Finales

✅ **5/5 checks pasados:**
- Todas las dependencias instaladas
- 9 módulos Python funcionando
- CSVs legibles y accesibles
- Directorios de salida creados
- App Streamlit compilable

✅ **Estadísticas:**
- 3,556 líneas de código
- 9 archivos Python
- 0 archivos obsoletos
- 0 problemas de importación

---

## 🎨 Características

### App Streamlit (app_ingreso_datos.py)

```
┌─────────────────────────────────────────┐
│ Control de Dossieres - Ingreso de Datos │
├─────────────────────────────────────────┤
│ Contratista: [BAYSA ▼]                  │
│ Origen:      [Normalizado ○]            │
├─────────────────────────────────────────┤
│ RESUMEN EJECUTIVO                       │
│ Total: 191 | Liberados: 100             │
│ Observados: 70 | En Revisión: 2         │
│ Planeados: 19 | Peso: 6.850 ton         │
├─────────────────────────────────────────┤
│ PRÓXIMAS ENTREGAS (BAYSA)                │
│ Entrega | Planeados | Peso (ton)        │
│ ENT001  | 5         | 1.200              │
│ ENT002  | 3         | 0.850              │
│ TOTAL   | 191       | 6.850              │
├─────────────────────────────────────────┤
│ [Agregar Nueva Fila]                     │
│ [Generar Dashboards] [↻ Refrescar]      │
└─────────────────────────────────────────┘
```

### Dashboards (HTML + Plotly)

- **dashboard_BAYSA_*.html** - Gráficos y tablas para BAYSA
- **dashboard_JAMAR_*.html** - Gráficos y tablas para JAMAR
- **dashboard_consolidado_*.html** - Vista combinada BAYSA + JAMAR

---

## 🔧 Estructura del Proyecto

```
proyecto_dossier/
├── 📄 app_ingreso_datos.py (488 líneas) ⭐ PRINCIPAL
├── 📄 dashboard.py (854 líneas)
├── 📄 dashboard_consolidado.py (1,222 líneas)
├── 📄 generar_todos_dashboards.py (204 líneas)
├── 📄 metricas_core.py (207 líneas)
├── 📄 utils_archivos.py (222 líneas)
├── 📄 validar_proyecto.py (195 líneas)
│
├── 📁 scripts/
│   ├── normalizar_baysa.py (73 líneas)
│   └── normalizar_jamar.py (91 líneas)
│
├── 📁 data/
│   ├── contratistas/
│   │   ├── BAYSA/
│   │   │   ├── ctrl_dosieres_BAYSA_normalizado.csv (191 reg)
│   │   │   └── ctrl_dosieres.csv (178 reg - fuente)
│   │   └── JAMAR/
│   │       └── ctrl_dosieres_JAMAR_normalizado.csv (259 reg)
│   └── _backup/ (respaldos automáticos)
│
├── 📁 output/
│   ├── dashboards/ (HTML generados)
│   ├── tablas/ (Tablas HTML)
│   └── historico/ (Archivos viejos)
│
├── 📁 .streamlit/
│   └── config.toml (tema ejecutivo)
│
├── 🎨 config.yaml (colores, estilos)
├── 📋 requirements.txt (dependencias)
│
└── 📖 Documentación
    ├── GUIA_RAPIDA.md ⭐
    ├── RESUMEN_ACTUALIZACION_FINAL.md
    ├── LIMPIEZA_Y_ACTUALIZACION.md
    ├── ARQUITECTURA.md
    └── README.md (este archivo)
```

---

## 🐍 Requisitos

**Python 3.10+** con:
- pandas ≥ 2.0.0
- plotly ≥ 5.0.0
- streamlit ≥ 1.30.0
- PyYAML ≥ 6.0.3
- openpyxl ≥ 3.0.0

Instalar: `pip install -r requirements.txt`

---

## 💡 Ejemplos de Uso

### 1. Ingresar nuevo registro desde la App

1. Abre: `streamlit run app_ingreso_datos.py`
2. Selecciona Contratista: BAYSA o JAMAR
3. Rellena formulario
4. Presiona "Agregar Fila"
5. ✅ Guardado automático con respaldo

### 2. Editar datos existentes

1. Abre la App
2. Busca en la tabla
3. Haz clic en cualquier celda
4. Modifica el valor
5. ✅ Se guarda automáticamente

### 3. Generar reportes

1. **Desde la App:** Presiona "Generar Dashboards"
2. **Manualmente:** `python generar_todos_dashboards.py S186`
3. ✅ Abre: `output/dashboards/dashboard_BAYSA_*.html`

---

## 🎯 Información Importante

### Encodings de Archivos

El proyecto maneja automáticamente diferentes encodings:
- **BAYSA:** latin-1 (Windows)
- **JAMAR:** utf-8-sig (UTF-8 con BOM)
- **Fallback:** Intenta utf-8, iso-8859-1, cp1252 si es necesario

### Backups Automáticos

Cada vez que editas datos, se crea un respaldo en `data/_backup/`

### Tema Ejecutivo

La app usa colores corporativos:
- Verde LIBERADO: #0F7C3F
- Interfaz limpia (menú oculto)
- Tipografía moderna sans-serif

---

## ⚠️ Troubleshooting

### "Streamlit no encontrado"
```bash
pip install streamlit>=1.30.0
```

### "Módulo no encontrado"
```bash
pip install -r requirements.txt
```

### CSV no se actualiza
```bash
# Reinicia la app con C en el navegador
# O: Ctrl+C en la terminal y vuelve a ejecutar
streamlit run app_ingreso_datos.py
```

### Validación falla
```bash
python validar_proyecto.py
# Revisa la salida para identificar el problema
```

---

## 📞 Próximos Pasos

1. **Ahora:** Lee [GUIA_RAPIDA.md](GUIA_RAPIDA.md)
2. **Luego:** Ejecuta `streamlit run app_ingreso_datos.py`
3. **Después:** Ingresa datos o genera dashboards
4. **Finalmente:** Explora la documentación técnica si necesitas cambios

---

## ✨ Mejoras Recientes

✅ Encodings robustos (ya no pierdes datos)
✅ Validación automática del proyecto
✅ Editor inline en la app
✅ Resumen ejecutivo con métricas correctas
✅ TOTAL row en tablas
✅ Tema ejecutivo limpio
✅ Documentación completa

---

**Última actualización:** 2025-01-17  
**Versión:** 1.0 (Post-Cleanup)  
**Estado:** ✅ LISTO PARA PRODUCCIÓN

```
[OK] 5/5 checks pasados
[OK] 9 módulos Python importables
[OK] 3,556 líneas de código
[OK] PROYECTO VALIDADO
```

---

**¿Preguntas?** Consulta [GUIA_RAPIDA.md](GUIA_RAPIDA.md) o [ARQUITECTURA.md](ARQUITECTURA.md)
