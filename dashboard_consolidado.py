#!/usr/bin/env python3
"""
Dashboard Consolidado - Múltiples Contratistas
===============================================

Combina datos de JAMAR y BAYSA para crear un dashboard consolidado.

Uso:
    python dashboard_consolidado.py
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
from pathlib import Path
from datetime import datetime
import logging
import sys

# ========== CONFIGURACIÓN DE LOGGING ==========

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cargar_configuracion(config_path: str = "config.yaml") -> dict:
    """Carga configuración desde YAML."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def cargar_datos_consolidados() -> pd.DataFrame:
    """Carga y combina datos normalizados de ambas contratistas."""
    
    archivos = {
        'JAMAR': 'data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv',
        'BAYSA': 'data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv'
    }
    
    dfs = []
    
    for contratista, archivo in archivos.items():
        if not Path(archivo).exists():
            logger.warning(f"⚠️  Archivo no encontrado: {archivo}")
            continue
        
        try:
            df = pd.read_csv(archivo, encoding='utf-8-sig')
            df['CONTRATISTA'] = contratista
            dfs.append(df)
            logger.info(f"✅ Cargado {archivo}: {len(df)} registros")
        except Exception as e:
            logger.error(f"❌ Error cargando {archivo}: {e}")
    
    if not dfs:
        logger.error("❌ No se cargaron datos de ninguna contratista")
        return pd.DataFrame()
    
    # Combinar dataframes
    df_consolidado = pd.concat(dfs, ignore_index=True)
    logger.info(f"📊 Datos consolidados: {len(df_consolidado)} registros de {df_consolidado['CONTRATISTA'].nunique()} contratistas")
    
    return df_consolidado

def calcular_metricas_consolidadas(df: pd.DataFrame) -> dict:
    """Calcula métricas consolidadas por contratista."""
    
    metricas = {
        'total_dossiers': len(df),
        'dossiers_liberados': (df['ESTATUS'] == 'LIBERADO').sum(),
        'peso_total': df['PESO'].sum(),
        'peso_liberado': df[df['ESTATUS'] == 'LIBERADO']['PESO'].sum(),
    }
    
    metricas['pct_liberado'] = (metricas['dossiers_liberados'] / metricas['total_dossiers'] * 100) if metricas['total_dossiers'] > 0 else 0
    metricas['pct_peso_liberado'] = (metricas['peso_liberado'] / metricas['peso_total'] * 100) if metricas['peso_total'] > 0 else 0
    
    # Métricas por contratista
    metricas['por_contratista'] = {}
    for contratista in df['CONTRATISTA'].unique():
        df_contr = df[df['CONTRATISTA'] == contratista]
        metricas['por_contratista'][contratista] = {
            'total': len(df_contr),
            'liberados': (df_contr['ESTATUS'] == 'LIBERADO').sum(),
            'peso_total': df_contr['PESO'].sum(),
            'peso_liberado': df_contr[df_contr['ESTATUS'] == 'LIBERADO']['PESO'].sum(),
        }
        m = metricas['por_contratista'][contratista]
        m['pct_liberado'] = (m['liberados'] / m['total'] * 100) if m['total'] > 0 else 0
        m['pct_peso'] = (m['peso_liberado'] / m['peso_total'] * 100) if m['peso_total'] > 0 else 0
    
    return metricas

def calcular_distribucion_consolidada(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribución de estatus consolidada (sin separación por contratista)."""
    
    return (
        df.groupby(['ESTATUS'], dropna=False)
        .agg(
            CANTIDAD=('ESTATUS', 'count'),
            PESO=('PESO', 'sum')
        )
        .reset_index()
    )

def calcular_etapa_solo_consolidada(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribución por ETAPA consolidada (sin estatus)."""
    
    return (
        df.groupby(['ETAPA'], dropna=False)
        .agg(
            CANTIDAD=('ESTATUS', 'count'),
            PESO=('PESO', 'sum')
        )
        .reset_index()
        .sort_values('CANTIDAD', ascending=False)
    )

def calcular_etapa_consolidada(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribución por ETAPA y ESTATUS consolidada (sin contratista)."""
    
    return (
        df.groupby(['ETAPA', 'ESTATUS'], dropna=False)
        .agg(
            CANTIDAD=('ESTATUS', 'count'),
            PESO=('PESO', 'sum')
        )
        .reset_index()
    )

def generar_dashboard_consolidado(df: pd.DataFrame, config: dict) -> go.Figure:
    """Genera el dashboard consolidado con métricas totales sin separación por contratista."""
    
    tipo = config['dashboard'].get('tipografia', {})
    font_family = tipo.get('familia_principal', 'Segoe UI, Arial, sans-serif')
    grid_color = config['colores'].get('GRID', '#E5E5E5')
    texto_color = config['colores'].get('TEXTO_SECUNDARIO', '#6B6B6B')
    texto_principal = config['colores'].get('TEXTO_PRINCIPAL', '#2C2C2C')
    fondo_color = config['colores'].get('FONDO', '#FFFFFF')
    
    # Calcular métricas consolidadas
    metricas = calcular_metricas_consolidadas(df)
    df_dist = calcular_distribucion_consolidada(df)
    df_etapa_consolidated = calcular_etapa_solo_consolidada(df)
    df_etapa = calcular_etapa_consolidada(df)
    
    # Crear figura con subplots (3 filas: KPIs + Estatus + ETAPA)
    fig = make_subplots(
        rows=3, cols=2,
        row_heights=[0.20, 0.40, 0.40],
        column_widths=[0.5, 0.5],
        subplot_titles=('', '', '<b>Cantidad por Estatus</b>', '<b>Peso por Estatus</b>',
                       '<b>Cantidad por ETAPA</b>', '<b>Peso por ETAPA</b>'),
        specs=[
            [{'type': 'indicator'}, {'type': 'indicator'}],
            [{'type': 'bar'}, {'type': 'bar'}],
            [{'type': 'bar'}, {'type': 'bar'}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.15
    )
    
    # Row 1: KPIs Globales Consolidados
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=metricas['pct_liberado'],
        number={'suffix': "%", 'font': {'size': tipo.get('metricas_grandes', 24), 'color': config['colores']['LIBERADO']}},
        delta={'reference': 90, 'suffix': "% vs Meta"},
        title={'text': "<b>% Liberado<br>(Cantidad)</b>", 'font': {'size': tipo.get('subtitulos', 14)}},
        gauge={
            'axis': {'range': [0, 100], 'ticksuffix': '%'},
            'bar': {'color': config['colores']['LIBERADO']},
            'steps': [
                {'range': [0, 50], 'color': '#F0F0F0'},
                {'range': [50, 90], 'color': '#E0E0E0'},
                {'range': [90, 100], 'color': '#D0D0D0'}
            ]
        }
    ), row=1, col=1)
    
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=metricas['pct_peso_liberado'],
        number={'suffix': "%", 'font': {'size': tipo.get('metricas_grandes', 24), 'color': config['colores']['LIBERADO']}},
        delta={'reference': 90, 'suffix': "% vs Meta"},
        title={'text': "<b>% Liberado<br>(Peso)</b>", 'font': {'size': tipo.get('subtitulos', 14)}},
        gauge={
            'axis': {'range': [0, 100], 'ticksuffix': '%'},
            'bar': {'color': config['colores']['LIBERADO']},
            'steps': [
                {'range': [0, 50], 'color': '#F0F0F0'},
                {'range': [50, 90], 'color': '#E0E0E0'},
                {'range': [90, 100], 'color': '#D0D0D0'}
            ]
        }
    ), row=1, col=2)
    
    # Row 2: Gráficos consolidados por ESTATUS
    prefer_order = ['LIBERADO', 'PLANEADO', 'OBSERVADO', 'EN_REVISIÓN']
    
    # Cantidad por Estatus
    for estatus in prefer_order:
        df_est = df_dist[df_dist['ESTATUS'] == estatus]
        if df_est.empty:
            continue
        
        cantidad = df_est['CANTIDAD'].values[0]
        
        fig.add_trace(go.Bar(
            x=[estatus],
            y=[cantidad],
            name=estatus,
            marker=dict(color=config['colores'].get(estatus, '#999999')),
            text=[cantidad],
            textposition='auto',
            textfont=dict(color='white', size=tipo.get('valores_graficos', 12)),
            hovertemplate=f'<b>{estatus}</b><br>Cantidad: %{{y}}<extra></extra>',
            showlegend=False
        ), row=2, col=1)
    
    # Peso por Estatus
    for estatus in prefer_order:
        df_est = df_dist[df_dist['ESTATUS'] == estatus]
        if df_est.empty:
            continue
        
        peso = df_est['PESO'].values[0]
        
        fig.add_trace(go.Bar(
            x=[estatus],
            y=[peso],
            name=estatus,
            marker=dict(color=config['colores'].get(estatus, '#999999')),
            text=[f'{peso:,.0f}'],
            textposition='auto',
            textfont=dict(color='white', size=tipo.get('valores_graficos', 11)),
            hovertemplate=f'<b>{estatus}</b><br>Peso: %{{y:,.0f}} ton<extra></extra>',
            showlegend=False
        ), row=2, col=2)

    # Row 3: Gráficos por ETAPA (consolidado, sin separación por estatus)
    # Cantidad por ETAPA
    fig.add_trace(go.Bar(
        x=df_etapa_consolidated['ETAPA'],
        y=df_etapa_consolidated['CANTIDAD'],
        name='ETAPA',
        marker=dict(color='#4472C4'),
        text=df_etapa_consolidated['CANTIDAD'],
        textposition='auto',
        textfont=dict(color='white', size=tipo.get('valores_graficos', 11)),
        hovertemplate='<b>%{x}</b><br>Cantidad: %{y}<extra></extra>',
        showlegend=False
    ), row=3, col=1)
    
    # Peso por ETAPA
    fig.add_trace(go.Bar(
        x=df_etapa_consolidated['ETAPA'],
        y=df_etapa_consolidated['PESO'],
        name='ETAPA',
        marker=dict(color='#70AD47'),
        text=df_etapa_consolidated['PESO'].apply(lambda x: f'{x:,.0f}'),
        textposition='auto',
        textfont=dict(color='white', size=tipo.get('valores_graficos', 10)),
        hovertemplate='<b>%{x}</b><br>Peso: %{y:,.0f} ton<extra></extra>',
        showlegend=False
    ), row=3, col=2)
    
    # Layout
    subtitulo = f"Total: {metricas['total_dossiers']} dossieres | Liberados: {metricas['dossiers_liberados']} ({metricas['pct_liberado']:.1f}%) | Peso: {metricas['peso_total']:,.0f} ton | Peso Liberado: {metricas['peso_liberado']:,.0f} ton ({metricas['pct_peso_liberado']:.1f}%)"
    
    fig.update_layout(
        title={
            'text': f"<b>DASHBOARD CONSOLIDADO - JAMAR & BAYSA</b><br><sub>{subtitulo}</sub>",
            'x': 0.5, 'xanchor': 'center',
            'font': {'size': tipo.get('titulo_dashboard', 28), 'family': font_family, 'color': texto_principal}
        },
        height=1500,
        showlegend=False,
        barmode='stack',
        plot_bgcolor=fondo_color,
        paper_bgcolor=fondo_color,
        font=dict(family=font_family, size=tipo.get('etiquetas', 12), color=texto_principal),
        hovermode='closest',
        margin=dict(l=100, r=100, t=180, b=100)
    )
    
    # Actualizar ejes
    fig.update_xaxes(gridcolor=grid_color, tickfont=dict(color=texto_color, family=font_family))
    fig.update_yaxes(gridcolor=grid_color, tickfont=dict(color=texto_color, family=font_family))
    
    # Row 2: Estatus
    fig.update_xaxes(title_text="<b>ESTATUS</b>", row=2, col=1, title_font=dict(size=tipo.get('subtitulos', 14)))
    fig.update_xaxes(title_text="<b>ESTATUS</b>", row=2, col=2, title_font=dict(size=tipo.get('subtitulos', 14)))
    fig.update_yaxes(title_text="<b>Cantidad</b>", row=2, col=1, title_font=dict(size=tipo.get('subtitulos', 14)))
    fig.update_yaxes(title_text="<b>Peso (ton)</b>", row=2, col=2, title_font=dict(size=tipo.get('subtitulos', 14)))
    
    # Row 3: ETAPA
    fig.update_xaxes(title_text="<b>ETAPA</b>", row=3, col=1, title_font=dict(size=tipo.get('subtitulos', 14)))
    fig.update_xaxes(title_text="<b>ETAPA</b>", row=3, col=2, title_font=dict(size=tipo.get('subtitulos', 14)))
    fig.update_yaxes(title_text="<b>Cantidad</b>", row=3, col=1, title_font=dict(size=tipo.get('subtitulos', 14)))
    fig.update_yaxes(title_text="<b>Peso (ton)</b>", row=3, col=2, title_font=dict(size=tipo.get('subtitulos', 14)))
    
    return fig

def main():
    """Genera el dashboard consolidado."""
    
    print("\n" + "="*60)
    print("📊 DASHBOARD CONSOLIDADO - JAMAR & BAYSA")
    print("="*60)
    
    # Cargar configuración
    config = cargar_configuracion()
    
    # Cargar datos consolidados
    df = cargar_datos_consolidados()
    
    if df.empty:
        logger.error("❌ No hay datos para generar dashboard")
        return 1
    
    # Generar dashboard
    logger.info("🎨 Generando dashboard consolidado...")
    fig = generar_dashboard_consolidado(df, config)
    
    # Guardar HTML
    output_dir = Path(config['paths']['output_dir'])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = output_dir / f"dashboard_consolidado_{timestamp}.html"
    
    fig.write_html(str(html_file), config={'displayModeBar': True, 'displaylogo': False})
    logger.info(f"✅ Dashboard guardado: {html_file.name}")
    
    # Mostrar resumen
    metricas = calcular_metricas_consolidadas(df)
    
    print(f"\n{'='*60}")
    print("📋 RESUMEN CONSOLIDADO")
    print(f"{'='*60}")
    print(f"\nTotal Global:")
    print(f"  • Dossieres: {metricas['total_dossiers']}")
    print(f"  • Liberados: {metricas['dossiers_liberados']} ({metricas['pct_liberado']:.1f}%)")
    print(f"  • Peso Total: {metricas['peso_total']:,.0f} ton")
    print(f"  • Peso Liberado: {metricas['peso_liberado']:,.0f} ton ({metricas['pct_peso_liberado']:.1f}%)")
    
    print(f"\nPor Contratista:")
    for contr, m in metricas['por_contratista'].items():
        print(f"\n  {contr}:")
        print(f"    • Dossieres: {m['total']}")
        print(f"    • Liberados: {m['liberados']} ({m['pct_liberado']:.1f}%)")
        print(f"    • Peso Total: {m['peso_total']:,.0f} ton")
        print(f"    • Peso Liberado: {m['peso_liberado']:,.0f} ton ({m['pct_peso']:.1f}%)")
    
    print(f"\n{'='*60}")
    print(f"✅ Dashboard generado: {html_file.name}")
    print(f"{'='*60}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
