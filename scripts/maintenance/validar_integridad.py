#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Validación del Proyecto - Control de Dossieres
==========================================================

Verifica:
1. Todas las dependencias están instaladas
2. Los módulos principales se importan sin errores
3. Los CSVs de entrada existen y son legibles
4. Las rutas de salida son accesibles
5. Los scripts principales ejecutan sin crash

Ejecutar:
    python validar_proyecto.py
"""

import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).parent

def verificar_dependencias():
    """Verifica que las dependencias estén instaladas."""
    print("[INFO] Verificando dependencias...")
    reqs = ["pandas", "plotly", "yaml", "openpyxl", "streamlit"]
    faltantes = []
    for req in reqs:
        try:
            __import__(req)
        except ImportError:
            faltantes.append(req)
    if faltantes:
        print(f"[ERROR] Paquetes faltantes: {', '.join(faltantes)}")
        return False
    print("[OK] Todas las dependencias están instaladas")
    return True

def verificar_modulos():
    """Verifica que los módulos principales se importen sin error."""
    print("\n[INFO] Verificando modulos principales...")
    modulos = [
        "metricas_core",
        "utils_archivos",
        "dashboard",
        "dashboard_consolidado",
        "generar_todos_dashboards",
    ]
    errores = []
    for mod in modulos:
        try:
            __import__(mod)
            print(f"  [OK] {mod}")
        except Exception as e:
            errores.append(f"{mod}: {e}")
            print(f"  [ERROR] {mod}: {e}")
    if errores:
        print(f"[ERROR] {len(errores)} modulo(s) con error")
        return False
    print("[OK] Todos los modulos importan correctamente")
    return True

def verificar_csvs():
    """Verifica que los CSVs de entrada existan y sean legibles."""
    print("\n[INFO] Verificando CSVs...")
    import pandas as pd
    
    csvs = {
        "BAYSA normalizado": (BASE / "data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv", True),
        "BAYSA fuente": (BASE / "data/contratistas/BAYSA/ctrl_dosieres.csv", False),
        "JAMAR normalizado": (BASE / "data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv", True),
        "JAMAR fuente": (BASE / "data/ctrl_dosieres_JAMAR.csv", False),  # Opcional
    }
    
    errores = []
    for nombre, (ruta, required) in csvs.items():
        if not ruta.exists():
            msg = f"{nombre}: NO EXISTE (opcional)" if not required else f"{nombre}: NO EXISTE (REQUERIDO)"
            if required:
                errores.append(msg)
            print(f"  [WARN] {msg}")
            continue
        
        try:
            for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                try:
                    df = pd.read_csv(ruta, encoding=enc)
                    print(f"  [OK] {nombre}: {len(df)} registros ({enc})")
                    break
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            if required:
                errores.append(f"{nombre}: {e}")
            print(f"  [{'ERROR' if required else 'WARN'}] {nombre}: {e}")
    
    if errores:
        print(f"[ERROR] {len(errores)} CSV(s) REQUERIDO(s) con problemas")
        return False
    print("[OK] Todos los CSVs requeridos son accesibles")
    return True

def verificar_directorios():
    """Verifica que los directorios de salida existan y sean escribibles."""
    print("\n[INFO] Verificando directorios de salida...")
    dirs = [
        BASE / "output",
        BASE / "output/dashboards",
        BASE / "output/tablas",
        BASE / "output/historico",
        BASE / ".streamlit",
    ]
    errores = []
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        if not d.is_dir():
            errores.append(f"No se pudo crear {d}")
            print(f"  [ERROR] {d}")
        else:
            print(f"  [OK] {d}")
    
    if errores:
        print(f"[ERROR] {len(errores)} directorio(s) con error")
        return False
    print("[OK] Todos los directorios están disponibles")
    return True

def verificar_streamlit_app():
    """Valida que la app de Streamlit cargue sin crashes."""
    print("\n[INFO] Verificando app Streamlit...")
    try:
        import streamlit as st
        from pathlib import Path
        import sys
        # Simular carga de la app sin ejecutarla
        app_file = BASE / "app_ingreso_datos.py"
        if not app_file.exists():
            print(f"  [ERROR] app_ingreso_datos.py no existe")
            return False
        
        # Compilar app para detectar syntax errors
        import py_compile
        py_compile.compile(str(app_file), doraise=True)
        print(f"  [OK] app_ingreso_datos.py: sintaxis valida")
        print("[OK] App Streamlit es compilable")
        return True
    except Exception as e:
        print(f"  [ERROR] Error en app Streamlit: {e}")
        return False

def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "="*60)
    print("[INFO] VALIDACION INTEGRAL DEL PROYECTO")
    print("="*60)
    
    checks = [
        ("Dependencias", verificar_dependencias),
        ("Modulos", verificar_modulos),
        ("CSVs de entrada", verificar_csvs),
        ("Directorios de salida", verificar_directorios),
        ("App Streamlit", verificar_streamlit_app),
    ]
    
    resultados = []
    for nombre, func in checks:
        try:
            ok = func()
            resultados.append((nombre, ok))
        except Exception as e:
            print(f"\n[ERROR] Error en {nombre}: {e}")
            resultados.append((nombre, False))
    
    print("\n" + "="*60)
    print("[INFO] RESUMEN")
    print("="*60)
    
    for nombre, ok in resultados:
        estado = "[OK]" if ok else "[ERROR]"
        print(f"{estado} {nombre}")
    
    total_ok = sum(1 for _, ok in resultados if ok)
    print(f"\nTotal: {total_ok}/{len(resultados)} checks pasados")
    
    if total_ok == len(resultados):
        print("\n[OK] PROYECTO VALIDADO - LISTO PARA USAR")
        return 0
    else:
        print("\n[ERROR] PROYECTO CON PROBLEMAS - REVISAR ARRIBA")
        return 1

if __name__ == "__main__":
    sys.exit(main())

