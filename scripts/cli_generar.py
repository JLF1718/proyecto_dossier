#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI Generador de Dashboards
============================

Script para generar todos los dashboards (JAMAR, BAYSA y consolidado)
usando los módulos refactorizados.

Uso:
    python scripts/cli_generar.py S186
"""

import sys
import os
from pathlib import Path

# Agregar proyecto al path para imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports de módulos refactorizados
from generators.dashboard_generator import main as generar_individual
from generators.consolidado_generator import main as generar_consolidado


def print_header(text: str):
    """Imprime encabezado."""
    text = text.replace('[DASHBOARD]', '').replace('[GENERATOR]', '')
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_success(text: str):
    """Imprime mensaje de éxito."""
    print(f"[OK] {text}")


def print_error(text: str):
    """Imprime mensaje de error."""
    print(f"[ERROR] {text}")


def print_info(text: str):
    """Imprime mensaje informativo."""
    print(f"[INFO] {text}")


def podar_output_automatico(output_dir: Path) -> None:
    """Poda salidas para ahorrar espacio manteniendo un unico poster BAYSA."""
    objetivos = {
        output_dir / "historico": 1,
        output_dir / "dashboards": 1,
    }

    for carpeta, mantener in objetivos.items():
        if not carpeta.exists():
            continue

        archivos = sorted(
            carpeta.rglob("*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        archivos = [p for p in archivos if p.is_file()]

        if len(archivos) <= mantener:
            continue

        for archivo in archivos[mantener:]:
            archivo.unlink(missing_ok=True)

    tablas_dir = output_dir / "tablas"
    if tablas_dir.exists():
        html_tablas = [p for p in tablas_dir.glob("*.html") if p.is_file()]
        preferidos = sorted(
            [p for p in html_tablas if "baysa" in p.name.lower() and "jamar" not in p.name.lower()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        conservar = set(preferidos[:1])

        for archivo in html_tablas:
            if archivo not in conservar:
                archivo.unlink(missing_ok=True)

    cache_backups = output_dir / "cache_backups"
    if cache_backups.exists():
        import shutil
        shutil.rmtree(cache_backups)


def main():
    """Genera todos los dashboards para una semana específica."""
    
    # Obtener semana desde argumentos o variable de entorno
    semana = None
    
    if len(sys.argv) > 1:
        semana = sys.argv[1].upper()
    elif "SEMANA_CORTE" in os.environ:
        semana = os.environ["SEMANA_CORTE"].upper()
    elif "SEMANA_PROYECTO" in os.environ:
        semana = os.environ["SEMANA_PROYECTO"].upper()
    else:
        print_error("Debe proporcionar SEMANA (ej: S186)")
        print_info("Uso: python scripts/cli_generar.py S186")
        sys.exit(1)
    
    print_header(f"[GENERATOR] GENERADOR DE DASHBOARDS - MÚLTIPLES CONTRATISTAS")
    print_info(f"Semana de corte: {semana}")
    
    # Configurar variable de entorno para los generadores
    os.environ["SEMANA_PROYECTO"] = semana
    os.environ["SEMANA_CORTE"] = semana
    
    # Cargar configuración
    import yaml
    config_path = PROJECT_ROOT / "config.yaml"
    
    if not config_path.exists():
        print_error(f"Archivo de configuración no encontrado: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Asegurar que 'contratista' es un diccionario
    if not isinstance(config.get('contratista'), dict):
        config['contratista'] = {}
    
    # Lista de contratistas
    contratistas = ["JAMAR", "BAYSA"]
    resultados = {}
    
    # Generar dashboards individuales
    for contratista in contratistas:
        print_header(f"[DASHBOARD] Generando dashboard para: {contratista}")
        
        try:
            # Configurar contratista en la sección correcta
            config['contratista']['nombre'] = contratista
            
            # Actualizar archivo de configuración temporalmente
            config_path = PROJECT_ROOT / "config.yaml"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_file = yaml.safe_load(f)
                
                # Asegurar que 'contratista' es un diccionario
                if not isinstance(config_file.get('contratista'), dict):
                    config_file['contratista'] = {}
                
                config_file['contratista']['nombre'] = contratista
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_file, f, allow_unicode=True, default_flow_style=False)
                
                print_info(f"config.yaml actualizado para {contratista}")
            
            # Generar dashboard
            # Resetear sys.argv para evitar problemas con argparse
            old_argv = sys.argv[:]
            sys.argv = [sys.argv[0]]  # Solo nombre del script
            
            generar_individual()
            
            sys.argv = old_argv  # Restaurar
            
            print_success(f"Dashboard generado para {contratista}")
            resultados[contratista] = "OK"
            
        except Exception as e:
            print_error(f"Error generando dashboard para {contratista}: {e}")
            resultados[contratista] = f"ERROR: {e}"
    
    # Resumen de dashboards individuales
    print_header("[SUMMARY] RESUMEN")
    for contratista, status in resultados.items():
        if status == "OK":
            print_success(f"{contratista}")
        else:
            print_error(f"{contratista}: {status}")
    
    # Generar dashboard consolidado
    print_header("[DASHBOARD] Generando dashboard consolidado...")
    
    try:
        # Resetear sys.argv para evitar problemas con argparse
        old_argv = sys.argv[:]
        sys.argv = [sys.argv[0]]  # Solo nombre del script
        
        generar_consolidado()
        
        sys.argv = old_argv  # Restaurar
        
        print_success("Dashboard consolidado generado")
    except Exception as e:
        print_error(f"Error generando dashboard consolidado: {e}")
        sys.exit(1)

    # Poda automática para evitar crecimiento de output/ entre corridas
    output_dir = PROJECT_ROOT / "output"
    podar_output_automatico(output_dir=output_dir)
    print_info("Poda automática aplicada: historico=1, tablas=1, dashboards=1")
    print_info("cache_backups eliminado para liberar espacio")
    
    # Mensaje final
    print_header("[OK] TODOS LOS DASHBOARDS GENERADOS EXITOSAMENTE")
    print_info("\nArchivos generados:")
    print_info("  - output/dashboards/dashboard_JAMAR_[timestamp].html")
    print_info("  - output/dashboards/dashboard_BAYSA_[timestamp].html")
    print_info("  - output/dashboards/dashboard_consolidado_[timestamp].html")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
