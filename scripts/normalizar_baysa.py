#!/usr/bin/env python3
"""
Normalización de CSV BAYSA -> Formato de Dashboard
==================================================

Convierte el CSV de BAYSA al formato estándar del dashboard.
Entrada:  data/contratistas/BAYSA/ctrl_dosieres.csv
Salida:   data/ctrl_dosieres_BAYSA_normalizado.csv
"""

import pandas as pd
from pathlib import Path
import sys

# Importar utilidades de backup
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils_backup import crear_backup_automatico, verificar_integridad_backup

def normalizar_baysa():
    """Normaliza CSV de BAYSA."""
    
    archivo_entrada = Path("data/contratistas/BAYSA/ctrl_dosieres.csv")
    archivo_salida = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
    
    # CRÍTICO: Crear backup antes de cualquier modificación
    if archivo_salida.exists():
        try:
            backup_path = crear_backup_automatico(archivo_salida, mantener_ultimos=10)
            print(f"🔒 Backup de seguridad creado: {backup_path.name}")
            if not verificar_integridad_backup(archivo_salida, backup_path):
                print("❌ ERROR: Backup no válido, abortando operación")
                return False
        except Exception as e:
            print(f"❌ ERROR CRÍTICO: No se pudo crear backup: {e}")
            print("   Operación cancelada por seguridad")
            return False
    
    if not archivo_entrada.exists():
        print(f"❌ Archivo no encontrado: {archivo_entrada}")
        return False
    
    try:
        # Leer CSV
        df = pd.read_csv(archivo_entrada, encoding='utf-8-sig')
        
        print(f"📂 Leyendo: {archivo_entrada}")
        print(f"   Registros: {len(df)}")
        print(f"   Columnas: {list(df.columns)}")
        
        # Mapeo de estatus -> canónico del dashboard
        status_map = {
            "PLANEADO": "PLANEADO",
            "LIBERADO": "LIBERADO",
            "OBSERVADO": "OBSERVADO",  # A corrección (contratista atendiendo comentarios)
            "EN_REVISIÓN": "EN_REVISIÓN",  # Revisión técnica interna
            "BAYSA_ATENDIENDO_COMENTARIOS": "OBSERVADO",  # Mapeo de antiguo nombre
            "INPROS_REVISANDO": "EN_REVISIÓN",  # Mapeo de antiguo nombre
            "NO_INICIADO": "PLANEADO",
            "POR_ASIGNAR": "PLANEADO",
        }
        
        # Normalizar estatus si existe la columna
        if "ESTATUS" in df.columns:
            df["ESTATUS_RAW"] = df["ESTATUS"].astype(str).str.strip()
            df["ESTATUS"] = df["ESTATUS_RAW"].map(status_map).fillna(df["ESTATUS_RAW"]).astype(str)
            df = df.drop(columns=["ESTATUS_RAW"])
        
        # Validar columnas requeridas
        columnas_requeridas = ["BLOQUE", "ETAPA", "ESTATUS", "PESO"]
        faltantes = [c for c in columnas_requeridas if c not in df.columns]
        if faltantes:
            print(f"❌ Columnas faltantes: {faltantes}")
            return False
        
        # Guardar CSV normalizado
        df.to_csv(archivo_salida, index=False, encoding='utf-8')
        
        print(f"✅ Guardado: {archivo_salida}")
        print(f"\nDistribución de estatus:")
        print(df["ESTATUS"].value_counts().to_string())
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = normalizar_baysa()
    sys.exit(0 if success else 1)
