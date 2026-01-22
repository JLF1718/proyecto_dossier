# Guía Rápida: Protección de Datos

## ⚡ Comandos Rápidos

### Validación y Backup (OBLIGATORIO antes de modificar datos)

```bash
# Validar integridad y crear backups
python validar_pre_operacion.py
```

### Normalización Segura

```bash
# Ahora incluyen backup automático
python scripts/normalizar_baysa.py
python scripts/normalizar_jamar.py
```

### Ver Backups Disponibles

```python
from pathlib import Path
from utils_backup import listar_backups_disponibles

archivo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
for backup in listar_backups_disponibles(archivo):
    print(f"📦 {backup.name}")
```

### Restaurar desde Backup

```python
from pathlib import Path
from utils_backup import restaurar_desde_backup, listar_backups_disponibles

archivo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
backups = listar_backups_disponibles(archivo)

# Restaurar desde el más reciente
restaurar_desde_backup(backups[0], archivo)
```

### Crear Backup Manual

```python
from pathlib import Path
from utils_backup import crear_backup_automatico

archivo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
backup = crear_backup_automatico(archivo)
print(f"✅ Backup: {backup}")
```

### Ejecutar Tests

```bash
# Todos los tests
pytest tests/test_backup_system.py -v

# Solo tests críticos de protección
pytest tests/test_backup_system.py::TestProteccionPerdidaDatos -v

# Tests de regresión del bug
pytest tests/test_backup_system.py::TestRegresionBugPerdidaDatos -v
```

## 🎯 Flujo de Trabajo Recomendado

```
1. python validar_pre_operacion.py
   ↓ (si pasa)
2. python scripts/normalizar_baysa.py
   ↓ (verifica automáticamente)
3. python validar_pre_operacion.py --no-backup
   ↓ (confirma integridad)
4. streamlit run app_ingreso_datos.py
```

## 🚨 En Caso de Emergencia

```python
# 1. Detener todas las operaciones
# 2. Listar backups
from utils_backup import listar_backups_disponibles
from pathlib import Path

archivo = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
backups = listar_backups_disponibles(archivo)

# 3. Verificar conteo en cada backup
import pandas as pd
for backup in backups[:5]:
    df = pd.read_csv(backup)
    print(f"{backup.name}: {len(df)} registros")

# 4. Restaurar el correcto
from utils_backup import restaurar_desde_backup
restaurar_desde_backup(backups[0], archivo)  # o el índice correcto
```

## 📊 Conteos Esperados

| Contratista | Registros Esperados | Última Validación |
|-------------|--------------------:|-------------------|
| BAYSA       | 191                 | 2026-01-19        |
| JAMAR       | 259                 | 2026-01-19        |

## ✅ Checklist Diario

- [ ] Ejecutar `validar_pre_operacion.py` al inicio del día
- [ ] Verificar que existen al menos 3 backups de cada archivo
- [ ] Confirmar conteos de registros coinciden con lo esperado
- [ ] Antes de cualquier normalización: crear backup manual adicional

## 📁 Ubicación de Archivos

```
proyecto_dossier/
├── utils_backup.py              # Módulo de backup
├── validar_pre_operacion.py     # Validador principal
├── PROTECCION_DATOS.md          # Documentación completa
├── GUIA_RAPIDA_PROTECCION.md    # Esta guía
├── scripts/
│   ├── normalizar_baysa.py      # Con protección
│   └── normalizar_jamar.py      # Con protección
├── tests/
│   └── test_backup_system.py    # Suite de tests
└── data/contratistas/
    ├── BAYSA/
    │   ├── ctrl_dosieres_BAYSA_normalizado.csv
    │   └── ctrl_dosieres_BAYSA_normalizado_backup_*.csv
    └── JAMAR/
        ├── ctrl_dosieres_JAMAR_normalizado.csv
        └── ctrl_dosieres_JAMAR_normalizado_backup_*.csv
```

## 🔗 Referencias

- Documentación completa: [PROTECCION_DATOS.md](PROTECCION_DATOS.md)
- Tests: `pytest tests/test_backup_system.py -v`
