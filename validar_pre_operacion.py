"""
Script de validación pre-operación para prevenir pérdida de datos.
Ejecutar ANTES de cualquier operación que modifique archivos CSV.
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Importar utilidades
sys.path.insert(0, str(Path(__file__).parent))
from utils_backup import crear_backup_automatico, listar_backups_disponibles


class ValidadorDatos:
    """Validador de integridad de datos antes de operaciones."""
    
    def __init__(self):
        self.errores = []
        self.warnings = []
        self.archivos_criticos = [
            Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv"),
            Path("data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv"),
        ]
    
    def validar_todo(self) -> bool:
        """Ejecuta todas las validaciones."""
        print("=" * 70)
        print("🔍 VALIDACIÓN DE INTEGRIDAD DE DATOS")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.validar_archivos_existen()
        self.validar_conteos_registros()
        self.validar_backups_disponibles()
        self.validar_estructura_columnas()
        
        print("\n" + "=" * 70)
        if self.errores:
            print("❌ ERRORES CRÍTICOS ENCONTRADOS:")
            for error in self.errores:
                print(f"   • {error}")
            print("\n⚠️  NO SE RECOMIENDA PROCEDER CON OPERACIONES DE DATOS")
            return False
        elif self.warnings:
            print("⚠️  ADVERTENCIAS:")
            for warning in self.warnings:
                print(f"   • {warning}")
            print("\n✅ Se puede proceder con PRECAUCIÓN")
            return True
        else:
            print("✅ TODAS LAS VALIDACIONES PASARON")
            print("✅ Es seguro proceder con operaciones de datos")
            return True
    
    def validar_archivos_existen(self):
        """Verifica que archivos críticos existan."""
        print("📂 Validando existencia de archivos...")
        for archivo in self.archivos_criticos:
            if not archivo.exists():
                self.errores.append(f"Archivo crítico no encontrado: {archivo}")
                print(f"   ❌ {archivo.name}")
            else:
                print(f"   ✅ {archivo.name}")
    
    def validar_conteos_registros(self):
        """Verifica conteos de registros esperados."""
        print("\n📊 Validando conteos de registros...")
        
        conteos_esperados = {
            "BAYSA": 191,  # Conteo histórico confirmado
            "JAMAR": None  # No sabemos el conteo esperado
        }
        
        for archivo in self.archivos_criticos:
            if not archivo.exists():
                continue
            
            try:
                df = pd.read_csv(archivo, encoding='utf-8-sig')
                conteo_actual = len(df)
                
                contratista = "BAYSA" if "BAYSA" in archivo.name else "JAMAR"
                esperado = conteos_esperados.get(contratista)
                
                if esperado and conteo_actual != esperado:
                    self.errores.append(
                        f"{contratista}: Conteo incorrecto. "
                        f"Esperado: {esperado}, Actual: {conteo_actual}"
                    )
                    print(f"   ❌ {contratista}: {conteo_actual} registros "
                          f"(esperado: {esperado})")
                else:
                    print(f"   ✅ {contratista}: {conteo_actual} registros")
                    
            except Exception as e:
                self.errores.append(f"Error leyendo {archivo.name}: {e}")
    
    def validar_backups_disponibles(self):
        """Verifica que existan backups recientes."""
        print("\n🔒 Validando backups disponibles...")
        
        for archivo in self.archivos_criticos:
            if not archivo.exists():
                continue
            
            backups = listar_backups_disponibles(archivo)
            
            if len(backups) == 0:
                self.warnings.append(f"Sin backups para {archivo.name}")
                print(f"   ⚠️  {archivo.name}: Sin backups")
            elif len(backups) < 3:
                self.warnings.append(f"Pocos backups para {archivo.name}: {len(backups)}")
                print(f"   ⚠️  {archivo.name}: {len(backups)} backups (recomendado: 5+)")
            else:
                print(f"   ✅ {archivo.name}: {len(backups)} backups disponibles")
                
                # Mostrar backup más reciente
                backup_reciente = backups[0]
                edad_segundos = (datetime.now().timestamp() - 
                               backup_reciente.stat().st_mtime)
                edad_horas = edad_segundos / 3600
                print(f"      Más reciente: {backup_reciente.name} "
                      f"({edad_horas:.1f} horas)")
    
    def validar_estructura_columnas(self):
        """Verifica que columnas requeridas existan."""
        print("\n📋 Validando estructura de columnas...")
        
        columnas_requeridas_baysa = ['BLOQUE', 'ETAPA', 'ESTATUS', 'PESO']
        columnas_requeridas_jamar = ['BLOQUE', 'ETAPA', 'ESTATUS', 'PESO']
        
        validaciones = [
            (Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv"),
             columnas_requeridas_baysa, "BAYSA"),
            (Path("data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv"),
             columnas_requeridas_jamar, "JAMAR"),
        ]
        
        for archivo, requeridas, nombre in validaciones:
            if not archivo.exists():
                continue
            
            try:
                df = pd.read_csv(archivo, encoding='utf-8-sig', nrows=0)
                columnas_actuales = set(df.columns)
                faltantes = set(requeridas) - columnas_actuales
                
                if faltantes:
                    self.errores.append(
                        f"{nombre}: Columnas faltantes: {faltantes}"
                    )
                    print(f"   ❌ {nombre}: Faltan columnas {faltantes}")
                else:
                    print(f"   ✅ {nombre}: Todas las columnas requeridas presentes")
                    
            except Exception as e:
                self.errores.append(f"Error validando columnas de {nombre}: {e}")


def crear_backups_todos_criticos():
    """Crea backups de todos los archivos críticos."""
    print("\n🔒 CREANDO BACKUPS DE SEGURIDAD...")
    print("=" * 70)
    
    archivos_criticos = [
        Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv"),
        Path("data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv"),
    ]
    
    backups_creados = []
    for archivo in archivos_criticos:
        if archivo.exists():
            try:
                backup = crear_backup_automatico(archivo, mantener_ultimos=10)
                backups_creados.append(backup)
                print(f"✅ Backup creado: {backup.name}")
                print(f"   Tamaño: {backup.stat().st_size:,} bytes")
            except Exception as e:
                print(f"❌ Error creando backup de {archivo.name}: {e}")
    
    print("=" * 70)
    print(f"✅ Total de backups creados: {len(backups_creados)}\n")
    return backups_creados


def validacion_pre_operacion(crear_backups: bool = True) -> bool:
    """
    Ejecuta validación completa antes de operaciones.
    
    Args:
        crear_backups: Si True, crea backups automáticos
    
    Returns:
        True si es seguro proceder, False si hay errores críticos
    """
    validador = ValidadorDatos()
    resultado = validador.validar_todo()
    
    if resultado and crear_backups:
        crear_backups_todos_criticos()
    
    return resultado


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validación pre-operación de integridad de datos"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No crear backups automáticos"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fallar también con warnings (modo estricto)"
    )
    
    args = parser.parse_args()
    
    resultado = validacion_pre_operacion(crear_backups=not args.no_backup)
    
    if not resultado:
        print("\n⚠️  Validación falló con errores críticos")
        sys.exit(1)
    
    if args.strict:
        validador = ValidadorDatos()
        validador.validar_todo()
        if validador.warnings:
            print("\n⚠️  Modo estricto: Fallando por warnings")
            sys.exit(1)
    
    sys.exit(0)
