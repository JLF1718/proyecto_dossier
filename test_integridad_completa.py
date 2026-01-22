"""
Test de integridad completa del sistema.
Verifica todos los componentes críticos.
"""

import pandas as pd
from pathlib import Path
import sys

def test_archivos_criticos():
    """Test 1: Verificar que archivos críticos existan."""
    print("=" * 70)
    print("TEST 1: ARCHIVOS CRÍTICOS")
    print("=" * 70)
    
    archivos = {
        "BAYSA normalizado": Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv"),
        "JAMAR normalizado": Path("data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv"),
        "Config": Path("config.yaml"),
        "Dashboard script": Path("dashboard.py"),
        "Dashboard consolidado": Path("dashboard_consolidado.py"),
        "App Streamlit": Path("app_ingreso_datos.py"),
        "Utils backup": Path("utils_backup.py"),
        "Validador": Path("validar_pre_operacion.py"),
    }
    
    errores = 0
    for nombre, ruta in archivos.items():
        if ruta.exists():
            print(f"✅ {nombre}: OK ({ruta.stat().st_size:,} bytes)")
        else:
            print(f"❌ {nombre}: NO ENCONTRADO")
            errores += 1
    
    print(f"\nResultado: {len(archivos) - errores}/{len(archivos)} archivos OK\n")
    return errores == 0

def test_conteos_datos():
    """Test 2: Verificar conteos esperados."""
    print("=" * 70)
    print("TEST 2: CONTEOS DE DATOS")
    print("=" * 70)
    
    try:
        # BAYSA
        df_baysa = pd.read_csv(
            "data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv",
            encoding='utf-8-sig'
        )
        print(f"BAYSA: {len(df_baysa)} registros")
        
        if len(df_baysa) != 191:
            print(f"❌ ERROR: Se esperaban 191 registros BAYSA, encontrados {len(df_baysa)}")
            return False
        
        # Distribución de estatus
        estatus_dist = df_baysa['ESTATUS'].value_counts()
        print("\nDistribución ESTATUS:")
        for estatus, count in estatus_dist.items():
            print(f"  {estatus}: {count}")
        
        liberados = (df_baysa['ESTATUS'] == 'LIBERADO').sum()
        if liberados != 100:
            print(f"⚠️ ADVERTENCIA: Se esperaban 100 LIBERADOS, encontrados {liberados}")
        
        # JAMAR
        df_jamar = pd.read_csv(
            "data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv",
            encoding='utf-8-sig'
        )
        print(f"\nJAMAR: {len(df_jamar)} registros")
        
        print("\n✅ Conteos correctos")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_estructura_columnas():
    """Test 3: Verificar estructura de columnas."""
    print("\n" + "=" * 70)
    print("TEST 3: ESTRUCTURA DE COLUMNAS")
    print("=" * 70)
    
    columnas_requeridas = ['BLOQUE', 'ETAPA', 'ESTATUS', 'PESO']
    
    try:
        df_baysa = pd.read_csv(
            "data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv",
            encoding='utf-8-sig'
        )
        
        faltantes = [c for c in columnas_requeridas if c not in df_baysa.columns]
        
        if faltantes:
            print(f"❌ Columnas faltantes en BAYSA: {faltantes}")
            return False
        
        print(f"✅ BAYSA: {len(df_baysa.columns)} columnas")
        print(f"   Columnas: {', '.join(df_baysa.columns)}")
        
        df_jamar = pd.read_csv(
            "data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv",
            encoding='utf-8-sig'
        )
        
        faltantes_jamar = [c for c in columnas_requeridas if c not in df_jamar.columns]
        
        if faltantes_jamar:
            print(f"❌ Columnas faltantes en JAMAR: {faltantes_jamar}")
            return False
        
        print(f"✅ JAMAR: {len(df_jamar.columns)} columnas")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_backups_disponibles():
    """Test 4: Verificar backups disponibles."""
    print("\n" + "=" * 70)
    print("TEST 4: BACKUPS DISPONIBLES")
    print("=" * 70)
    
    try:
        # Backups BAYSA
        baysa_dir = Path("data/contratistas/BAYSA")
        backups_baysa = list(baysa_dir.glob("*backup*.csv"))
        print(f"BAYSA: {len(backups_baysa)} backups encontrados")
        
        if len(backups_baysa) < 3:
            print("⚠️ ADVERTENCIA: Menos de 3 backups BAYSA (recomendado: 5+)")
        
        # Backups JAMAR
        jamar_dir = Path("data/contratistas/JAMAR")
        backups_jamar = list(jamar_dir.glob("*backup*.csv"))
        print(f"JAMAR: {len(backups_jamar)} backups encontrados")
        
        if len(backups_jamar) < 3:
            print("⚠️ ADVERTENCIA: Menos de 3 backups JAMAR (recomendado: 5+)")
        
        print("\n✅ Backups disponibles")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_dashboards_generados():
    """Test 5: Verificar dashboards recientes."""
    print("\n" + "=" * 70)
    print("TEST 5: DASHBOARDS GENERADOS")
    print("=" * 70)
    
    try:
        output_dir = Path("output/dashboards")
        if not output_dir.exists():
            print("❌ Directorio output/dashboards no encontrado")
            return False
        
        dashboards = list(output_dir.glob("dashboard_*.html"))
        print(f"Total dashboards: {len(dashboards)}")
        
        # Buscar dashboards de hoy
        from datetime import datetime
        hoy = datetime.now().strftime("%Y%m%d")
        dashboards_hoy = [d for d in dashboards if hoy in d.name]
        
        print(f"Dashboards generados hoy: {len(dashboards_hoy)}")
        
        if len(dashboards_hoy) == 0:
            print("⚠️ ADVERTENCIA: No hay dashboards generados hoy")
        else:
            print("\nÚltimos dashboards:")
            for dash in sorted(dashboards_hoy, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                print(f"  • {dash.name} ({dash.stat().st_size:,} bytes)")
        
        print("\n✅ Dashboards verificados")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_sistema_backup():
    """Test 6: Verificar sistema de backup."""
    print("\n" + "=" * 70)
    print("TEST 6: SISTEMA DE BACKUP")
    print("=" * 70)
    
    try:
        from utils_backup import crear_backup_automatico, listar_backups_disponibles
        
        # Test con archivo de prueba
        test_file = Path("data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv")
        
        if not test_file.exists():
            print("❌ Archivo de prueba no encontrado")
            return False
        
        # Listar backups actuales
        backups_antes = listar_backups_disponibles(test_file)
        print(f"Backups antes: {len(backups_antes)}")
        
        # Crear nuevo backup
        backup_nuevo = crear_backup_automatico(test_file, mantener_ultimos=10)
        print(f"✅ Backup creado: {backup_nuevo.name}")
        
        # Verificar que se creó
        backups_despues = listar_backups_disponibles(test_file)
        print(f"Backups después: {len(backups_despues)}")
        
        if backup_nuevo.exists():
            print(f"✅ Backup verificado ({backup_nuevo.stat().st_size:,} bytes)")
        else:
            print("❌ Backup no se creó correctamente")
            return False
        
        print("\n✅ Sistema de backup funcionando")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Ejecutar todos los tests."""
    print("\n" + "=" * 70)
    print("🧪 TEST DE INTEGRIDAD COMPLETA DEL SISTEMA")
    print("=" * 70)
    print(f"Fecha: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tests = [
        ("Archivos Críticos", test_archivos_criticos),
        ("Conteos de Datos", test_conteos_datos),
        ("Estructura de Columnas", test_estructura_columnas),
        ("Backups Disponibles", test_backups_disponibles),
        ("Dashboards Generados", test_dashboards_generados),
        ("Sistema de Backup", test_sistema_backup),
    ]
    
    resultados = []
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"\n❌ ERROR en {nombre}: {e}")
            resultados.append((nombre, False))
    
    # Resumen
    print("\n" + "=" * 70)
    print("📋 RESUMEN DE TESTS")
    print("=" * 70)
    
    pasados = sum(1 for _, r in resultados if r)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        icono = "✅" if resultado else "❌"
        print(f"{icono} {nombre}")
    
    print(f"\n{'=' * 70}")
    if pasados == total:
        print(f"✅ TODOS LOS TESTS PASARON ({pasados}/{total})")
        print("=" * 70)
        return 0
    else:
        print(f"⚠️  ALGUNOS TESTS FALLARON ({pasados}/{total})")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
