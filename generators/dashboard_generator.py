#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Control de Dossieres BAYSA/INPROS - CLI
======================================================

Script de línea de comandos para generar dashboards interactivos
desde archivos Excel de control de dossieres.

Uso:
    python dashboard.py                          # Usar configuración por defecto
    python dashboard.py --input datos.xlsx       # Especificar archivo de entrada
    python dashboard.py --no-cache              # Deshabilitar caché
    python dashboard.py --export pdf png        # Exportar en múltiples formatos
    python dashboard.py --help                  # Mostrar ayuda

Autor: Jose Luis
Fecha: Noviembre 2025
"""

import argparse
import logging
import sys
import os

# Configurar encoding UTF-8 para stdout/stderr
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pickle

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml

# Importar funciones core de métricas (ÚNICA FUENTE DE VERDAD)
from core.metricas import (
    calcular_metricas_individuales,
    validar_consistencia_metricas,
    imprimir_metricas
)

# Importar utilidades comunes
from generators.utils_generator import (
    obtener_estructura_directorios,
    crear_directorios,
    solicitar_semana,
    guardar_archivos_individuales
)

# ========== CONFIGURACIÓN DE LOGGING ==========

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== FUNCIONES DE UTILIDAD ==========

def cargar_configuracion(config_path: str = "config.yaml") -> Dict:
    """Carga configuración desde archivo YAML."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Configuración cargada desde {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"❌ Archivo de configuración no encontrado: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"❌ Error al parsear configuración YAML: {e}")
        sys.exit(1)

def obtener_cache_path(cache_dir: Path, nombre: str) -> Path:
    """Genera ruta para archivo de caché."""
    return cache_dir / f"{nombre}.pkl"

def cache_es_valido(cache_path: Path, archivo_fuente: Path, max_age_hours: int = 24) -> bool:
    """Verifica si el caché existe, no está expirado y es más reciente que el archivo fuente."""
    if not cache_path.exists():
        return False
    
    # Verificar edad del caché
    edad_horas = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds() / 3600
    if edad_horas >= max_age_hours:
        return False
    
    # Verificar si el archivo fuente fue modificado después del caché
    if archivo_fuente.exists():
        fecha_cache = cache_path.stat().st_mtime
        fecha_fuente = archivo_fuente.stat().st_mtime
        if fecha_fuente > fecha_cache:
            logger.info("📝 Archivo fuente modificado - invalidando caché")
            return False
    
    return True

def guardar_cache(obj, cache_path: Path) -> None:
    """Guarda objeto en caché."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'wb') as f:
        pickle.dump(obj, f)
    logger.info(f"💾 Caché guardado: {cache_path.name}")

def cargar_cache(cache_path: Path):
    """Carga objeto desde caché."""
    with open(cache_path, 'rb') as f:
        obj = pickle.load(f)
    logger.info(f"💾 Caché cargado: {cache_path.name}")
    return obj

def validar_datos(df: pd.DataFrame, columnas_requeridas: List[str]) -> None:
    """Valida que el DataFrame tenga las columnas requeridas."""
    faltantes = set(columnas_requeridas) - set(df.columns)
    if faltantes:
        raise ValueError(f"❌ Columnas faltantes en el archivo: {faltantes}")
    logger.info(f"✅ Validación exitosa: {len(columnas_requeridas)} columnas encontradas")

# ========== PROCESAMIENTO DE DATOS ==========

def obtener_columnas_fecha(rev_nums: range) -> Tuple[List[str], List[str]]:
    """Genera listas de columnas de fecha para BAYSA e INPROS."""
    baysa_cols = [f"BAYSA ENTREGA FECHA R{r}" for r in rev_nums]
    inpros_cols = [f"INPROS RESPUESTA FECHA R{r}" for r in rev_nums]
    return baysa_cols, inpros_cols

def normalizar_fechas(df: pd.DataFrame, columnas_fecha: List[str]) -> pd.DataFrame:
    """Convierte columnas de fecha a datetime."""
    df_copy = df.copy()
    for col in columnas_fecha:
        if col in df_copy.columns:
            df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce")
    return df_copy

def calcular_metricas_proceso(df: pd.DataFrame, baysa_cols: List[str], inpros_cols: List[str]) -> pd.DataFrame:
    """Calcula métricas de proceso en un pipeline."""
    # Verificar si existen las columnas de fechas
    baysa_cols_exist = [c for c in baysa_cols if c in df.columns]
    inpros_cols_exist = [c for c in inpros_cols if c in df.columns]
    
    # Si no hay columnas de fechas, solo calcular NO_REVISIONES_REALIZADAS basado en No. REVISIÓN
    if not baysa_cols_exist and not inpros_cols_exist:
        return df.assign(
            NO_REVISIONES_REALIZADAS=lambda x: x.get('No. REVISIÓN', 0).fillna(0).astype(int)
        ).assign(
            # Si el estatus es PLANEADO, el nivel de revisión debe ser 0
            NO_REVISIONES_REALIZADAS=lambda x: x.apply(
                lambda row: 0 if row.get('ESTATUS') == 'PLANEADO' else row['NO_REVISIONES_REALIZADAS'],
                axis=1
            )
        )
    
    # Si existen columnas de fechas, calcular métricas completas
    return (
        df.assign(
            PRIMERA_ENTREGA_BAYSA_FECHA=lambda x: x[baysa_cols_exist].min(axis=1) if baysa_cols_exist else pd.NaT,
            ULTIMA_RESPUESTA_INPROS_FECHA=lambda x: x[inpros_cols_exist].max(axis=1) if inpros_cols_exist else pd.NaT
        )
        .assign(
            NO_REVISIONES_REALIZADAS=lambda x: (
                x[baysa_cols_exist].notna() | x[inpros_cols_exist].notna()
            ).sum(axis=1) if (baysa_cols_exist or inpros_cols_exist) else x.get('No. REVISIÓN', 0).fillna(0).astype(int)
        )
        .assign(
            # Si el estatus es PLANEADO, el nivel de revisión debe ser 0
            NO_REVISIONES_REALIZADAS=lambda x: x.apply(
                lambda row: 0 if row.get('ESTATUS') == 'PLANEADO' else row['NO_REVISIONES_REALIZADAS'],
                axis=1
            )
        )
        .assign(
            TIEMPO_TOTAL_PROCESO_DIAS=lambda x: (
                x['ULTIMA_RESPUESTA_INPROS_FECHA'] - x['PRIMERA_ENTREGA_BAYSA_FECHA']
            ).dt.days if baysa_cols_exist and inpros_cols_exist else 0
        )
    )

def detectar_columna_bloque(df: pd.DataFrame, columnas_posibles: List[str]) -> Optional[str]:
    """Detecta la primera columna de identificador de bloque disponible."""
    for col in columnas_posibles:
        if col in df.columns:
            return col
    return None

def preparar_bloques_revision(df: pd.DataFrame, top_n: int = 15,
                             colores_estatus: Dict[str, str] = None,
                             in_review_statuses: List[str] = None) -> pd.DataFrame:
    """Prepara DataFrame de bloques en revisión con pipeline optimizado.

    Parámetros:
    - df: DataFrame fuente
    - top_n: máximos bloques a devolver
    - colores_estatus: mapeo estatus -> color
    - in_review_statuses: lista de estatus que se consideran "en revisión"
    """

    if in_review_statuses is None:
        in_review_statuses = ['OBSERVADO', 'EN_REVISIÓN']

    bloques = df[
        (df['ESTATUS'].isin(in_review_statuses)) &
        (df['NO_REVISIONES_REALIZADAS'] > 0)
    ].copy()
    
    if bloques.empty:
        return pd.DataFrame()
    
    columnas_posibles = ['DOSIER', 'DOSIER / SUBESTACION', 'BLOQUE', 'SUBESTACION']
    bloque_col = detectar_columna_bloque(df, columnas_posibles)
    
    if bloque_col:
        bloques = bloques.assign(BLOQUE_ID=lambda x: x[bloque_col].astype(str))
    elif 'ETAPA' in df.columns:
        bloques = bloques.assign(
            BLOQUE_ID=lambda x: x['ETAPA'].astype(str) + '_' + x.index.astype(str)
        )
    else:
        bloques = bloques.assign(
            BLOQUE_ID=lambda x: 'BLOQUE_' + x.index.astype(str)
        )
    
    return (
        bloques
        .sort_values('NO_REVISIONES_REALIZADAS', ascending=False)
        .head(top_n)
        .assign(COLOR=lambda x: x['ESTATUS'].map(colores_estatus))
        .reset_index(drop=True)
    )

def calcular_metricas_generales(df: pd.DataFrame) -> Dict:
    """
    Calcula métricas generales del proyecto.
    
    IMPORTANTE: Esta función ahora delega al módulo metricas_core.py
    para asegurar consistencia con dashboard_consolidado.py
    """
    return calcular_metricas_individuales(df)

def calcular_distribucion_estatus(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribución por estatus."""
    return df.groupby('ESTATUS', dropna=False).agg(
        CANTIDAD=('ESTATUS', 'count'),
        PESO=('PESO', lambda x: x.sum() / 1000)  # Convertir kg a ton
    ).reset_index()

def calcular_progreso_etapa(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula progreso por etapa desglosado por estatus (CANTIDAD y PESO)."""
    if 'ETAPA' not in df.columns or 'ESTATUS' not in df.columns:
        return pd.DataFrame()
    
    # Agregar por ETAPA y ESTATUS para obtener cantidad y peso
    df_etapa_estatus = (
        df.groupby(['ETAPA', 'ESTATUS'], dropna=False)
        .agg(
            CANTIDAD=('ESTATUS', 'count'),
            PESO=('PESO', lambda x: x.sum() / 1000)  # Convertir kg a ton
        )
        .reset_index()
    )
    
    return df_etapa_estatus

# ========== GENERACIÓN DE GRÁFICOS ==========

def crear_gauge(valor: float, titulo: str, color: str = '#0F7C3F', tipo_config: dict = None) -> go.Indicator:
    """Crea un indicador tipo gauge con tipografía IBCS mejorada para pantalla."""
    if tipo_config is None:
        tipo_config = {'subtitulos': 22, 'metricas_grandes': 36, 'familia_principal': 'Segoe UI, Arial, sans-serif'}
    
    # Grises neutros para steps (IBCS estándar)
    steps_colors = ["#F5F5F5", "#E0E0E0", "#D3D3D3"]
    
    return go.Indicator(
        mode="gauge+number+delta",
        value=valor,
        number={'suffix': "%", 'font': {'size': tipo_config.get('metricas_grandes', 36), 'color': color, 'family': tipo_config.get('familia_principal', 'Segoe UI'), 'weight': 'bold'}},
        delta={'reference': 90, 'increasing': {'color': color}, 'suffix': "% vs Meta", 'font': {'size': 14}},
        title={'text': f"<b style='font-size:{tipo_config.get('subtitulos', 22)}px'>{titulo}</b><br><span style='font-size:13px; color:#666;'>Meta: 90%</span>", 'font': {'size': tipo_config.get('subtitulos', 22), 'family': tipo_config.get('familia_principal', 'Segoe UI')}},
        gauge={
            'axis': {'range': [0, 100], 'ticksuffix': '%', 'tickfont': {'size': tipo_config.get('etiquetas', 14), 'family': tipo_config.get('familia_principal', 'Segoe UI')}},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "#FFFFFF",
            'borderwidth': 1,
            'bordercolor': "#E5E5E5",
            'steps': [
                {'range': [0, 33], 'color': steps_colors[0]},
                {'range': [33, 66], 'color': steps_colors[1]},
                {'range': [66, 100], 'color': steps_colors[2]}
            ],
            'threshold': {
                'line': {'color': color, 'width': 3},
                'thickness': 0.75,
                'value': 90
            }
        }
    )

def crear_dona(labels: List, values: List, colores: List, hover_format: str = 'cantidad') -> go.Pie:
    """Crea un gráfico de dona con tipografía mejorada para pantalla."""
    hover_template = '<b style="font-size:14px">%{label}</b><br>Cantidad: %{value}<br>Porcentaje: %{percent}<extra></extra>' \
        if hover_format == 'cantidad' else '<b style="font-size:14px">%{label}</b><br>Peso: %{value:,.0f}<br>Porcentaje: %{percent}<extra></extra>'
    
    return go.Pie(
        labels=labels, values=values, hole=0.4,
        marker=dict(colors=colores, line=dict(color='white', width=2)),
        textposition='inside', textinfo='percent',
        textfont=dict(size=16, color='white', family='Segoe UI, Arial, sans-serif', weight='bold'),
        hovertemplate=hover_template,
        showlegend=False, pull=[0.05, 0, 0, 0]
    )

def generar_dashboard(mej: pd.DataFrame, config: Dict, semana_corte: str = "S186") -> go.Figure:
    """Genera el dashboard completo."""
    
    # Configuración IBCS
    tipo = config['dashboard'].get('tipografia', {})
    font_family = tipo.get('familia_principal', 'Segoe UI, Arial, sans-serif')
    grid_color = config['colores'].get('GRID', '#E5E5E5')
    texto_color = config['colores'].get('TEXTO_SECUNDARIO', '#6B6B6B')
    texto_principal = config['colores'].get('TEXTO_PRINCIPAL', '#2C2C2C')
    fondo_color = config['colores'].get('FONDO', '#FFFFFF')
    
    # Calcular métricas
    metricas = calcular_metricas_generales(mej)
    df_estatus = calcular_distribucion_estatus(mej)
    df_etapa_progress = calcular_progreso_etapa(mej)
    bloques_en_revision = preparar_bloques_revision(
        mej,
        config['dashboard']['top_bloques'],
        config['colores'],
        config['dashboard'].get('in_review_statuses', ['OBSERVADO', 'EN_REVISIÓN'])
    )
    
    # Preparar colores
    colores_grafico = [config['colores'].get(estatus, '#999999') for estatus in df_estatus['ESTATUS']]
    
    # Crear estructura
    fig = make_subplots(
        rows=3, cols=2,
        row_heights=[0.15, 0.35, 0.50],
        column_widths=config['dashboard']['column_widths'],
        subplot_titles=('', '', '<b>Distribución por Cantidad</b>', '<b>Distribución por Peso</b>',
                       '<b>Dossieres por ETAPA</b>', '<b>Peso por ETAPA</b>'),
        specs=[
            [{'type': 'indicator'}, {'type': 'indicator'}],
            [{'type': 'pie'}, {'type': 'pie'}],
            [{'type': 'bar'}, {'type': 'bar'}]
        ],
        vertical_spacing=config['dashboard']['vertical_spacing'],
        horizontal_spacing=config['dashboard']['horizontal_spacing']
    )
    
    # Row 1: KPIs con colores IBCS
    gauge_color = config['colores']['LIBERADO']
    fig.add_trace(crear_gauge(metricas['pct_liberado'], "% Dossiers Liberados", gauge_color, tipo), row=1, col=1)
    fig.add_trace(crear_gauge(metricas['pct_peso_liberado'], "% Peso Liberado", gauge_color, tipo), row=1, col=2)
    
    # Row 2: Donas
    fig.add_trace(crear_dona(df_estatus['ESTATUS'], df_estatus['CANTIDAD'], colores_grafico, 'cantidad'), row=2, col=1)
    fig.add_trace(crear_dona(df_estatus['ESTATUS'], df_estatus['PESO'], colores_grafico, 'peso'), row=2, col=2)
    
    # Leyenda: mostrar sólo estatus presentes en los datos, con orden preferente
    prefer_order = ["LIBERADO", "PLANEADO", "OBSERVADO", "EN_REVISIÓN"]
    presentes = list(df_estatus['ESTATUS']) if not df_estatus.empty else []
    # Mantener orden preferente y luego cualquier estatus adicional
    legend_statuses = [s for s in prefer_order if s in presentes] + [s for s in presentes if s not in prefer_order]
    parts = []
    for st in legend_statuses:
        color = config['colores'].get(st, '#999999')
        label = st
        parts.append(f'<span style="color:{color}">●</span> {label}')
    leyenda_html = ' | '.join(parts) if parts else ''
    fig.add_annotation(
        text=leyenda_html,
        xref="paper", yref="paper", x=0.5, y=0.56,
        xanchor="center", yanchor="top", showarrow=False,
        font=dict(
            size=tipo.get('anotaciones', 14), 
            family=font_family,
            color=config['colores'].get('TEXTO_SECUNDARIO', '#2C2C2C')
        ),
        bgcolor="rgba(255,255,255,0.95)", borderpad=8,
        bordercolor=grid_color, borderwidth=1
    )
    
    # Row 3: Barras por ETAPA desglosadas por ESTATUS (misma matriz que donas)
    if not df_etapa_progress.empty:
        # Definir orden preferente de estatus
        prefer_order = ['LIBERADO', 'PLANEADO', 'OBSERVADO', 'EN_REVISIÓN']
        # Eliminar valores NaN antes de ordenar
        estatus_presentes = sorted([s for s in df_etapa_progress['ESTATUS'].unique() if pd.notna(s)])
        estatus_order = [s for s in prefer_order if s in estatus_presentes] + [s for s in estatus_presentes if s not in prefer_order]
        
        # CANTIDAD por ETAPA y ESTATUS
        for estatus in estatus_order:
            df_est = df_etapa_progress[df_etapa_progress['ESTATUS'] == estatus].copy()
            if df_est.empty:
                continue
            
            # Agrupar por ETAPA para asegurar que se agrega correctamente
            df_est_agg = df_est.groupby('ETAPA')['CANTIDAD'].sum().reset_index()
            
            fig.add_trace(go.Bar(
                y=df_est_agg['ETAPA'], x=df_est_agg['CANTIDAD'],
                orientation='h', 
                name=estatus,
                marker=dict(color=config['colores'].get(estatus, '#999999')),
                text=df_est_agg['CANTIDAD'],
                textposition='auto', 
                textfont=dict(color='white', size=tipo.get('valores_graficos', 16), family=font_family, weight='bold'),
                hovertemplate='<b style="font-size:14px">%{y}</b><br>' + estatus + ': %{x}<extra></extra>',
                showlegend=False
            ), row=3, col=1)
        
        # PESO por ETAPA y ESTATUS
        for estatus in estatus_order:
            df_est = df_etapa_progress[df_etapa_progress['ESTATUS'] == estatus].copy()
            if df_est.empty:
                continue
            
            # Agrupar por ETAPA
            df_est_agg = df_est.groupby('ETAPA')['PESO'].sum().reset_index()
            
            fig.add_trace(go.Bar(
                y=df_est_agg['ETAPA'], x=df_est_agg['PESO'],
                orientation='h', 
                name=estatus,
                marker=dict(color=config['colores'].get(estatus, '#999999')),
                text=df_est_agg['PESO'].apply(lambda x: f'{x:,.0f}'),
                textposition='auto', 
                textfont=dict(color='white', size=tipo.get('valores_graficos', 15), family=font_family, weight='bold'),
                hovertemplate='<b style="font-size:14px">%{y}</b><br>' + estatus + ': %{x:,.0f}<extra></extra>',
                showlegend=False
            ), row=3, col=2)
        
        # Leyenda basada en estatus presentes
        leyenda_parts = []
        for st in estatus_order:
            color = config['colores'].get(st, '#999999')
            leyenda_parts.append(f'<span style="color:{color}">●</span> {st}')
        leyenda_barras = ' | '.join(leyenda_parts)
        
        fig.add_annotation(
            text=leyenda_barras,
            xref="paper", yref="paper", x=0.5, y=0.32,
            xanchor="center", yanchor="top", showarrow=False,
            font=dict(size=tipo.get('anotaciones', 14), family=font_family, color='#2C2C2C'),
            bgcolor="rgba(255,255,255,0.95)", borderpad=8,
            bordercolor=grid_color, borderwidth=1
        )
    
    # Row 4: Bloques en revisión (DESHABILITADO)
    # if len(bloques_en_revision) > 0:
    #     fig.add_trace(go.Bar(
    #         y=bloques_en_revision['BLOQUE_ID'].tolist(),
    #         x=bloques_en_revision['NO_REVISIONES_REALIZADAS'].astype(int).tolist(),
    #         orientation='h', marker=dict(color=bloques_en_revision['COLOR'].tolist()),
    #         text=[f'{rev} rev' for rev in bloques_en_revision['NO_REVISIONES_REALIZADAS'].astype(int)],
    #         textposition='auto', textfont=dict(
    #             size=tipo.get('valores_graficos', 15), 
    #             color='white', 
    #             family=font_family,
    #             weight='bold'
    #         ),
    #         hovertemplate='<b style="font-size:14px">%{y}</b><br>Revisiones: %{x}<br>Estatus: %{customdata[0]}<br>Peso: %{customdata[1]:,.0f}<extra></extra>',
    #         customdata=list(zip(bloques_en_revision['ESTATUS'], bloques_en_revision['PESO'])),
    #         showlegend=False
    #     ), row=4, col=1)
    
    # Layout con diseño IBCS
    # Construir subtítulo con métricas clave
    subtitulo_base = f"<b style='color:#0F7C3F'>📅 SEMANA DE CORTE: {semana_corte}</b> | Total: {metricas['total_dossiers']} dossieres | Liberados: {metricas['dossiers_liberados']} ({metricas['pct_liberado']:.1f}%) | Peso Liberado: {metricas['peso_liberado']:,.2f} ({metricas['pct_peso_liberado']:.1f}%)"
    subtitulo_ejecucion = f" | ✓ Ejecución Real: {metricas['pct_ejecucion_real']:.1f}%"
    subtitulo_alerta = f" | ⚠️ {metricas['bloques_brecha_invalida']} bloques con ajustes pendientes" if metricas['bloques_brecha_invalida'] > 0 else ""
    
    # Obtener nombre de la contratista desde la configuración (si existe)
    titulo_dashboard = config.get('contratista', {}).get('titulo_dashboard', 'DASHBOARD DE CONTROL - DOSSIERES')
    
    fig.update_layout(
        title={
            'text': f"<b>{titulo_dashboard}</b><br><span style='font-size:16px; font-weight:normal;'>{subtitulo_base}{subtitulo_ejecucion}{subtitulo_alerta}</span>",
            'x': 0.5, 'xanchor': 'center', 
            'font': {'size': tipo.get('titulo_dashboard', 38), 'family': font_family, 'color': texto_principal, 'weight': 'bold'}
        },
        height=config['dashboard']['height'],
        showlegend=False, barmode='stack', hovermode='closest',
        dragmode='pan',  # Permite desplazar/mover gráficos en lugar de zoom
        plot_bgcolor=fondo_color,
        paper_bgcolor=fondo_color,
        font=dict(family=font_family, size=tipo.get('etiquetas', 16), color=texto_principal),
        margin=dict(
            l=config['dashboard']['margin_left'],
            r=config['dashboard']['margin_right'],
            t=config['dashboard']['margin_top'],
            b=config['dashboard']['margin_bottom']
        )
    )
    
    # Configurar ejes con estilo IBCS y tipografía mejorada
    fig.update_xaxes(
        title_text="<b>Cantidad</b>", row=3, col=1, 
        title_font=dict(size=tipo.get('subtitulos', 22), family=font_family, color=texto_principal), 
        gridcolor=grid_color, tickfont=dict(color=texto_color, family=font_family, size=14)
    )
    fig.update_xaxes(
        title_text="<b>Peso</b>", row=3, col=2, 
        title_font=dict(size=tipo.get('subtitulos', 22), family=font_family, color=texto_principal), 
        gridcolor=grid_color, tickfont=dict(color=texto_color, family=font_family, size=14)
    )
    # Remover grid de los gráficos de barras (Row 3)
    fig.update_xaxes(showgrid=False, zeroline=False, row=3)
    fig.update_yaxes(showgrid=False, zeroline=False, row=3)
    
    # Ajustar subtítulos con estilo IBCS y mejor legibilidad
    for i, annotation in enumerate(fig.layout.annotations):
        if i >= 2 and i <= 5:
            annotation.font.size = tipo.get('subtitulos', 24)
            annotation.font.color = texto_principal
            annotation.font.family = font_family
    
    return fig, metricas, bloques_en_revision

# ========== FUNCIÓN PRINCIPAL ==========

def main():
    """Función principal del CLI."""
    
    parser = argparse.ArgumentParser(
        description='Genera dashboard interactivo de control de dossieres BAYSA/INPROS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python dashboard.py
  python dashboard.py --input data/nuevo_archivo.xlsx
  python dashboard.py --no-cache
  python dashboard.py --export pdf png
  python dashboard.py --config mi_config.yaml
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Archivo Excel de entrada (default: config.yaml)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Carpeta de salida (default: config.yaml)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.yaml',
        help='Archivo de configuración YAML (default: config.yaml)'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Deshabilitar caché (procesar desde Excel siempre)'
    )
    
    parser.add_argument(
        '--export', '-e',
        nargs='+',
        choices=['html', 'pdf', 'png'],
        default=['html'],
        help='Formatos de exportación (default: html)'
    )
    
    args = parser.parse_args()
    
    # Cargar configuración
    config = cargar_configuracion(args.config)
    
    # Override con argumentos de CLI
    if args.input:
        config['paths']['input_file'] = args.input
    if args.output:
        config['paths']['output_dir'] = args.output
    if args.no_cache:
        config['cache']['enabled'] = False
    
    # Preparar rutas
    input_file = Path(config['paths']['input_file'])
    output_dir = Path(config['paths']['output_dir'])
    cache_dir = Path(config['paths']['cache_dir'])
    
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Mostrar información
    print("\n" + "="*70)
    print("🚀 DASHBOARD DE CONTROL DE DOSSIERES BAYSA/INPROS")
    print("="*70)
    print(f"📁 Entrada: {input_file}")
    print(f"📁 Salida: {output_dir}")
    print(f"💾 Caché: {'Habilitado' if config['cache']['enabled'] else 'Deshabilitado'}")
    print(f"📤 Exportar: {', '.join(args.export).upper()}")
    print("="*70 + "\n")
    
    # Cargar datos
    cache_nombre = 'datos_procesados'
    cache_path = obtener_cache_path(cache_dir, cache_nombre)
    usar_cache = config['cache']['enabled'] and cache_es_valido(cache_path, input_file, config['cache']['max_age_hours'])
    
    if usar_cache:
        logger.info("💾 Cargando datos desde caché...")
        mej = cargar_cache(cache_path)
    else:
        logger.info("📂 Cargando datos desde Excel...")
        
        if not input_file.exists():
            logger.error(f"❌ Archivo no encontrado: {input_file}")
            sys.exit(1)
        
        # Detectar tipo de archivo y cargar
        if input_file.suffix.lower() == '.csv':
            logger.info("📄 Detectado archivo CSV")
            # Intentar diferentes codificaciones
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df_orig = None
            for enc in encodings:
                try:
                    df_orig = pd.read_csv(input_file, encoding=enc)
                    logger.info(f"✅ Archivo CSV cargado con codificación: {enc}")
                    break
                except UnicodeDecodeError:
                    continue
            if df_orig is None:
                raise ValueError("No se pudo leer el archivo CSV con ninguna codificación soportada")
        else:
            logger.info("📊 Detectado archivo Excel")
            df_orig = pd.read_excel(input_file, config['excel']['sheet_ctrl'])
        
        validar_datos(df_orig, ['ESTATUS', 'PESO'])
        
        rev_nums = range(config['excel']['rev_nums_min'], config['excel']['rev_nums_max'])
        baysa_fecha_cols, inpros_fecha_cols = obtener_columnas_fecha(rev_nums)
        
        mej = (
            df_orig
            .pipe(normalizar_fechas, baysa_fecha_cols + inpros_fecha_cols)
            .pipe(calcular_metricas_proceso, baysa_fecha_cols, inpros_fecha_cols)
        )
        
        if config['cache']['enabled']:
            guardar_cache(mej, cache_path)
        
        logger.info(f"✅ Datos procesados: {mej.shape[0]} registros")
    
    # Capturar semana de corte (primero desde variable de entorno, luego solicitar)
    semana_corte = os.getenv('SEMANA_CORTE') or os.getenv('SEMANA_PROYECTO')
    if semana_corte:
        semana = semana_corte.strip().upper()
        logger.info(f"📌 Semana de corte: {semana}")
    else:
        # Solicitar semana de proyecto
        semana = solicitar_semana(tipo='proyecto')
    
    # Generar dashboard
    logger.info("🎨 Generando dashboard...")
    fig, metricas, bloques = generar_dashboard(mej, config, semana)
    
    # Preparar estructura de directorios estandarizada
    dirs = obtener_estructura_directorios(output_dir)
    crear_directorios(dirs)
    
    # Obtener nombre de contratista
    nombre_contratista = config.get('contratista', {}).get('nombre', 'dashboard')
    fecha_str = datetime.now().strftime("%Y%m%d")
    
    # Exportar archivos
    archivos_generados = []
    
    if 'html' in args.export or config['export']['html']:
        # Leer datos para backup si es necesario
        df_backup = None
        if config['export'].get('excel', False):
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            for enc in encodings:
                try:
                    df_backup = pd.read_csv(input_file, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            if df_backup is None:
                logger.warning("No se pudo leer el archivo CSV para backup Excel")
        
        # Guardar usando utilidad común
        dashboard_actual, dashboard_historico = guardar_archivos_individuales(
            fig_dashboard=fig,
            contratista=nombre_contratista,
            timestamp=timestamp,
            semana=semana,
            dirs=dirs,
            config=config,
            df_data=df_backup
        )
        
        archivos_generados.append(dashboard_actual)
        logger.info(f"✅ HTML generado: {dashboard_actual.name}")
        logger.info(f"📦 Dashboard guardado en histórico: {dashboard_historico.relative_to(output_dir)}")
        
        # Obtener directorios de gráficos
        semana_dir = dashboard_historico.parent
        graficos_dir = semana_dir / "graficos"
        
        # Exportar gráficos individuales
        logger.info("🎨 Exportando gráficos individuales...")
        
        # Gauge 1: % Dossiers Liberados
        gauge1 = go.Figure(fig.data[0])
        gauge1.update_layout(title="% Dossiers Liberados", height=400, width=500)
        gauge1.write_html(str(graficos_dir / "01_gauge_dossiers_liberados.html"))
        
        # Gauge 2: % Peso Liberado
        gauge2 = go.Figure(fig.data[1])
        gauge2.update_layout(title="% Peso Liberado", height=400, width=500)
        gauge2.write_html(str(graficos_dir / "02_gauge_peso_liberado.html"))
        
        # Dona 1: Distribución por Cantidad
        dona1 = go.Figure(fig.data[2])
        dona1.update_layout(title="Distribución por Cantidad", height=500, width=600)
        dona1.write_html(str(graficos_dir / "03_dona_cantidad.html"))
        
        # Dona 2: Distribución por Peso
        dona2 = go.Figure(fig.data[3])
        dona2.write_html(str(graficos_dir / "04_dona_peso.html"))
        
        # Barras ETAPA - Cantidad (Liberados + Pendientes)
        barras_etapa_cant = go.Figure()
        if len(fig.data) > 4:
            barras_etapa_cant.add_trace(fig.data[4])  # Liberados
            if len(fig.data) > 5:
                barras_etapa_cant.add_trace(fig.data[5])  # Pendientes
            barras_etapa_cant.update_layout(
                title="Dossieres por ETAPA", 
                xaxis_title="Cantidad", 
                yaxis_title="ETAPA",
                barmode='stack',
                height=500, 
                width=700
            )
            barras_etapa_cant.write_html(str(graficos_dir / "05_barras_etapa_cantidad.html"))
        
        # Barras ETAPA - Peso (Liberados + Pendientes)
        barras_etapa_peso = go.Figure()
        if len(fig.data) > 6:
            barras_etapa_peso.add_trace(fig.data[6])  # Liberados
            if len(fig.data) > 7:
                barras_etapa_peso.add_trace(fig.data[7])  # Pendientes
            barras_etapa_peso.update_layout(
                title="Peso por ETAPA", 
                xaxis_title="Peso", 
                yaxis_title="ETAPA",
                barmode='stack',
                height=500, 
                width=700
            )
            barras_etapa_peso.write_html(str(graficos_dir / "06_barras_etapa_peso.html"))
        
        # Barras: Bloques en Ciclo de Revisión (DESHABILITADO)
        # if len(fig.data) > 8 and len(bloques) > 0:
        #     barras_revision = go.Figure(fig.data[8])
        #     barras_revision.update_layout(
        #         title="Bloques en Ciclo de Revisión (Top 15)", 
        #         xaxis_title="Número de Revisiones",
        #         yaxis_title="Bloque / Dossier",
        #         height=600, 
        #         width=800
        #     )
        #     barras_revision.write_html(str(graficos_dir / "07_barras_bloques_revision.html"))
        
        logger.info(f"✅ {len(list(graficos_dir.glob('*.html')))} gráficos individuales guardados en: {graficos_dir.relative_to(output_dir)}")
    
    if 'pdf' in args.export and config['export'].get('pdf', False):
        try:
            pdf_file = output_dir / f"dashboard_{timestamp}.pdf"
            fig.write_image(
                str(pdf_file),
                width=config['export']['image']['width'],
                height=config['export']['image']['height'],
                scale=config['export']['image']['scale']
            )
            archivos_generados.append(pdf_file)
            logger.info(f"✅ PDF generado: {pdf_file.name}")
        except Exception as e:
            logger.error(f"❌ Error al generar PDF: {e}")
            logger.error("💡 Instala kaleido: pip install kaleido")
    
    if 'png' in args.export and config['export'].get('png', False):
        try:
            png_file = output_dir / f"dashboard_{timestamp}.png"
            fig.write_image(
                str(png_file),
                width=config['export']['image']['width'],
                height=config['export']['image']['height'],
                scale=config['export']['image']['scale']
            )
            archivos_generados.append(png_file)
            logger.info(f"✅ PNG generado: {png_file.name}")
        except Exception as e:
            logger.error(f"❌ Error al generar PNG: {e}")
            logger.error("💡 Instala kaleido: pip install kaleido")
    
    # Resumen final
    print("\n" + "="*70)
    print("✅ DASHBOARD GENERADO EXITOSAMENTE")
    print("="*70)
    print(f"\n📊 Estadísticas:")
    print(f"   • Dossieres procesados: {metricas['total_dossiers']}")
    print(f"   • Liberados: {metricas['dossiers_liberados']} ({metricas['pct_liberado']:.1f}%)")
    print(f"   • Peso liberado: {metricas['peso_liberado']:,.0f} ton ({metricas['pct_peso_liberado']:.1f}%)")
    print(f"   • Bloques en revisión: {len(bloques)}")
    
    print(f"\n📁 Archivos generados:")
    print(f"   • Actual: dashboards/{dashboard_actual.name}")
    print(f"   • Histórico: {dashboard_historico.relative_to(output_dir)}")
    
    print(f"\n📂 Estructura:")
    print(f"   output/dashboards/        ← Dashboards actuales")
    print(f"   output/historico/{nombre_contratista}/  ← Histórico por semana")
    print(f"   data/historico/{nombre_contratista}/    ← Respaldos Excel")
    
    print("\n💡 Abre el archivo HTML en tu navegador para ver el dashboard interactivo")
    print("="*70 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso cancelado por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        sys.exit(1)

