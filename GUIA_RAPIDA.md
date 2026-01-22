# 🚀 Guía Rápida - Proyecto Control de Dossieres

## Estado: ✅ VALIDADO Y LISTO PARA PRODUCCIÓN

**Última validación:** 5/5 checks pasados  
**Módulos:** 9 archivos Python, 3,556 líneas de código  
**Base de datos:** BAYSA (191 registros), JAMAR (259 registros)

---

## 📋 Opción 1: Usar la App Streamlit (RECOMENDADO)

La forma más fácil y visual de trabajar con el proyecto.

### Paso 1: Abre Terminal en el Proyecto

```bash
cd "C:\Users\Jose Luis\proyecto_dossier"
```

### Paso 2: Ejecuta la App

```bash
streamlit run app_ingreso_datos.py
```

**Resultado:** Se abre automáticamente en tu navegador (http://localhost:8501)

### Paso 3: Usa la App

En la app encontrarás:

1. **Selector de Contratista**
   - BAYSA (191 registros)
   - JAMAR (259 registros)

2. **Selector de Origen**
   - Normalizado (recomendado, datos actualizados)
   - Fuente (backup, datos originales)

3. **Formulario de Ingreso**
   - BLOQUE
   - ETAPA
   - ESTATUS (Planeado, Observado, En Revisión, Liberado)
   - PESO (en kg)
   - No. REVISIÓN (opcional)
   - ENTREGA (solo BAYSA)

4. **Resumen Ejecutivo**
   - Total de registros
   - Cantidad por estado
   - Peso total en toneladas

5. **Editor de Datos**
   - Tabla con 5 columnas principales
   - Haz clic para editar valores
   - Se guardan automáticamente

6. **Próximas Entregas** (solo BAYSA)
   - Tabla con fechas de entrega planeadas
   - TOTAL row con agregados

7. **Generar Dashboards**
   - Botón para crear 3 dashboards:
     - BAYSA individual
     - JAMAR individual
     - Consolidado (BAYSA + JAMAR)
   - Archivos HTML en `output/dashboards/`

---

## 📊 Opción 2: Generar Dashboards Manualmente

Si prefieres solo generar los reportes sin usar la app.

```bash
python generar_todos_dashboards.py S186
```

(Reemplaza `S186` con la semana/número que necesites)

**Salida:**
- `output/dashboards/dashboard_BAYSA_*.html`
- `output/dashboards/dashboard_JAMAR_*.html`
- `output/dashboards/dashboard_consolidado_*.html`

---

## ✅ Opción 3: Validar el Proyecto

Para verificar que todo está funcionando correctamente.

```bash
python validar_proyecto.py
```

o

```bash
python estado_proyecto.py
```

**Resultado esperado:** 5/5 checks pasados

---

## 🛠️ Opciones Avanzadas

### Normalizar Datos Fuente a Formato Estándar

```bash
python scripts/normalizar_baysa.py
python scripts/normalizar_jamar.py
```

Esto regenera los CSVs normalizados desde los datos fuente.

### Ver la Estructura del Proyecto

```bash
tree /F
```

o explorar manualmente en el explorador de archivos.

---

## 📁 Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| `app_ingreso_datos.py` | APP PRINCIPAL (Streamlit) |
| `dashboard.py` | Genera dashboard individual |
| `dashboard_consolidado.py` | Genera dashboard consolidado |
| `generar_todos_dashboards.py` | Orquestador de dashboards |
| `metricas_core.py` | Cálculos centralizados |
| `validar_proyecto.py` | Validación automática |
| `config.yaml` | Estilos y colores |
| `.streamlit/config.toml` | Tema ejecutivo |

---

## 💾 Datos

| Ruta | Contenido | Estado |
|------|-----------|--------|
| `data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv` | 191 registros BAYSA | ✅ Activo |
| `data/contratistas/BAYSA/ctrl_dosieres.csv` | 178 registros (fuente) | ✅ Respaldo |
| `data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv` | 259 registros JAMAR | ✅ Activo |
| `data/_backup/` | Copias automáticas | ✅ Auto-creadas |

---

## 🎨 Tema Ejecutivo

La app utiliza colores corporativos:
- **Verde LIBERADO:** #0F7C3F
- **Tipografía:** Sans-serif moderna
- **Menú oculto:** Interfaz limpia (solo contenido)

---

## ⚡ Atajos de Teclado en Streamlit

- `C`: Limpiar caché (si la app se comporta raro)
- `R`: Reiniciar script
- `Q`: Salir

---

## 🐛 Troubleshooting

### Error: "Streamlit not found"
```bash
pip install streamlit>=1.30.0
```

### Error: "Module not found"
```bash
pip install -r requirements.txt
```

### CSV no se actualiza
```bash
# Limpiar caché de Streamlit
rm -r ~/.streamlit/
```

### App se cuelga
```bash
# Presiona Ctrl+C en la terminal
# Luego vuelve a ejecutar:
streamlit run app_ingreso_datos.py
```

---

## 📞 Contacto

Si encuentras problemas:

1. Ejecuta: `python validar_proyecto.py`
2. Revisa la salida para identificar el error
3. Intenta regenerar los dashboards con: `python generar_todos_dashboards.py`

---

## 📚 Documentación Adicional

- `ARQUITECTURA.md` - Diseño técnico completo
- `RESUMEN_ACTUALIZACION_FINAL.md` - Cambios recientes
- `LIMPIEZA_Y_ACTUALIZACION.md` - Detalles de limpieza
- `PRODUCCION_RESUMEN.md` - Resumen de producción

---

**¡Listo para usar! 🎉**

Pregunta: ¿Qué deseas hacer?
1. Usar la app Streamlit
2. Generar dashboards
3. Editar datos manualmente
