# Sistema de Protección contra Pérdida de Datos

## 📋 Resumen

Este documento describe el sistema de seguridad implementado para prevenir pérdida de datos, como el incidente del 19 de enero de 2026 donde se perdieron 13 registros BAYSA (191 → 178).

## 🔴 Incidente Original

**Fecha:** 19 de enero de 2026, 10:31 AM  
**Problema:** Script de normalización sobrescribió archivo CSV sin crear backup  
**Pérdida:** 13 registros BAYSA (de 191 a 178)  
**Causa Raíz:**
- CSV no rastreado por git (`.gitignore` excluye `*.csv`)
- Script no creaba backup antes de modificar
- Sin validación de conteo de registros

**Recuperación:** Archivo restaurado desde backup histórico en Excel consolidado (S186 del 17 de enero).

## 🛡️ Medidas Implementadas

### 1. Sistema de Backup Automático (`utils_backup.py`)

Módulo centralizado para gestión de backups:

```python
from utils_backup import crear_backup_automatico

# Crear backup antes de modificar cualquier archivo
backup = crear_backup_automatico(archivo_csv, mantener_ultimos=10)
```

**Funcionalidades:**
- ✅ Backup automático con timestamp
- ✅ Verificación de integridad
- ✅ Limpieza automática (mantiene últimos N backups)
- ✅ Restauración desde backup
- ✅ Listado de backups disponibles

### 2. Scripts de Normalización Actualizados

Ambos scripts ahora incluyen protección obligatoria:

**scripts/normalizar_baysa.py:**
```python
# CRÍTICO: Crear backup antes de cualquier modificación
if archivo_salida.exists():
    backup_path = crear_backup_automatico(archivo_salida, mantener_ultimos=10)
    if not verificar_integridad_backup(archivo_salida, backup_path):
        print("❌ ERROR: Backup no válido, abortando operación")
        return False
```

**scripts/normalizar_jamar.py:**
- Misma protección implementada

### 3. Validación Pre-Operación (`validar_pre_operacion.py`)

Script de validación integral que ejecuta:

```bash
python validar_pre_operacion.py
```

**Validaciones:**
1. ✅ Existencia de archivos críticos
2. ✅ Conteo de registros esperados (BAYSA: 191)
3. ✅ Backups disponibles (mínimo 3 recomendados)
4. ✅ Estructura de columnas requeridas

**Opciones:**
```bash
# Solo validar, sin crear backups
python validar_pre_operacion.py --no-backup

# Modo estricto (fallar con warnings)
python validar_pre_operacion.py --strict
```

### 4. Suite de Tests (`tests/test_backup_system.py`)

Tests comprensivos que incluyen:

```bash
# Ejecutar todos los tests
pytest tests/test_backup_system.py -v

# Solo tests críticos
pytest tests/test_backup_system.py::TestProteccionPerdidaDatos -v
```

**Coverage:**
- ✅ Creación y verificación de backups
- ✅ Limpieza de backups antiguos
- ✅ Restauración desde backup
- ✅ Protección contra pérdida específica (191→178)
- ✅ Integración completa del flujo

## 📝 Procedimientos Obligatorios

### Antes de Modificar Archivos CSV

**SIEMPRE ejecutar:**

```bash
# 1. Validar integridad actual
python validar_pre_operacion.py

# 2. Si validación pasa, proceder con operación
python scripts/normalizar_baysa.py
# o
python scripts/normalizar_jamar.py
```

### Procedimiento Manual de Backup

```python
from pathlib import Path
from utils_backup import crear_backup_automatico

archivo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
backup = crear_backup_automatico(archivo)
print(f"Backup creado: {backup}")
```

### Restauración desde Backup

```python
from pathlib import Path
from utils_backup import listar_backups_disponibles, restaurar_desde_backup

# Listar backups disponibles
archivo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
backups = listar_backups_disponibles(archivo)

for i, backup in enumerate(backups, 1):
    print(f"{i}. {backup.name}")

# Restaurar desde el más reciente
restaurar_desde_backup(backups[0], archivo)
```

## 🚨 Protocolo en Caso de Pérdida de Datos

Si se detecta pérdida de datos:

1. **NO EJECUTAR MÁS COMANDOS** que modifiquen archivos
2. Listar backups disponibles:
   ```python
   from utils_backup import listar_backups_disponibles
   backups = listar_backups_disponibles(archivo_afectado)
   ```
3. Verificar conteo de registros en backups
4. Restaurar desde el backup más reciente válido
5. Reportar el incidente para análisis

## 📊 Monitoreo y Logs

### Archivos de Backup

Ubicación: `data/contratistas/{CONTRATISTA}/`

Nomenclatura: `ctrl_dosieres_{CONTRATISTA}_normalizado_backup_{TIMESTAMP}.csv`

Ejemplo:
```
ctrl_dosieres_BAYSA_normalizado_backup_20260119_105353.csv
ctrl_dosieres_BAYSA_normalizado_backup_20260119_105636.csv
```

### Retención

- **Automática:** Se mantienen los últimos 10 backups
- **Manual:** Backups adicionales en `data/historico/`

## ✅ Checklist de Seguridad

Antes de cualquier operación con datos:

- [ ] ¿Se ejecutó `validar_pre_operacion.py`?
- [ ] ¿La validación pasó sin errores críticos?
- [ ] ¿Existen al menos 3 backups recientes?
- [ ] ¿El conteo de registros es el esperado?
- [ ] ¿Se confirmó que los scripts tienen protección de backup?

## 🔧 Configuración de Git

### Recomendación: Rastrear Archivos Críticos

Aunque `.gitignore` excluye `*.csv`, considerar:

```bash
# Opción 1: Forzar tracking de archivos normalizados críticos
git add -f data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv
git add -f data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv

# Opción 2: Modificar .gitignore para permitir archivos normalizados
# En .gitignore, cambiar:
# *.csv
# Por:
# *.csv
# !*_normalizado.csv
```

**⚠️ Nota:** Discutir con el equipo antes de cambiar política de git.

## 📚 Referencias

- **Módulo principal:** `utils_backup.py`
- **Validación:** `validar_pre_operacion.py`
- **Tests:** `tests/test_backup_system.py`
- **Scripts protegidos:**
  - `scripts/normalizar_baysa.py`
  - `scripts/normalizar_jamar.py`

## 🔄 Actualizaciones del Sistema

**Versión:** 1.0  
**Fecha:** 19 de enero de 2026  
**Autor:** Sistema de Protección de Datos  

**Cambios:**
- ✅ Implementado sistema de backup automático
- ✅ Actualizado scripts de normalización
- ✅ Creado validador pre-operación
- ✅ Agregada suite completa de tests
- ✅ Documentación de procedimientos

---

## ⚠️ IMPORTANTE

Este sistema NO reemplaza las buenas prácticas de:
1. Commits frecuentes en git
2. Revisión de código antes de ejecutar
3. Testing en entornos de desarrollo
4. Validación manual de resultados

**La prevención es la mejor protección.**
