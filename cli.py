#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI Principal - Control de Dossieres
=====================================

Interfaz de línea de comandos para todas las operaciones principales del proyecto.

Uso:
    python cli.py run              # Abrir app Streamlit
    python cli.py generate S186    # Generar dashboards para semana S186
    python cli.py validate         # Validar integridad del proyecto
    python cli.py status           # Ver estado rápido
    python cli.py --help           # Ver todas las opciones
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Configurar paths
PROJECT_ROOT = Path(__file__).parent
APP_DIR = PROJECT_ROOT / "app"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
MAINTENANCE_DIR = SCRIPTS_DIR / "maintenance"

# Colores para terminal (Windows compatible)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'


def print_header(text: str):
    """Imprime encabezado bonito."""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_info(text: str):
    """Imprime mensaje informativo."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def print_warning(text: str):
    """Imprime advertencia."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def cmd_run(args):
    """Ejecuta la app Streamlit."""
    print_header("🌐 ABRIENDO APP - CONTROL DE DOSSIERES")
    
    app_file = APP_DIR / "streamlit_app.py"
    
    if not app_file.exists():
        print_error(f"Archivo no encontrado: {app_file}")
        print_info("Intenta ejecutar 'python cli.py validate' para diagnosticar")
        sys.exit(1)
    
    print_info(f"Archivo: {app_file}")
    print_info("Abriendo en navegador automáticamente...")
    print_info("Presiona CTRL+C para detener\n")
    
    try:
        # Usar subprocess para ejecutar streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", str(app_file)]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print_info("\nApp detenida.")
    except Exception as e:
        print_error(f"Error al ejecutar app: {e}")
        sys.exit(1)


def cmd_generate(args):
    """Genera dashboards para una semana específica."""
    if not args.semana:
        print_error("Debes proporcionar la SEMANA (ej: S186)")
        print_info("Uso: python cli.py generate S186")
        sys.exit(1)
    
    semana = args.semana.upper()
    
    # Validar formato
    import re
    if not re.match(r"^S\d{1,4}$", semana):
        print_error(f"Formato de semana inválido: {semana}")
        print_info("Debe ser S### (ej: S186, S1, S1020)")
        sys.exit(1)
    
    print_header(f"📊 GENERANDO DASHBOARDS PARA {semana}")
    
    # Ejecutar generador de dashboards
    generar_script = SCRIPTS_DIR / "cli_generar.py"
    
    if not generar_script.exists():
        # Fallback: ejecutar generar_todos_dashboards.py si aún existe
        print_warning("Usando generador legacy (generar_todos_dashboards.py)")
        generar_script = PROJECT_ROOT / "generar_todos_dashboards.py"
    
    if not generar_script.exists():
        print_error(f"Generador no encontrado: {generar_script}")
        sys.exit(1)
    
    try:
        # Pasar la semana como argumento
        cmd = [sys.executable, str(generar_script), semana]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["SEMANA_CORTE"] = semana
        
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
        
        if result.returncode == 0:
            print_success(f"Dashboards generados para {semana}")
            print_info(f"Busca los archivos en: {PROJECT_ROOT}/output/dashboards/")
            print_info(f"Exportados (histórico) en: {PROJECT_ROOT}/output/exports/")
        else:
            print_error(f"Error generando dashboards (código {result.returncode})")
            sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


def cmd_validate(args):
    """Valida la integridad del proyecto."""
    print_header("✅ VALIDANDO INTEGRIDAD DEL PROYECTO")
    
    validar_script = MAINTENANCE_DIR / "validar_integridad.py"
    
    if not validar_script.exists():
        # Fallback a validar_proyecto.py
        print_warning("Usando validador legacy (validar_proyecto.py)")
        validar_script = PROJECT_ROOT / "validar_proyecto.py"
    
    if not validar_script.exists():
        print_error(f"Validador no encontrado: {validar_script}")
        sys.exit(1)
    
    try:
        cmd = [sys.executable, str(validar_script)]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


def cmd_status(args):
    """Muestra estado rápido del proyecto."""
    print_header("📊 ESTADO DEL PROYECTO")
    
    # Verificar carpetas críticas
    print_info("Verificando estructura...")
    
    checks = {
        "App": APP_DIR / "streamlit_app.py",
        "Core (Métricas)": PROJECT_ROOT / "core" / "metricas.py",
        "Generators": SCRIPTS_DIR / "cli_generar.py",
        "Data/BAYSA": PROJECT_ROOT / "data" / "contratistas" / "BAYSA" / "ctrl_dosieres_BAYSA_normalizado.csv",
        "Data/JAMAR": PROJECT_ROOT / "data" / "contratistas" / "JAMAR" / "ctrl_dosieres_JAMAR_normalizado.csv",
        "Output": PROJECT_ROOT / "output",
        "Config": PROJECT_ROOT / "config.yaml",
    }
    
    issues = []
    for name, path in checks.items():
        if path.exists():
            print_success(f"{name}")
        else:
            print_warning(f"{name} (NO ENCONTRADO)")
            issues.append(name)
    
    # Contar CSV
    print_info("\nDatos:")
    baysa_csv = PROJECT_ROOT / "data" / "contratistas" / "BAYSA" / "ctrl_dosieres_BAYSA_normalizado.csv"
    jamar_csv = PROJECT_ROOT / "data" / "contratistas" / "JAMAR" / "ctrl_dosieres_JAMAR_normalizado.csv"
    
    try:
        import pandas as pd
        if baysa_csv.exists():
            df_baysa = pd.read_csv(baysa_csv, encoding='latin-1')
            print(f"  • BAYSA: {len(df_baysa)} registros")
        
        if jamar_csv.exists():
            df_jamar = pd.read_csv(jamar_csv, encoding='utf-8-sig')
            print(f"  • JAMAR: {len(df_jamar)} registros")
    except Exception as e:
        print_warning(f"  No se pudieron contar registros: {e}")
    
    # Resumen
    print_info("\nDashboards generados:")
    dashboards_dir = PROJECT_ROOT / "output" / "dashboards"
    if dashboards_dir.exists():
        dashboards = list(dashboards_dir.glob("*.html"))
        print(f"  • {len(dashboards)} dashboards en output/dashboards/")
    
    print_info("\nExportes (histórico de cortes):")
    exports_dir = PROJECT_ROOT / "output" / "exports"
    if exports_dir.exists():
        exportes = list(exports_dir.glob("*.json")) + list(exports_dir.glob("*.html"))
        print(f"  • {len(exportes)} exportes en output/exports/")
    
    # Conclusión
    if issues:
        print_warning(f"\nAlgunos archivos no encontrados. Ejecuta: python cli.py validate")
    else:
        print_success("\n¡Proyecto OK! Puedes ejecutar: python cli.py run")


def cmd_backup(args):
    """Crea un respaldo del proyecto."""
    print_header("💾 CREANDO RESPALDO")
    
    backup_script = MAINTENANCE_DIR / "backup_helper.py"
    
    if not backup_script.exists():
        print_error(f"Script de respaldo no encontrado: {backup_script}")
        sys.exit(1)
    
    try:
        cmd = [sys.executable, str(backup_script)]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="CLI - Control de Dossieres",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python cli.py run                  # Abrir app (RECOMENDADO)
  python cli.py generate S186        # Generar dashboards para S186
  python cli.py validate             # Validar proyecto
  python cli.py status               # Ver estado rápido
  python cli.py backup               # Crear respaldo
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")
    
    # Comando: run
    parser_run = subparsers.add_parser("run", help="Abre la app Streamlit")
    parser_run.set_defaults(func=cmd_run)
    
    # Comando: generate
    parser_gen = subparsers.add_parser("generate", help="Genera dashboards para una semana")
    parser_gen.add_argument("semana", nargs="?", help="Semana (ej: S186)")
    parser_gen.set_defaults(func=cmd_generate)
    
    # Comando: validate
    parser_val = subparsers.add_parser("validate", help="Valida integridad del proyecto")
    parser_val.set_defaults(func=cmd_validate)
    
    # Comando: status
    parser_st = subparsers.add_parser("status", help="Muestra estado rápido")
    parser_st.set_defaults(func=cmd_status)
    
    # Comando: backup
    parser_bak = subparsers.add_parser("backup", help="Crea respaldo")
    parser_bak.set_defaults(func=cmd_backup)
    
    args = parser.parse_args()
    
    # Si no hay comando, mostrar ayuda
    if not args.command:
        print_header("🎯 CONTROL DE DOSSIERES - CLI")
        print("\nUso rápido (RECOMENDADO):")
        print("  python cli.py run          # Abrir app\n")
        parser.print_help()
        sys.exit(0)
    
    # Ejecutar comando
    args.func(args)


if __name__ == "__main__":
    main()
