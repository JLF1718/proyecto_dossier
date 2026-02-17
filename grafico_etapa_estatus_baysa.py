import pandas as pd
import plotly.graph_objects as go

def crear_grafico_etapa_estatus_baysa(df: pd.DataFrame, config: dict) -> go.Figure:
    """
    Crea un gráfico de barras agrupadas por ETAPA y ESTATUS para BAYSA.
    """
    # Filtrar datos de BAYSA
    df_baysa = df[df['CONTRATISTA'] == 'BAYSA'].copy()
    if df_baysa.empty:
        return None

    # Usar las etapas en el orden que aparecen en el DataFrame original
    etapas = df_baysa['ETAPA'].drop_duplicates().tolist()
    # Agrupar por ETAPA y ESTATUS (solo para totales)
    df_grouped = (
        df_baysa.groupby(['ETAPA', 'ESTATUS'], dropna=False)
        .agg(CANTIDAD=('ESTATUS', 'count'))
        .reset_index()
    )
    estatuses = ['TOTALES', 'LIBERADO', 'OBSERVADO', 'EN REVISIÓN', 'PLANEADO']
    colores = {
        'TOTALES': '#444',  # Gris más oscuro
        'LIBERADO': config['colores'].get('LIBERADO', '#0F7C3F'),
        'OBSERVADO': config['colores'].get('OBSERVADO', '#D0021B'),
        'EN REVISIÓN': config['colores'].get('EN_REVISIÓN', '#F5A623'),
        'PLANEADO': config['colores'].get('PLANEADO', '#808080'),
    }
    # Calcular totales por etapa
    totales = df_baysa.groupby('ETAPA', dropna=False)['ESTATUS'].count().reindex(etapas, fill_value=0)
    # Crear figura
    fig = go.Figure()
    # TOTALES (fondo gris, opacidad baja) con etiquetas de datos
    totales_labels = [f"<b><span style='color:black'>{val}</span></b><br><b><span style='color:black'>100%</span></b>" if val > 0 else "" for val in totales.values]
    fig.add_trace(go.Bar(
        x=etapas,
        y=totales.values,
        name='TOTALES',
        marker=dict(color=colores['TOTALES']),
        opacity=0.18,
        text=totales_labels,
        textposition='outside',
        textfont=dict(size=13, color='black')
    ))
    # Barras por estatus con etiquetas de datos y porcentajes
    for estatus in estatuses[1:]:
        # Normalizar espacios y tildes para evitar errores de coincidencia
        estatus_norm = estatus.strip().upper().replace('Í', 'I').replace('Ó', 'O').replace('É', 'E').replace('Á', 'A').replace('Ú', 'U')
        y_vals = []
        for etapa in etapas:
            # Buscar coincidencia flexible en el DataFrame original, no agrupado, para evitar errores de agrupación
            match = df_baysa[(df_baysa['ETAPA'].astype(str).str.strip().str.upper() == str(etapa).strip().upper()) & (df_baysa['ESTATUS'].str.strip().str.upper().str.replace('Í', 'I').str.replace('Ó', 'O').str.replace('É', 'E').str.replace('Á', 'A').str.replace('Ú', 'U') == estatus_norm)]
            y_vals.append(len(match))
        # Calcular porcentajes respecto al total de cada etapa
        pct_vals = [
            (y / totales[etapa] * 100) if totales[etapa] > 0 else 0
            for y, etapa in zip(y_vals, etapas)
        ]
        # Etiqueta: valor + salto de línea + porcentaje
        text_labels = [
            f"{y}<br>{pct:.1f}%" for y, pct in zip(y_vals, pct_vals)
        ]
        # Forzar visibilidad de la barra y etiqueta de EN REVISIÓN
        if estatus == 'EN REVISIÓN':
            fig.add_trace(go.Bar(
                x=etapas,
                y=y_vals,
                name=estatus,
                marker=dict(color='#FFC300', line=dict(color='#B8860B', width=2)),
                text=text_labels,
                textposition='outside',
                textfont=dict(size=14, color='black'),
                opacity=1.0
            ))
        else:
            fig.add_trace(go.Bar(
                x=etapas,
                y=y_vals,
                name=estatus,
                marker=dict(color=colores[estatus]),
                text=text_labels,
                textposition='auto',
                textfont=dict(size=12, color='black')
            ))
    # Layout
    # Ajustar el rango del eje Y para evitar que la etiqueta de ETAPA_1 se corte
    max_total = max(totales.values)
    fig.update_layout(
        title={'text': '<b>Dossieres por Etapa y Estatus - BAYSA</b>', 'x': 0.5},
        xaxis={'title': {'text': 'Etapa'}},
        yaxis={
            'title': None,
            'showticklabels': False,
            'showgrid': False,
            'zeroline': False,
            'visible': False,
            'range': [0, max_total * 1.18]
        },
        barmode='group',
        bargap=0.18,
        height=400,
        plot_bgcolor='#fff',
        paper_bgcolor='#fff',
        font=dict(family='Segoe UI, Arial, sans-serif'),
        legend=dict(
            title='',
            orientation='h',
            yanchor='bottom',
            y=-0.22,
            xanchor='center',
            x=0.5,
            font=dict(size=13)
        ),
        margin=dict(l=30, r=30, t=60, b=70)
    )
    return fig
