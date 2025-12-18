#!/usr/bin/env python3
"""
Generador de Dashboards para Múltiples Contratistas
====================================================

Genera dashboards para JAMAR y BAYSA en secuencia.

Uso:
    python generar_todos_dashboards.py
"""

import subprocess
import sys
import yaml
from pathlib import Path

def actualizar_config(contratista: str, titulo: str, archivo_entrada: str):
    """Actualiza config.yaml para una contratista específica."""
    
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Actualizar rutas e información
    config['paths']['input_file'] = archivo_entrada
    config['contratista'] = {
        'nombre': contratista,
        'titulo_dashboard': titulo
    }
    
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"  ✏️  config.yaml actualizado para {contratista}")

def generar_dashboard_contratista(contratista: str, titulo: str, archivo_entrada: str, config_original: str):
    """Genera dashboard para una contratista."""
    
    print(f"\n{'='*60}")
    print(f"📊 Generando dashboard para: {contratista}")
    print(f"{'='*60}")
    
    # Validar que el archivo existe
    if not Path(archivo_entrada).exists():
        print(f"❌ Archivo no encontrado: {archivo_entrada}")
        return False
    
    try:
        # Actualizar configuración
        actualizar_config(contratista, titulo, archivo_entrada)
        
        # Ejecutar dashboard.py con entrada de semana
        proceso = subprocess.Popen(
            ['python', 'dashboard.py', '--no-cache'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        stdout, stderr = proceso.communicate(input='S181\n')
        
        if proceso.returncode != 0:
            print(f"❌ Error generando dashboard para {contratista}")
            if stderr:
                print(stderr)
            return False
        
        print(f"✅ Dashboard generado para {contratista}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Restaurar configuración original después de cada generación
        with open('config.yaml', 'w', encoding='utf-8') as f:
            f.write(config_original)

def main():
    """Genera dashboards para todas las contratistas."""
    
    print("\n" + "="*60)
    print("🚀 GENERADOR DE DASHBOARDS - MÚLTIPLES CONTRATISTAS")
    print("="*60)
    
    # Guardar configuración original
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config_original = f.read()
    
    contratistas = [
        ('JAMAR', 'DASHBOARD DE CONTROL - DOSSIERES JAMAR', 'data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv'),
        ('BAYSA', 'DASHBOARD DE CONTROL - DOSSIERES BAYSA', 'data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv'),
    ]
    
    resultados = []
    
    for nombre, titulo, archivo in contratistas:
        exito = generar_dashboard_contratista(nombre, titulo, archivo, config_original)
        resultados.append((nombre, exito))
    
    # Resumen
    print(f"\n{'='*60}")
    print("📋 RESUMEN")
    print(f"{'='*60}")
    
    for nombre, exito in resultados:
        estado = "✅ OK" if exito else "❌ ERROR"
        print(f"  {estado}  {nombre}")
    
    # Verificar que todos fueron exitosos
    todos_exitosos = all(exito for _, exito in resultados)
    
    if todos_exitosos:
        # Generar dashboard consolidado
        print(f"\n{'='*60}")
        print("📊 Generando dashboard consolidado...")
        print(f"{'='*60}")
        
        try:
            resultado_consolidado = subprocess.run(
                ['python', 'dashboard_consolidado.py'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if resultado_consolidado.returncode == 0:
                print("✅ Dashboard consolidado generado")
                consolidado_ok = True
            else:
                print("❌ Error generando dashboard consolidado")
                consolidado_ok = False
        except Exception as e:
            print(f"❌ Error: {e}")
            consolidado_ok = False
        
        print(f"\n{'='*60}")
        print("✅ TODOS LOS DASHBOARDS GENERADOS EXITOSAMENTE")
        print(f"{'='*60}")
        print("\nArchivos generados:")
        print("  • output/dashboard_JAMAR_[timestamp].html")
        print("  • output/dashboard_BAYSA_[timestamp].html")
        if consolidado_ok:
            print("  • output/dashboard_consolidado_[timestamp].html")
    else:
        print(f"\n❌ Algunos dashboards fallaron")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
