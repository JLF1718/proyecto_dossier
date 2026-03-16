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
    python cli.py smoke-validate   # Ejecutar smoke test de release
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
    # Remover emojis para compatibilidad con Windows
    text = text.replace('📊', '[DASHBOARD]').replace('🌐', '[WEB]').replace('✅', '[OK]')
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")


def print_error(text: str):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")


def print_info(text: str):
    """Imprime mensaje informativo."""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")


def print_warning(text: str):
    """Imprime advertencia."""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")


def cmd_run(args):
    """Ejecuta la app Streamlit."""
    print_header("[WEB] ABRIENDO APP - CONTROL DE DOSSIERES")
    
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


def cmd_run_web(args):
    """Ejecuta la app web FastAPI (Fase 1)."""
    print_header("[WEB] ABRIENDO APP WEB PROFESIONAL - FASTAPI")

    app_file = PROJECT_ROOT / "webapp" / "main.py"

    if not app_file.exists():
        print_error(f"Archivo no encontrado: {app_file}")
        print_info("Verifica que exista la carpeta webapp/")
        sys.exit(1)

    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = os.getenv("WEB_PORT", "8000")

    print_info(f"Archivo: {app_file}")
    print_info(f"URL local: http://localhost:{port}")
    print_info("Presiona CTRL+C para detener\n")

    try:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "webapp.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        print_info("\nApp web detenida.")
    except Exception as e:
        print_error(f"Error al ejecutar app web: {e}")
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
    
    print_header(f"[DASHBOARD] GENERANDO DASHBOARDS PARA {semana}")
    
    # Ejecutar generador de dashboards
    generar_script = SCRIPTS_DIR / "cli_generar.py"
    usar_legacy = False

    if not generar_script.exists():
        print_warning("Usando generador legacy (generar_todos_dashboards.py)")
        usar_legacy = True
    
    try:
        # Pasar la semana como argumento
        cmd = [sys.executable, "-m", "scripts.cli_generar", semana]
        if usar_legacy:
            cmd = [sys.executable, str(PROJECT_ROOT / "generar_todos_dashboards.py"), semana]
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
    print_header("[OK] VALIDANDO INTEGRIDAD DEL PROYECTO")
    
    validar_script = MAINTENANCE_DIR / "validar_integridad.py"
    usar_legacy = not validar_script.exists()

    if usar_legacy:
        print_warning("Usando validador legacy (validar_proyecto.py)")

    if usar_legacy and not (PROJECT_ROOT / "validar_proyecto.py").exists():
        print_error(f"Validador no encontrado: {PROJECT_ROOT / 'validar_proyecto.py'}")
        sys.exit(1)
    
    try:
        cmd = [sys.executable, "-m", "scripts.maintenance.validar_integridad"]
        if usar_legacy:
            cmd = [sys.executable, str(PROJECT_ROOT / "validar_proyecto.py")]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


def cmd_status(args):
    """Muestra estado rápido del proyecto."""
    print_header("[STATUS] ESTADO DEL PROYECTO")
    
    # Verificar carpetas críticas
    print_info("Verificando estructura...")
    
    checks = {
        "App": APP_DIR / "streamlit_app.py",
        "Dashboard": PROJECT_ROOT / "dashboard" / "app.py",
        "Backend": PROJECT_ROOT / "backend" / "main.py",
        "Core (Métricas)": PROJECT_ROOT / "core" / "metricas.py",
        "Generators": PROJECT_ROOT / "generators" / "dashboard_generator.py",
        "Data/BAYSA (processed)": PROJECT_ROOT / "data" / "processed" / "baysa_dossiers_clean.csv",
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
    baysa_csv = PROJECT_ROOT / "data" / "processed" / "baysa_dossiers_clean.csv"
    
    try:
        import pandas as pd
        if baysa_csv.exists():
            df_baysa = pd.read_csv(baysa_csv)
            print(f"  • BAYSA: {len(df_baysa)} registros")
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
        cmd = [sys.executable, "-m", "scripts.maintenance.backup_helper"]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


def cmd_prune(args):
    """Ejecuta poda segura para reducir peso en disco."""
    print_header("[MAINTENANCE] PODA SEGURA DE ALMACENAMIENTO")

    try:
        cmd = [sys.executable, "-m", "scripts.maintenance.prune_storage"]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


def cmd_snapshot_build(args):
    """Genera o actualiza un snapshot semanal persistente."""
    print_header("[SNAPSHOT] GENERANDO SNAPSHOT SEMANAL")
    cmd = [sys.executable, "-m", "scripts.build_weekly_snapshot"]
    if args.week is not None:
        cmd.extend(["--week", str(args.week)])
    if args.force:
        cmd.append("--force")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


def cmd_audit_kpis(args):
    """Imprime la auditoria de peso y KPI vigente."""
    print_header("[AUDIT] AUDITORIA DE PESOS Y KPI")
    subprocess.run([sys.executable, "-m", "scripts.audit_kpis"], cwd=str(PROJECT_ROOT), check=True)


def cmd_inspect_management(args):
    """Inspecciona payloads de gestion y reporte ejecutivo."""
    print_header("[PAYLOAD] INSPECCION DE GESTION")
    cmd = [sys.executable, "-m", "scripts.inspect_management_payload", "--payload", args.payload, "--lang", args.lang]
    if args.week is not None:
        cmd.extend(["--week", str(args.week)])
    if args.comparison_week is not None:
        cmd.extend(["--comparison-week", str(args.comparison_week)])
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


def cmd_smoke_validate(args):
    """Ejecuta smoke test compacto de release (payloads + salud opcional)."""
    print_header("[SMOKE] VALIDACION COMPACTA DE RELEASE")
    cmd = [sys.executable, "-m", "scripts.smoke_validate_release"]
    if args.api_base:
        cmd.extend(["--api-base", args.api_base])
    if args.dash_url:
        cmd.extend(["--dash-url", args.dash_url])
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="CLI - Control de Dossieres",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python cli.py run                  # Abrir app (RECOMENDADO)
    python cli.py run-web              # Abrir app web profesional
  python cli.py generate S186        # Generar dashboards para S186
  python cli.py validate             # Validar proyecto
  python cli.py status               # Ver estado rápido
        python cli.py smoke-validate      # Smoke de release
    python cli.py backup               # Crear respaldo
    python cli.py prune                # Podar caches, historicos y backups antiguos
    python cli.py snapshot-build       # Persistir snapshot semanal
    python cli.py audit-kpis           # Auditar KPIs y pesos actuales
    python cli.py inspect-management   # Ver payloads de gestion / reporte
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")
    
    # Comando: run
    parser_run = subparsers.add_parser("run", help="Abre la app Streamlit")
    parser_run.set_defaults(func=cmd_run)

    # Comando: run-web
    parser_run_web = subparsers.add_parser("run-web", help="Abre app web profesional (FastAPI)")
    parser_run_web.set_defaults(func=cmd_run_web)
    
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

    # Comando: prune
    parser_prune = subparsers.add_parser("prune", help="Poda segura para reducir peso en disco")
    parser_prune.set_defaults(func=cmd_prune)

    # Comando: snapshot-build
    parser_snapshot = subparsers.add_parser("snapshot-build", help="Genera o actualiza un snapshot semanal persistente")
    parser_snapshot.add_argument("--week", type=int, default=None, help="Semana de analisis a persistir")
    parser_snapshot.add_argument("--force", action="store_true", help="Reemplaza el snapshot si ya existe")
    parser_snapshot.set_defaults(func=cmd_snapshot_build)

    # Comando: audit-kpis
    parser_audit = subparsers.add_parser("audit-kpis", help="Imprime la auditoria de KPIs y pesos")
    parser_audit.set_defaults(func=cmd_audit_kpis)

    # Comando: inspect-management
    parser_inspect = subparsers.add_parser("inspect-management", help="Inspecciona payloads de gestion y reporte")
    parser_inspect.add_argument("--payload", default="weekly", choices=["weekly", "historical", "executive"], help="Payload a mostrar")
    parser_inspect.add_argument("--week", type=int, default=None, help="Semana de analisis")
    parser_inspect.add_argument("--comparison-week", type=int, default=None, help="Semana historica a comparar")
    parser_inspect.add_argument("--lang", default="en", choices=["en", "es"], help="Idioma para payload ejecutivo")
    parser_inspect.set_defaults(func=cmd_inspect_management)

    # Comando: smoke-validate
    parser_smoke = subparsers.add_parser("smoke-validate", help="Ejecuta smoke test compacto de release")
    parser_smoke.add_argument("--api-base", default=None, help="Base URL backend (ej: http://127.0.0.1:8000)")
    parser_smoke.add_argument("--dash-url", default=None, help="URL dashboard (ej: http://127.0.0.1:8050)")
    parser_smoke.set_defaults(func=cmd_smoke_validate)
    
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
