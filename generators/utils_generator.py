#!/usr/bin/env python3
"""
Utilidades Comunes para Manejo de Archivos
===========================================

Módulo compartido para organización consistente de archivos
generados por todos los scripts del proyecto.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd

# ========== CONFIGURACIÓN PLOTLY ==========
# Configuración estándar con botones de descarga habilitados
PLOTLY_CONFIG_INTERACTIVE = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToAdd': ['toImage'],
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'grafico',
        'height': 1080,
        'width': 1920,
        'scale': 2
    }
}

PLOTLY_CONFIG_STATIC = {
    'displayModeBar': False,
    'displaylogo': False
}


def leer_csv_robusto(ruta: Path) -> pd.DataFrame:
    """Lee CSV con fallback automático de encodings."""
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
        try:
            return pd.read_csv(ruta, encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    return pd.DataFrame()


def obtener_estructura_directorios(output_dir: Path) -> dict:
    """Retorna la estructura estandarizada de directorios."""
    return {
        'output': output_dir,
        'dashboards': output_dir / 'dashboards',
        'tablas': output_dir / 'tablas',
        'historico': output_dir / 'historico',
        'data_historico': Path('data') / 'historico',
        'data_historico_contratista': Path('data') / 'historico',
        'data_historico_consolidado': Path('data') / 'historico' / 'consolidado'
    }


def crear_directorios(dirs: dict) -> None:
    """Crea todos los directorios necesarios."""
    for nombre, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)


def solicitar_semana(tipo: str = "proyecto") -> str:
    """
    Solicita la semana al usuario o usa variable de entorno.
    
    Args:
        tipo: 'proyecto' o 'corte' para personalizar mensaje
    
    Returns:
        Semana en formato S### (ej: S183)
    """
    var_env = 'SEMANA_PROYECTO' if tipo == 'proyecto' else 'SEMANA_CORTE'
    semana_env = os.getenv(var_env)
    
    if semana_env:
        semana = semana_env.strip().upper()
        if semana.startswith('S') and semana[1:].isdigit():
            print(f"[INFO] Semana desde variable de entorno: {semana}")
            return semana
    
    prompt = f"[INPUT] Ingresa el número de semana (ej: S183): "
    return input(prompt).strip().upper()


def guardar_archivos_individuales(
    fig_dashboard,
    contratista: str,
    timestamp: str,
    semana: str,
    dirs: dict,
    config: dict,
    df_data: Optional[pd.DataFrame] = None
) -> Tuple[Path, Path]:
    """
    Guarda dashboard individual y sus archivos asociados en estructura organizada.
    
    Returns:
        Tupla con (archivo_actual, archivo_historico)
    """
    # Guardar en dashboards/ (archivo actual)
    ts_dash = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dashboard_actual = dirs['dashboards'] / f"dashboard_{contratista}_{ts_dash}.html"
    fig_dashboard.write_html(
        str(dashboard_actual),
        config=PLOTLY_CONFIG_INTERACTIVE
    )

    # Crear carpeta de histórico para la semana
    fecha_str = datetime.now().strftime("%Y%m%d")
    semana_dir = dirs['historico'] / contratista / f"{semana}_{fecha_str}"
    semana_dir.mkdir(parents=True, exist_ok=True)
    graficos_dir = semana_dir / "graficos"
    graficos_dir.mkdir(parents=True, exist_ok=True)

    # Guardar en histórico
    ts_hist = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dashboard_historico = semana_dir / f"dashboard_{contratista}_{semana}_{ts_hist}.html"
    fig_dashboard.write_html(
        str(dashboard_historico),
        config=PLOTLY_CONFIG_INTERACTIVE
    )
    
    # Guardar datos Excel si se proporcionan
    if df_data is not None:
        data_hist_dir = dirs['data_historico_contratista'] / contratista
        data_hist_dir.mkdir(parents=True, exist_ok=True)
        excel_historico = data_hist_dir / f"ctrl_dosieres_{semana}.xlsx"
        df_data.to_excel(str(excel_historico), sheet_name="ctrl_dosieres", index=False, engine='openpyxl')
    
    return dashboard_actual, dashboard_historico


def guardar_archivos_consolidados(
    fig_dashboard,
    fig_tabla_resumen,
    tablas_individuales: dict,
    timestamp: str,
    semana: str,
    dirs: dict,
    df_consolidado: pd.DataFrame
) -> dict:
    """
    Guarda dashboard consolidado, tablas y sus archivos asociados.
    
    IMPORTANTE: Los archivos en output/exports/ son históricos por SEMANA DE CORTE.
    No se eliminan, se acumulan como registro de cada corte semanal.
    
    Returns:
        Dict con todas las rutas generadas
    """
    rutas = {}
    fecha_str = datetime.now().strftime("%Y%m%d")
    
    # ===== ARCHIVOS ACTUALES =====
    # Dashboard consolidado
    ts_dash = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dashboard_actual = dirs['dashboards'] / f"dashboard_consolidado_{ts_dash}.html"
    fig_dashboard.write_html(str(dashboard_actual), config=PLOTLY_CONFIG_INTERACTIVE)
    rutas['dashboard_actual'] = dashboard_actual

    # Tabla resumen
    ts_tabla = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    tabla_resumen = dirs['tablas'] / f"tabla_resumen_ibcs_{ts_tabla}.html"
    fig_tabla_resumen.write_html(str(tabla_resumen), config=PLOTLY_CONFIG_STATIC)
    rutas['tabla_resumen'] = tabla_resumen

    # Tablas individuales
    rutas['tablas_individuales'] = []
    for contratista, fig_tabla in tablas_individuales.items():
        ts_ind = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        tabla_ind = dirs['tablas'] / f"tabla_{contratista.lower()}_{ts_ind}.html"
        fig_tabla.write_html(str(tabla_ind), config=PLOTLY_CONFIG_STATIC)
        rutas['tablas_individuales'].append(tabla_ind)
    
    # ===== ARCHIVOS HISTÓRICOS POR SEMANA =====
    semana_dir = dirs['historico'] / f"{semana}_{fecha_str}"
    semana_dir.mkdir(parents=True, exist_ok=True)
    graficos_dir = semana_dir / "graficos"
    graficos_dir.mkdir(parents=True, exist_ok=True)
    
    # Dashboard consolidado histórico
    dashboard_hist = semana_dir / f"dashboard_consolidado_{semana}_{fecha_str}.html"
    fig_dashboard.write_html(str(dashboard_hist), config=PLOTLY_CONFIG_INTERACTIVE)
    rutas['dashboard_historico'] = dashboard_hist
    
    # Tabla resumen histórica
    tabla_res_hist = semana_dir / f"tabla_resumen_{semana}_{fecha_str}.html"
    fig_tabla_resumen.write_html(str(tabla_res_hist), config=PLOTLY_CONFIG_STATIC)
    rutas['tabla_resumen_historico'] = tabla_res_hist
    
    # Tablas individuales históricas
    rutas['tablas_individuales_historico'] = []
    for contratista, fig_tabla in tablas_individuales.items():
        tabla_ind_hist = semana_dir / f"tabla_{contratista.lower()}_{semana}_{fecha_str}.html"
        fig_tabla.write_html(str(tabla_ind_hist), config=PLOTLY_CONFIG_STATIC)
        rutas['tablas_individuales_historico'].append(tabla_ind_hist)
    
    # Datos Excel consolidados
    dirs['data_historico_consolidado'].mkdir(parents=True, exist_ok=True)
    excel_historico = dirs['data_historico_consolidado'] / f"ctrl_dosieres_consolidado_{semana}.xlsx"
    df_consolidado.to_excel(str(excel_historico), sheet_name="ctrl_dosieres", index=False, engine='openpyxl')
    rutas['excel_historico'] = excel_historico
    
    return rutas


def limpiar_archivos_antiguos(directorio: Path, patron: str, mantener: int = 1) -> None:
    """
    Limpia archivos antiguos manteniendo solo los más recientes.
    
    NOTA: NO limpia output/exports/ ya que es histórico por SEMANA DE CORTE.
    
    Args:
        directorio: Carpeta donde buscar archivos
        patron: Patrón glob para buscar (ej: 'dashboard_*.html')
        mantener: Número de archivos más recientes a mantener
    """
    # Proteger output/exports/
    if 'exports' in str(directorio):
        return
    
    archivos = list(directorio.glob(patron))
    if len(archivos) > mantener:
        archivos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        for archivo_viejo in archivos[mantener:]:
            archivo_viejo.unlink()


def mostrar_resumen_archivos(rutas: dict, output_dir: Path, semana: str) -> None:
    """Muestra un resumen organizado de los archivos generados."""
    print(f"\n{'='*60}")
    print("ARCHIVOS GENERADOS")
    print(f"{'='*60}\n")
    
    if 'dashboard_actual' in rutas:
        print(f"[OK] Dashboard: dashboards/{rutas['dashboard_actual'].name}")
    
    if 'tabla_resumen' in rutas:
        print(f"[OK] Tabla Resumen: tablas/{rutas['tabla_resumen'].name}")
    
    if 'tablas_individuales' in rutas and rutas['tablas_individuales']:
        print(f"\n[INFO] Tablas Individuales:")
        for tabla in rutas['tablas_individuales']:
            print(f"  • {tabla.name}")
    
    print(f"\n[INFO] Histórico Semana {semana}:")
    if 'dashboard_historico' in rutas:
        print(f"  • Dashboard: {rutas['dashboard_historico'].relative_to(output_dir)}")
    if 'tabla_resumen_historico' in rutas:
        print(f"  • Tabla Resumen: {rutas['tabla_resumen_historico'].relative_to(output_dir)}")
    if 'excel_historico' in rutas:
        print(f"  • Datos Excel: {rutas['excel_historico']}")
    
    print(f"\n[INFO] Estructura de archivos:")
    print(f"  output/")
    print(f"    ├── dashboards/     [Dashboards actuales]")
    print(f"    ├── tablas/         [Tablas actuales]")
    print(f"    └── historico/      [Histórico por semana]")
