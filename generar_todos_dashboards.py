#!/usr/bin/env python3
"""
Generador de Dashboards para Múltiples Contratistas
====================================================

Genera dashboards para JAMAR y BAYSA en secuencia.

Uso:
    python generar_todos_dashboards.py
"""

import os
import re
import subprocess
import sys
import yaml
from pathlib import Path


def actualizar_config(contratista: str, titulo: str, archivo_entrada: str) -> None:
    """Actualiza config.yaml para una contratista específica."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    config.setdefault("paths", {})
    config["paths"]["input_file"] = archivo_entrada
    config["contratista"] = {
        "nombre": contratista,
        "titulo_dashboard": titulo
    }

    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

    print(f"  ✏️  config.yaml actualizado para {contratista}")


def pedir_semana() -> str:
    """
    Solicita la semana de corte al usuario en formato S###.
    Ejemplos válidos: S1, S12, S181, S1020
    """
    while True:
        s = input("Semana de corte (formato S###, ej. S181): ").strip().upper()
        if re.fullmatch(r"S\d{1,4}", s):
            return s
        print("❌ Formato inválido. Usa, por ejemplo: S181")


def generar_dashboard_contratista(
    contratista: str,
    titulo: str,
    archivo_entrada: str,
    config_original: str,
    semana_corte: str
) -> bool:
    """Genera dashboard para una contratista."""

    print(f"\n{'='*60}")
    print(f"📊 Generando dashboard para: {contratista}")
    print(f"{'='*60}")

    if not Path(archivo_entrada).exists():
        print(f"❌ Archivo no encontrado: {archivo_entrada}")
        return False

    try:
        actualizar_config(contratista, titulo, archivo_entrada)

        # Forzar UTF-8 en el proceso hijo (dashboard.py)
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
        env["SEMANA_CORTE"] = semana_corte  # Pasar semana como variable de entorno

        # Ejecutar con subprocess.run que es más simple y robusto
        resultado = subprocess.run(
            [sys.executable, "-X", "utf8", "dashboard.py", "--no-cache"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        if resultado.returncode != 0:
            print(f"❌ Error generando dashboard para {contratista}")
            if resultado.stderr:
                # Mostrar solo las líneas de error relevantes, no warnings
                for line in resultado.stderr.split('\n'):
                    if 'Error' in line or 'Traceback' in line or 'File' in line:
                        print(line)
            return False

        print(f"✅ Dashboard generado para {contratista}")
        return True

        print(f"✅ Dashboard generado para {contratista}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    finally:
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write(config_original)


def main() -> int:
    print("\n" + "=" * 60)
    print("🚀 GENERADOR DE DASHBOARDS - MÚLTIPLES CONTRATISTAS")
    print("=" * 60)

    # Semana de corte (desde argumento, variable de entorno o input)
    if len(sys.argv) > 1:
        semana_corte = sys.argv[1].strip().upper()
        if not re.fullmatch(r"S\d{1,4}", semana_corte):
            print(f"❌ Formato inválido: {sys.argv[1]}. Usa, por ejemplo: S186")
            return 1
        print(f"📌 Semana de corte (desde argumento): {semana_corte}")
    else:
        semana_corte = pedir_semana()

    with open("config.yaml", "r", encoding="utf-8") as f:
        config_original = f.read()

    contratistas = [
        ("JAMAR", "DASHBOARD DE CONTROL - DOSSIERES JAMAR",
         "data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv"),
        ("BAYSA", "DASHBOARD DE CONTROL - DOSSIERES BAYSA",
         "data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv"),
    ]

    resultados = []
    for nombre, titulo, archivo in contratistas:
        exito = generar_dashboard_contratista(nombre, titulo, archivo, config_original, semana_corte)
        resultados.append((nombre, exito))

    print(f"\n{'='*60}")
    print("📋 RESUMEN")
    print(f"{'='*60}")

    for nombre, exito in resultados:
        estado = "✅ OK" if exito else "❌ ERROR"
        print(f"  {estado}  {nombre}")

    if not all(exito for _, exito in resultados):
        print("\n❌ Algunos dashboards fallaron")
        return 1

    # Consolidado
    print(f"\n{'='*60}")
    print("📊 Generando dashboard consolidado...")
    print(f"{'='*60}")

    consolidado_ok = False
    try:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["SEMANA_CORTE"] = semana_corte  # Pasar la semana al consolidado

        resultado_consolidado = subprocess.run(
            [sys.executable, "-X", "utf8", "dashboard_consolidado.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        if resultado_consolidado.returncode == 0:
            print("✅ Dashboard consolidado generado")
            consolidado_ok = True
        else:
            print("❌ Error generando dashboard consolidado")
            if resultado_consolidado.stderr:
                print(resultado_consolidado.stderr)

    except Exception as e:
        print(f"❌ Error: {e}")

    print(f"\n{'='*60}")
    print("✅ TODOS LOS DASHBOARDS GENERADOS EXITOSAMENTE")
    print(f"{'='*60}")
    print("\nArchivos generados:")
    print("  • output/dashboard_JAMAR_[timestamp].html")
    print("  • output/dashboard_BAYSA_[timestamp].html")
    if consolidado_ok:
        print("  • output/dashboard_consolidado_[timestamp].html")

    return 0


if __name__ == "__main__":
    sys.exit(main())
