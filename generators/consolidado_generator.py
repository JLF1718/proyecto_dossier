import os
"""
Dashboard Consolidado - Múltiples Contratistas
===============================================

Combina datos de JAMAR y BAYSA para crear un dashboard consolidado.

Uso:
    python dashboard_consolidado.py
"""
from pathlib import Path
import unicodedata
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
from pathlib import Path
from datetime import datetime
import logging
import sys
from typing import Tuple
import re
import json

# Importar funciones core de métricas (ÚNICA FUENTE DE VERDAD)
# Compatible tanto al ejecutar como módulo (-m) como script directo.
try:
    from core.metricas import (
        calcular_metricas_consolidadas,
        calcular_peso_liberado,
        validar_consistencia_metricas,
        imprimir_metricas
    )

    from generators.utils_generator import (
        obtener_estructura_directorios,
        crear_directorios,
        solicitar_semana,
        guardar_archivos_consolidados,
        mostrar_resumen_archivos,
        PLOTLY_CONFIG_INTERACTIVE
    )
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from core.metricas import (
        calcular_metricas_consolidadas,
        calcular_peso_liberado,
        validar_consistencia_metricas,
        imprimir_metricas
    )

    from generators.utils_generator import (
        obtener_estructura_directorios,
        crear_directorios,
        solicitar_semana,
        guardar_archivos_consolidados,
        mostrar_resumen_archivos,
        PLOTLY_CONFIG_INTERACTIVE
    )

# ====== BLINDAJE UTF-8 (colócalo AQUÍ) ======
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ========== CONFIGURACIÓN DE LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generar_bloques_liberados_html_json_desde_df(df: pd.DataFrame, out_dir: Path) -> tuple[Path, Path]:
    """
    Genera:
      - output/exports/bloques_liberados.json
      - output/exports/bloques_liberados.html

    Columnas en HTML: Contratista | Etapa | Bloque | Peso (ton)
    Agrega fila final: TOTALES | <conteo_etapas> | <conteo_bloques> | <suma_peso_ton>
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    req = {"ESTATUS", "BLOQUE", "PESO", "CONTRATISTA", "ETAPA"}
    faltantes = sorted(list(req - set(df.columns)))
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas para exportar bloques liberados: {faltantes}")

    # --- Base liberados ---
    dfx = df.copy()
    dfx["PESO"] = pd.to_numeric(dfx["PESO"], errors="coerce").fillna(0)

    liberados = dfx[dfx["ESTATUS"] == "LIBERADO"][["CONTRATISTA", "ETAPA", "BLOQUE", "PESO"]].copy()

    # Agrupa por bloque para evitar duplicados por filas (robusto)
    liberados = (
        liberados
        .groupby(["CONTRATISTA", "ETAPA", "BLOQUE"], as_index=False)["PESO"]
        .sum()
    )

    # --- Normalizar ETAPA a formato canónico ETAPA_01..ETAPA_99 / SIN_ETAPA ---
    def canon_etapa(v: object) -> str:
        s = "" if pd.isna(v) else str(v)
        s = s.strip().upper().replace(" ", "_").replace("-", "_")
        if not s or s in {"NAN", "NONE"}:
            return "SIN_ETAPA"
        if "SIN" in s and "ETAPA" in s:
            return "SIN_ETAPA"
        m = re.search(r"(\d{1,2})", s)
        if m:
            return f"ETAPA_{int(m.group(1)):02d}"
        return s

    liberados["ETAPA"] = liberados["ETAPA"].apply(canon_etapa)

    # Convierte a ton (asumiendo que PESO viene en kg)
    liberados["PESO"] = liberados["PESO"] / 1000.0

    # Orden (opcional pero profesional): Contratista, Etapa, Bloque
    liberados = liberados.sort_values(["CONTRATISTA", "ETAPA", "BLOQUE"], kind="stable").reset_index(drop=True)

    # --- Totales ---
    total_bloques = int(len(liberados))
    total_peso_ton = float(liberados["PESO"].sum())

    # --- Conteo etapas (ya en canónico) ---
    etapas_set = set(liberados["ETAPA"].astype(str).tolist())

    # Cuenta ETAPA_01..ETAPA_04 (ajusta rango si luego agregas más etapas)
    conteo_etapas = sum(1 for n in range(1, 5) if f"ETAPA_{n:02d}" in etapas_set)
    if "SIN_ETAPA" in etapas_set:
        conteo_etapas += 1

    # --- JSON ---
    json_path = out_dir / "bloques_liberados.json"
    json_data = liberados.to_dict(orient="records")
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- HTML (fila TOTALES al final, SIEMPRE) ---
    def fila_html(contratista: str, etapa: str, bloque: str, peso: float, cls: str = "") -> str:
        c = f" class='{cls}'" if cls else ""
        return f"<tr{c}><td>{contratista}</td><td>{etapa}</td><td>{bloque}</td><td>{peso:.2f}</td></tr>"

    rows = []
    for r in liberados.itertuples(index=False):
        rows.append(fila_html(str(r.CONTRATISTA), str(r.ETAPA), str(r.BLOQUE), float(r.PESO)))

    # Fila final: TOTALES (al final del tbody)
    rows.append(fila_html("TOTALES", str(conteo_etapas), str(total_bloques), total_peso_ton, cls="totales"))

    html = f"""<!DOCTYPE html>
<html lang='es'>
<head>
  <meta charset='UTF-8'>
  <title>Lista de Bloques Liberados</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; background: #fafbfc; margin: 0; padding: 0; }}
    .container {{ max-width: 980px; margin: 40px auto; background: #fff; border-radius: 10px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.07); padding: 32px; }}
    h1 {{ text-align: center; margin-bottom: 0.2em; }}
    .total {{ text-align: center; font-size: 1.05em; margin-bottom: 1.5em; color: #0F7C3F; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 0.5em; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: center; }}
    th {{ background: #4A4A4A; color: #fff; font-size: 1.0em; }}
    tr:nth-child(even) {{ background: #f8f9fa; }}
    tr.totales td {{ font-weight: 700; background: #FFF6EA; border-top: 2px solid #F6A623; }}
  </style>
</head>
<body>
  <div class='container'>
    <h1>Lista de Bloques Liberados</h1>
    <div class='total'>Total de bloques liberados: <b>{total_bloques}</b></div>

    <table id='tabla-bloques'>
      <thead>
        <tr>
          <th>Contratista</th>
          <th>Etapa</th>
          <th>Bloque</th>
          <th>Peso (ton)</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    html_path = out_dir / "bloques_liberados.html"
    html_path.write_text(html, encoding="utf-8")

    return json_path, html_path


def _norm_txt(x: object) -> str:
    """Trim + uppercase + quita acentos + colapsa espacios."""
    s = "" if pd.isna(x) else str(x)
    s = s.strip().upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # sin acentos
    s = re.sub(r"\s+", " ", s)
    return s

def normalizar_peso(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura PESO numérico (kg)."""
    if 'PESO' in df.columns:
        df['PESO'] = pd.to_numeric(df['PESO'], errors="coerce").fillna(0)
    return df

def normalizar_estatus(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Canoniza ESTATUS usando config.yaml (sin hardcode):
    Lee normalizacion_estatus del YAML y convierte alias -> canónico.
    """
    if 'ESTATUS' not in df.columns:
        return df

    mapa = config.get("normalizacion_estatus", {}) or {}

    # Construir diccionario inverso alias->canon
    alias_to_canon = {}
    for canon, aliases in mapa.items():
        if not aliases:
            continue
        for a in aliases:
            key = _norm_txt(a).replace("-", " ").replace("_", " ")
            key = re.sub(r"\s+", " ", key).strip()
            alias_to_canon[key] = canon

        canon_key = _norm_txt(canon).replace("-", " ").replace("_", " ")
        canon_key = re.sub(r"\s+", " ", canon_key).strip()
        alias_to_canon[canon_key] = canon

    canon_default = "PLANEADO"

    def canonizar(v: object) -> str:
        t = _norm_txt(v).replace("-", " ").replace("_", " ")
        t = re.sub(r"\s+", " ", t).strip()

        if t in alias_to_canon:
            return alias_to_canon[t]

        # fallback: si trae "REV" y EN_REVISIÓN existe en el YAML
        if "REV" in t and "EN_REVISIÓN" in mapa:
            return "EN_REVISIÓN"

        return canon_default

    df['ESTATUS'] = df['ESTATUS'].apply(canonizar)
    return df

def cargar_configuracion(config_path: str = "config.yaml") -> dict:
    """Carga configuración desde YAML."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def cargar_datos_consolidados(config: dict) -> pd.DataFrame:

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
            # Intentar diferentes codificaciones
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            for enc in encodings:
                try:
                    df = pd.read_csv(archivo, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                raise ValueError("No se pudo leer el archivo CSV con ninguna codificación soportada")
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
    
    # Normalizar nombre de columna CONTRATISTA (puede venir como 'Contratista' después de concat)
    if 'Contratista' in df_consolidado.columns and 'CONTRATISTA' not in df_consolidado.columns:
        df_consolidado.rename(columns={'Contratista': 'CONTRATISTA'}, inplace=True)
    elif 'contratista' in df_consolidado.columns and 'CONTRATISTA' not in df_consolidado.columns:
        df_consolidado.rename(columns={'contratista': 'CONTRATISTA'}, inplace=True)
    
    logger.info(f"📊 Datos consolidados: {len(df_consolidado)} registros de {df_consolidado['CONTRATISTA'].nunique()} contratistas")
    
        # Normalizaciones críticas (sin hardcode)
    df_consolidado = normalizar_peso(df_consolidado)
    df_consolidado = normalizar_estatus(df_consolidado, config)

    # Log de control para validar EN_REVISIÓN
    try:
        logger.info(f"📌 Conteo por estatus (post-normalización): {df_consolidado['ESTATUS'].value_counts().to_dict()}")
    except Exception:
        pass

    return df_consolidado

# Las funciones de cálculo de métricas ahora están en metricas_core.py
# para asegurar consistencia entre dashboard.py y dashboard_consolidado.py
# Ver metricas_core.calcular_metricas_consolidadas() para la implementación

def calcular_distribucion_consolidada(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribución de estatus consolidada (sin separación por contratista)."""
    
    return (
        df.groupby(['ESTATUS'], dropna=False)
        .agg(
            CANTIDAD=('ESTATUS', 'count'),
            PESO=('PESO', lambda x: x.sum() / 1000)  # Convertir kg a ton
        )
        .reset_index()
    )

def calcular_etapa_solo_consolidada(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula distribución por ETAPA consolidada (sin estatus)."""
    
    return (
        df.groupby(['ETAPA'], dropna=False)
        .agg(
            CANTIDAD=('ESTATUS', 'count'),
            PESO=('PESO', lambda x: x.sum() / 1000)  # Convertir kg a ton
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
            PESO=('PESO', lambda x: x.sum() / 1000)  # Convertir kg a ton
        )
        .reset_index()
    )

def crear_tabla_resumen_ibcs(df: pd.DataFrame, config: dict, semana_corte: str = "S186") -> go.Figure:
    """Crea tabla de resumen de estatus por contratista con visualización IBCS."""
    
    # Preparar datos por contratista
    resumen_data = []
    
    for contratista in sorted(df['CONTRATISTA'].unique()):
        df_contr = df[df['CONTRATISTA'] == contratista]
        total = len(df_contr)
        
        # Contar por estatus
        estatus_counts = df_contr['ESTATUS'].value_counts().to_dict()
        liberados = estatus_counts.get('LIBERADO', 0)
        observados = estatus_counts.get('OBSERVADO', 0)
        en_revision = estatus_counts.get('EN_REVISIÓN', 0)
        planeados = estatus_counts.get('PLANEADO', 0)
        
        # Pesos (convertir kg a toneladas)
        peso_total = df_contr['PESO'].sum() / 1000
        peso_liberado = df_contr[df_contr['ESTATUS'] == 'LIBERADO']['PESO'].sum() / 1000
        
        # Porcentajes
        pct_liberado = (liberados / total * 100) if total > 0 else 0
        pct_observado = (observados / total * 100) if total > 0 else 0
        pct_revision = (en_revision / total * 100) if total > 0 else 0
        pct_planeado = (planeados / total * 100) if total > 0 else 0
        pct_peso_lib = (peso_liberado / peso_total * 100) if peso_total > 0 else 0
        
        resumen_data.append({
            'Contratista': contratista,
            'Total': total,
            'Liberados': liberados,
            'Pct_Liberados': pct_liberado,
            'Observados': observados,
            'Pct_Observados': pct_observado,
            'En_Revisión': en_revision,
            'Pct_Revisión': pct_revision,
            'Planeados': planeados,
            'Pct_Planeados': pct_planeado,
            'Peso_Total': peso_total,
            'Peso_Liberado': peso_liberado,
            'Pct_Peso_Lib': pct_peso_lib
        })
    
    # Añadir fila de totales
    total_global = len(df)
    liberados_global = (df['ESTATUS'] == 'LIBERADO').sum()
    observados_global = (df['ESTATUS'] == 'OBSERVADO').sum()
    revision_global = (df['ESTATUS'] == 'EN_REVISIÓN').sum()
    planeados_global = (df['ESTATUS'] == 'PLANEADO').sum()
    peso_total_global = df['PESO'].sum() / 1000
    peso_liberado_global = df[df['ESTATUS'] == 'LIBERADO']['PESO'].sum() / 1000
    
    resumen_data.append({
        'Contratista': '<b>TOTAL</b>',
        'Total': total_global,
        'Liberados': liberados_global,
        'Pct_Liberados': (liberados_global / total_global * 100) if total_global > 0 else 0,
        'Observados': observados_global,
        'Pct_Observados': (observados_global / total_global * 100) if total_global > 0 else 0,
        'En_Revisión': revision_global,
        'Pct_Revisión': (revision_global / total_global * 100) if total_global > 0 else 0,
        'Planeados': planeados_global,
        'Pct_Planeados': (planeados_global / total_global * 100) if total_global > 0 else 0,
        'Peso_Total': peso_total_global,
        'Peso_Liberado': peso_liberado_global,
        'Pct_Peso_Lib': (peso_liberado_global / peso_total_global * 100) if peso_total_global > 0 else 0
    })
    
    df_resumen = pd.DataFrame(resumen_data)
    
    # Crear figura de tabla IBCS
    tipo = config['dashboard'].get('tipografia', {})
    font_family = tipo.get('familia_principal', 'Segoe UI, Arial, sans-serif')
    
    # Colores de los minigráficos - usar colores del proyecto
    col_liberado = config['colores'].get('LIBERADO', '#4CAF50')
    col_observado = config['colores'].get('OBSERVADO', '#FFA726')
    col_revision = config['colores'].get('EN_REVISIÓN', '#42A5F5')
    col_planeado = config['colores'].get('PLANEADO', '#9E9E9E')
    
    # Preparar datos para la tabla con formato mejorado
    header_values = [
        '<b>Contratista</b>',
        '<b>Total<br>Dossieres</b>',
        '<b>Liberados</b>',
        '<b>Observados</b>',
        '<b>En Revisión</b>',
        '<b>Planeados</b>',
        '<b>Peso Total<br>(ton)</b>',
        '<b>Peso Liberado<br>(ton)</b>'
    ]
    
    # Función mejorada para crear barras IBCS con caracteres Unicode
    def crear_celda_ibcs(cantidad, pct, color):
        """Crea una celda con formato IBCS: cantidad, %, y barra visual con bloques Unicode."""
        if cantidad == 0:
            pct_text = "0.0%"
            barra = ""
        else:
            pct_text = f"{pct:.1f}%"
            # Crear barra usando caracteres de bloque Unicode
            num_bloques = int(pct / 5)  # 1 bloque por cada 5%
            barra = '█' * num_bloques if num_bloques > 0 else ''
        
        return f'<b>{cantidad}</b><br><span style="font-size:10px; color:#666;">{pct_text}</span><br><span style="color:{color}; font-size:14px;">{barra}</span>'
    
    def crear_celda_peso(peso, pct, color):
        """Crea celda de peso con formato IBCS."""
        peso_fmt = f"{peso:,.0f}"
        if peso == 0:
            pct_text = "0.0%"
            barra = ""
        else:
            pct_text = f"{pct:.1f}%"
            # Crear barra usando caracteres de bloque Unicode
            num_bloques = int(pct / 5)  # 1 bloque por cada 5%
            barra = '█' * num_bloques if num_bloques > 0 else ''
        
        return f'<b>{peso_fmt}</b><br><span style="font-size:10px; color:#666;">{pct_text}</span><br><span style="color:{color}; font-size:14px;">{barra}</span>'
    
    cell_values = [
        # Columna 1: Contratista
        df_resumen['Contratista'].tolist(),
        
        # Columna 2: Total Dossieres
        [f"<b>{int(total)}</b>" for total in df_resumen['Total'].tolist()],
        
        # Columna 3: Liberados con barra verde
        [crear_celda_ibcs(row['Liberados'], row['Pct_Liberados'], col_liberado) 
         for _, row in df_resumen.iterrows()],
        
        # Columna 4: Observados con barra naranja
        [crear_celda_ibcs(row['Observados'], row['Pct_Observados'], col_observado) 
         for _, row in df_resumen.iterrows()],
        
        # Columna 5: En Revisión con barra azul
        [crear_celda_ibcs(row['En_Revisión'], row['Pct_Revisión'], col_revision) 
         for _, row in df_resumen.iterrows()],
        
        # Columna 6: Planeados con barra gris
        [crear_celda_ibcs(row['Planeados'], row['Pct_Planeados'], col_planeado) 
         for _, row in df_resumen.iterrows()],
        
        # Columna 7: Peso Total
        [f"<b>{row['Peso_Total']:,.0f}</b>" for _, row in df_resumen.iterrows()],
        
        # Columna 8: Peso Liberado con barra
        [crear_celda_peso(row['Peso_Liberado'], row['Pct_Peso_Lib'], col_liberado) 
         for _, row in df_resumen.iterrows()]
    ]
    
    # Colores de fondo por fila (alternar blanco/gris claro, fondo destacado para totales)
    fill_colors = []
    font_colors = []
    font_sizes = []
    
    for i in range(len(df_resumen)):
        if i == len(df_resumen) - 1:  # Fila de totales
            fill_colors.append(['#E0E0E0'] * len(header_values))  # Gris claro
            font_colors.append(['#2C2C2C'] * len(header_values))  # Gris muy oscuro
            font_sizes.append([13] * len(header_values))
        elif i % 2 == 0:
            fill_colors.append(['#FFFFFF'] * len(header_values))
            font_colors.append(['#2C2C2C'] * len(header_values))
            font_sizes.append([12] * len(header_values))
        else:
            fill_colors.append(['#F8F9FA'] * len(header_values))
            font_colors.append(['#2C2C2C'] * len(header_values))
            font_sizes.append([12] * len(header_values))
    
    # Transponer para formato de Plotly
    fill_colors_transposed = [[fill_colors[row][col] for row in range(len(fill_colors))] 
                              for col in range(len(header_values))]
    font_colors_transposed = [[font_colors[row][col] for row in range(len(font_colors))] 
                              for col in range(len(header_values))]
    
    fig = go.Figure(data=[go.Table(
        columnwidth=[100, 80, 120, 120, 120, 120, 100, 130],  # Anchos optimizados para barras
        header=dict(
            values=header_values,
            fill_color='#4A4A4A',  # Gris oscuro para encabezados
            font=dict(color='white', size=13, family=font_family),
            align=['left', 'center', 'left', 'left', 'left', 'left', 'right', 'left'],
            height=45,
            line=dict(color='#3A3A3A', width=1)  # Borde gris oscuro
        ),
        cells=dict(
            values=cell_values,
            fill_color=fill_colors_transposed,
            font=dict(
                color=font_colors_transposed,
                size=12,
                family=font_family
            ),
            align=['left', 'center', 'left', 'left', 'left', 'left', 'right', 'left'],
            height=75,  # Altura aumentada para acomodar las barras
            line=dict(color='#E0E0E0', width=0.5)
        )
    )])
    
    fig.update_layout(
        title=dict(
            text=f'<b>Resumen de Estatus por Contratista (Semana: {semana_corte})</b><br><span style="font-size:11px; color:#666;">Las barras representan el porcentaje respecto al total de cada contratista</span>',
            x=0.5,
            xanchor='center',
            font=dict(size=18, family=font_family, color='#2C2C2C')  # Gris oscuro
        ),
        height=300,
        margin=dict(l=30, r=30, t=60, b=70, pad=0),

        paper_bgcolor='white'
    )
    
    return fig

def crear_tabla_individual_contratista(
    df: pd.DataFrame,
    contratista: str,
    config: dict,
    semana_corte: str = "S186",
    include_nota_descarga: bool = True,
) -> go.Figure:
    """Crea tabla IBCS detallada para un contratista individual."""
    
    # Filtrar datos del contratista
    df_contr = df[df['CONTRATISTA'] == contratista].copy()
    
    if df_contr.empty:
        logger.warning(f"⚠️  No hay datos para {contratista}")
        return None
    
    tipo = config['dashboard'].get('tipografia', {})
    font_family = tipo.get('familia_principal', 'Segoe UI, Arial, sans-serif')
    
    # Colores de los minigráficos
    col_liberado = config['colores'].get('LIBERADO', '#4CAF50')
    col_observado = config['colores'].get('OBSERVADO', '#FFA726')
    col_revision = config['colores'].get('EN_REVISIÓN', '#42A5F5')
    col_planeado = config['colores'].get('PLANEADO', '#9E9E9E')
    
    # Calcular métricas por estatus
    total = len(df_contr)
    estatus_counts = df_contr['ESTATUS'].value_counts().to_dict()
    
    liberados = estatus_counts.get('LIBERADO', 0)
    observados = estatus_counts.get('OBSERVADO', 0)
    en_revision = estatus_counts.get('EN_REVISIÓN', 0)
    planeados = estatus_counts.get('PLANEADO', 0)
    
    # Pesos (convertir kg a toneladas)
    peso_total = df_contr['PESO'].sum() / 1000
    peso_liberado = df_contr[df_contr['ESTATUS'] == 'LIBERADO']['PESO'].sum() / 1000
    peso_observado = df_contr[df_contr['ESTATUS'] == 'OBSERVADO']['PESO'].sum() / 1000
    peso_revision = df_contr[df_contr['ESTATUS'] == 'EN_REVISIÓN']['PESO'].sum() / 1000
    peso_planeado = df_contr[df_contr['ESTATUS'] == 'PLANEADO']['PESO'].sum() / 1000
    
    # Porcentajes
    pct_liberado = (liberados / total * 100) if total > 0 else 0
    pct_observado = (observados / total * 100) if total > 0 else 0
    pct_revision = (en_revision / total * 100) if total > 0 else 0
    pct_planeado = (planeados / total * 100) if total > 0 else 0
    
    pct_peso_lib = (peso_liberado / peso_total * 100) if peso_total > 0 else 0
    pct_peso_obs = (peso_observado / peso_total * 100) if peso_total > 0 else 0
    pct_peso_rev = (peso_revision / peso_total * 100) if peso_total > 0 else 0
    pct_peso_plan = (peso_planeado / peso_total * 100) if peso_total > 0 else 0
    
    # Crear funciones para formateo
    def crear_celda_ibcs(cantidad, pct, color):
        if cantidad == 0 or pct == 0:
            pct_text = "0.0%"
            barra = ""
        else:
            pct_text = f"{pct:.1f}%"
            num_bloques = max(1, int(pct / 5))  # Mínimo 1 bloque si pct > 0
            barra = '█' * num_bloques
        return f'<b>{cantidad}</b><br><span style="font-size:11px; color:#666;">{pct_text}</span><br><span style="color:{color}; font-size:16px;">{barra}</span>'
    
    def crear_celda_peso(peso, pct, color):
        peso_fmt = f"{peso:,.0f}"
        if peso == 0 or pct == 0:
            pct_text = "0.0%"
            barra = ""
        else:
            pct_text = f"{pct:.1f}%"
            num_bloques = max(1, int(pct / 5))  # Mínimo 1 bloque si pct > 0
            barra = '█' * num_bloques
        return f'<b>{peso_fmt}</b><br><span style="font-size:11px; color:#666;">{pct_text}</span><br><span style="color:{color}; font-size:16px;">{barra}</span>'
    
    # Datos de la tabla
    header_values = [
        '<b>Métrica</b>',
        '<b>Liberados</b>',
        '<b>Observados</b>',
        '<b>En Revisión</b>',
        '<b>Planeados</b>',
        '<b>Total</b>'
    ]
    
    cell_values = [
        ['<b>Cantidad Dossieres</b>', '<b>Peso (ton)</b>'],
        [
            crear_celda_ibcs(liberados, pct_liberado, col_liberado),
            crear_celda_peso(peso_liberado, pct_peso_lib, col_liberado)
        ],
        [
            crear_celda_ibcs(observados, pct_observado, col_observado),
            crear_celda_peso(peso_observado, pct_peso_obs, col_observado)
        ],
        [
            crear_celda_ibcs(en_revision, pct_revision, col_revision),
            crear_celda_peso(peso_revision, pct_peso_rev, col_revision)
        ],
        [
            crear_celda_ibcs(planeados, pct_planeado, col_planeado),
            crear_celda_peso(peso_planeado, pct_peso_plan, col_planeado)
        ],
        [
            f'<b>{total}</b>',
            f'<b>{peso_total:,.0f}</b>'
        ]
    ]
    
    # Colores de fondo
    fill_colors = [
        ['#FFFFFF', '#F8F9FA', '#FFFFFF', '#F8F9FA', '#FFFFFF', '#E0E0E0'],
        ['#FFFFFF', '#F8F9FA', '#FFFFFF', '#F8F9FA', '#FFFFFF', '#E0E0E0']
    ]
    
    font_colors = [
        ['#2C2C2C'] * 6,
        ['#2C2C2C'] * 6
    ]
    
    incluir_nota_baysa = contratista == 'BAYSA' and include_nota_descarga
    table_kwargs = {}
    if incluir_nota_baysa:
        table_kwargs['domain'] = dict(x=[0.0, 1.0], y=[0.34, 1.0])

    fig = go.Figure(data=[go.Table(
        columnwidth=[120, 130, 130, 130, 130, 100],
        header=dict(
            values=header_values,
            fill_color='#4A4A4A',
            font=dict(color='white', size=14, family=font_family),
            align=['left', 'left', 'left', 'left', 'left', 'center'],
            height=45,
            line=dict(color='#3A3A3A', width=1)
        ),
        cells=dict(
            values=cell_values,
            fill_color=fill_colors,
            font=dict(
                color=font_colors,
                size=13,
                family=font_family
            ),
            align=['left', 'left', 'left', 'left', 'left', 'center'],
            height=80,
            line=dict(color='#E0E0E0', width=0.5)
        ),
        **table_kwargs
    )])

    layout_kwargs = dict(
        title=dict(
            text=f'<b>Resumen - {contratista} (Semana: {semana_corte})</b><br><span style="font-size:12px; color:#666;">Total: {total} dossieres | Peso Total: {peso_total:,.0f} ton</span>',
            x=0.5,
            xanchor='center',
            font=dict(size=20, family=font_family, color='#2C2C2C')
        ),
        height=320,
        margin=dict(l=30, r=30, t=60, b=70, pad=0),
        paper_bgcolor='white'
    )

    if incluir_nota_baysa:
        layout_kwargs['height'] = 520
        layout_kwargs['margin'] = dict(l=30, r=30, t=60, b=20, pad=0)

    fig.update_layout(**layout_kwargs)

    if incluir_nota_baysa:
        fig.add_shape(
            type='rect',
            xref='paper',
            yref='paper',
            x0=0.0,
            x1=1.0,
            y0=0.0,
            y1=0.25,
            line=dict(color='#F0D9B5', width=1),
            fillcolor='#FFF6EA',
            layer='below'
        )
        fig.add_shape(
            type='rect',
            xref='paper',
            yref='paper',
            x0=0.0,
            x1=0.006,
            y0=0.0,
            y1=0.25,
            line=dict(color='#F6A623', width=0),
            fillcolor='#F6A623',
            layer='above'
        )
        fig.add_annotation(
            xref='paper',
            yref='paper',
            x=0.015,
            y=0.225,
            xanchor='left',
            yanchor='top',
            showarrow=False,
            align='left',
            font=dict(size=17, family=font_family, color='#E67C00'),
            text='<b>Nota Ejecutiva: Observaciones Críticas</b>'
        )
        fig.add_annotation(
            xref='paper',
            yref='paper',
            x=0.015,
            y=0.155,
            xanchor='left',
            yanchor='top',
            showarrow=False,
            align='left',
            font=dict(size=12, family=font_family, color='#222'),
            text='Las observaciones identificadas en la columna OBSERVADO se concentran principalmente en tres categorías críticas<br><b>TOPOGRAFÍA</b>, <b>PLANOS AS-BUILT</b> y <b>PRODUCTO TERMINADO</b>. La ausencia de estas secciones compromete la verificación de trazabilidad<br>y cumplimiento normativo, representando un riesgo de no conformidad en auditorías y revisiones de calidad.'
        )
        fig.add_annotation(
            xref='paper',
            yref='paper',
            x=0.015,
            y=0.055,
            xanchor='left',
            yanchor='top',
            showarrow=False,
            align='left',
            font=dict(size=12, family=font_family, color='#222'),
            text='<b>Peso (ton):</b> El indicador registra el peso total del bloque, pendiente la homologación de entregas parciales una vez se integren los registros<br>del dossier para asegurar la integridad metrológica de la medición.'
        )
    
    return fig


def crear_tabla_entregas_baysa(df: pd.DataFrame, config: dict) -> go.Figure:
    """
    Crea tabla IBCS con datos de entrega programada para BAYSA.
    Muestra dossieres programados para entregar y su avance de liberación.
    """
    from datetime import datetime, timedelta
    
    def calcular_rango_semana(codigo_semana: str, semana_base: str = "S185", fecha_inicio_base: str = "2026-01-10") -> str:
        """
        Calcula el rango de fechas (sábado a viernes) para una semana de proyecto.
        S185 inicia el 2026-01-10 (sábado).
        """
        try:
            num_semana = int(codigo_semana.replace('S', ''))
            num_base = int(semana_base.replace('S', ''))
            diferencia_semanas = num_semana - num_base
            fecha_base = datetime.strptime(fecha_inicio_base, "%Y-%m-%d")
            fecha_inicio = fecha_base + timedelta(weeks=diferencia_semanas)
            fecha_fin = fecha_inicio + timedelta(days=6)  # Sábado a viernes
            
            return f"{fecha_inicio.strftime('%d/%m/%y')} - {fecha_fin.strftime('%d/%m/%y')}"
        except:
            return ""
    
    # Verificar si existe columna ENTREGA
    if 'ENTREGA' not in df.columns:
        logger.warning("⚠️ Columna ENTREGA no encontrada, omitiendo tabla de entregas BAYSA")
        return None
    
    # Filtrar BAYSA con datos de ENTREGA
    df_filtrado = df[(df['CONTRATISTA'] == 'BAYSA') & 
                     (df['ENTREGA'].notna()) & 
                     (df['ENTREGA'] != '')].copy()
    
    if len(df_filtrado) == 0:
        return None
    

    # Calcular ambas columnas por separado y unirlas
    # Liberados: solo los que tienen estatus LIBERADO
    def contar_liberados(estatus_col):
        return (estatus_col == 'LIBERADO').sum()
    
    # Entregados: todos los que NO están en PLANEADO (incluye EN_REVISIÓN, OBSERVADO, LIBERADO)
    def contar_entregados(estatus_col):
        return (estatus_col != 'PLANEADO').sum()

    entregas_base = df_filtrado.groupby('ENTREGA').agg({
        'BLOQUE': 'count',
        'PESO': lambda x: x.sum() / 1000,
    })
    entregas_base['Liberados'] = df_filtrado.groupby('ENTREGA')['ESTATUS'].apply(contar_liberados)
    entregas_base['Entregados'] = df_filtrado.groupby('ENTREGA')['ESTATUS'].apply(contar_entregados)
    entregas_base = entregas_base.reset_index()
    entregas_base.columns = ['Semana', 'Planeados', 'Peso', 'Liberados', 'Entregados']
    entregas = entregas_base.sort_values('Semana')

    # Agregar fila de totales
    total_row = {
        'Semana': '<b>TOTAL</b>',
        'Planeados': entregas['Planeados'].sum(),
        'Peso': entregas['Peso'].sum(),
        'Liberados': entregas['Liberados'].sum(),
        'Entregados': entregas['Entregados'].sum()
    }
    entregas = pd.concat([entregas, pd.DataFrame([total_row])], ignore_index=True)
    
    # Configuración tipográfica
    tipo = config['dashboard'].get('tipografia', {})
    font_family = tipo.get('familia_principal', 'Segoe UI, Arial, sans-serif')
    
    # Colores
    col_planeado = config['colores'].get('PLANEADO', '#9E9E9E')
    col_liberado = config['colores'].get('LIBERADO', '#4CAF50')
    
    def crear_celda_cantidad(cantidad, pct, color):
        if cantidad == 0:
            return "0<br><span style='font-size:11px; color:#666;'>0.0%</span>"
        pct_text = f"{pct:.1f}%"
        num_bloques = max(1, int(pct / 5))
        barra = '█' * num_bloques
        return f'<b>{cantidad}</b><br><span style="font-size:11px; color:#666;">{pct_text}</span><br><span style="color:{color}; font-size:16px;">{barra}</span>'
    
    # Preparar datos (excluir fila TOTAL de las listas con visualización)
    datos_sin_total = entregas[:-1]  # Todas menos la última (TOTAL)
    

    total_planeados = entregas.iloc[-1]['Planeados']
    total_peso = entregas.iloc[-1]['Peso']
    total_liberados = entregas.iloc[-1]['Liberados']
    total_entregados = entregas.iloc[-1]['Entregados']

    semanas_vals = []
    planeados_vals = []
    peso_vals = []
    entregados_vals = []
    liberados_vals = []

    # Procesar filas de datos (sin TOTAL)
    for idx, row in datos_sin_total.iterrows():
        # Semana con rango de fechas
        rango_fechas = calcular_rango_semana(row["Semana"])
        semana_html = f'<b>{row["Semana"]}</b><br><span style="font-size:11px; color:#666;">{rango_fechas}</span>'
        semanas_vals.append(semana_html)
        # Planeados: solo mostrar cantidad sin barra
        planeados_vals.append(f'<b>{row["Planeados"]}</b>')
        peso_vals.append(f'<b>{row["Peso"]:,.0f}</b>')
        # Entregados: mostrar cantidad, porcentaje y barra de progreso (color planeado)
        total_semana = row['Planeados']
        pct_ent = (row['Entregados'] / total_semana * 100) if total_semana > 0 else 0
        entregados_vals.append(crear_celda_cantidad(row['Entregados'], pct_ent, col_planeado))
        # Liberados: mostrar cantidad, porcentaje y barra de progreso
        pct_lib = (row['Liberados'] / total_semana * 100) if total_semana > 0 else 0
        liberados_vals.append(crear_celda_cantidad(row['Liberados'], pct_lib, col_liberado))

    # Agregar fila TOTAL al final
    semanas_vals.append('<b>TOTAL</b>')
    planeados_vals.append(f'<b>{int(total_planeados)}</b>')
    peso_vals.append(f'<b>{total_peso:,.0f}</b>')
    pct_total_ent = (int(total_entregados) / int(total_planeados) * 100) if total_planeados > 0 else 0
    pct_total_lib = (int(total_liberados) / int(total_planeados) * 100) if total_planeados > 0 else 0
    entregados_vals.append(crear_celda_cantidad(int(total_entregados), pct_total_ent, col_planeado))
    liberados_vals.append(crear_celda_cantidad(int(total_liberados), pct_total_lib, col_liberado))

    # Crear figura con columna adicional Entregados
    fig = go.Figure(data=[go.Table(
        columnwidth=[120, 160, 180, 180, 180],
        header=dict(
            values=['<b>Semana<br>Entrega</b>', '<b>Dossieres<br>Planeados</b>', '<b>Peso Total<br>(ton)</b>', 
                    '<b>Entregados<br>(No Liberados)</b>', '<b>Liberados<br>(Avance)</b>'],
            fill_color='#4A4A4A',
            font=dict(color='white', size=14, family=font_family),
            align=['center', 'center', 'center', 'left', 'left'],
            height=45,
            line=dict(color='#3A3A3A', width=1)
        ),
        cells=dict(
            values=[semanas_vals, planeados_vals, peso_vals, entregados_vals, liberados_vals],
            fill_color=[
                ['#FFFFFF' if i < len(semanas_vals)-1 and i % 2 == 0 else '#F8F9FA' if i < len(semanas_vals)-1 else '#E0E0E0' 
                 for i in range(len(semanas_vals))] for _ in range(5)
            ],
            font=dict(color='#2C2C2C', size=13, family=font_family),
            align=['center', 'center', 'center', 'left', 'left'],
            height=75,
            line=dict(color='#E0E0E0', width=1)
        )
    )])

    # Calcular altura dinámica: encabezado (45) + título (90) + margen inferior (30) + filas (incluyendo TOTAL)
    num_filas = len(semanas_vals)  # Incluye la fila TOTAL
    altura_calculada = 90 + 45 + (num_filas * 75) + 30
    
    fig.update_layout(
        title=dict(
            text=f'<b>Plan de Entregas Pendientes - BAYSA</b><br><span style="font-size:12px; color:#666;">Dossieres Programados: {total_planeados} | Liberados: {total_liberados} ({pct_total_lib:.1f}%) | Entregados: {total_entregados} ({pct_total_ent:.1f}%) | Peso Total: {total_peso:,.0f} ton</span>',
            x=0.5,
            xanchor='center',
            font=dict(size=20, family=font_family, color='#2C2C2C')
        ),
        width=1300,
        height=altura_calculada,
        margin=dict(l=30, r=30, t=60, b=70, pad=0),

        paper_bgcolor='white',
    )
    # Centrar la tabla en el HTML exportado (solo para PDF/HTML)
    fig.update_layout(
        autosize=False,
        template=None,
    )
    return fig


def crear_gantt_entregas_baysa(df: pd.DataFrame, config: dict) -> go.Figure:
    """
    Crea diagrama de Gantt SVG escalable para entregas BAYSA.
    """
    from datetime import datetime, timedelta
    
    def semana_a_fecha(codigo_semana: str, semana_base: str = "S185", fecha_inicio_base: str = "2026-01-10") -> pd.Timestamp:
        """
        Convierte código de semana a fecha de inicio (sábado).
        S185 inicia el 2026-01-10 (sábado).
        """
        try:
            num_semana = int(codigo_semana.replace('S', ''))
            num_base = int(semana_base.replace('S', ''))
            diferencia_semanas = num_semana - num_base
            
            fecha_base = datetime.strptime(fecha_inicio_base, "%Y-%m-%d")
            fecha_inicio = fecha_base + timedelta(weeks=diferencia_semanas)
            
            return pd.Timestamp(fecha_inicio)
        except:
            return pd.Timestamp('2026-01-10')
    
    # Verificar si existe columna ENTREGA
    if 'ENTREGA' not in df.columns:
        logger.warning("⚠️ Columna ENTREGA no encontrada, omitiendo Gantt de entregas BAYSA")
        return None
    
    # Filtrar datos
    df_filtrado = df[(df['CONTRATISTA'] == 'BAYSA') & 
                     (df['ENTREGA'].notna()) & 
                     (df['ENTREGA'] != '')].copy()
    
    if len(df_filtrado) == 0:
        return None
    
    # Configuración
    tipo = config['dashboard'].get('tipografia', {})
    font_family = tipo.get('familia_principal', 'Segoe UI, Arial, sans-serif')
    col_observado = config['colores'].get('OBSERVADO', '#FFA726')
    col_revision = config['colores'].get('EN_REVISIÓN', '#42A5F5')
    col_planeado = config['colores'].get('PLANEADO', '#9E9E9E')
    col_liberado = config['colores'].get('LIBERADO', '#4CAF50')
    
    # Preparar datos para Gantt
    gantt_data = []
    for idx, row in df_filtrado.iterrows():
        # Convertir semana a fecha (sábado de inicio de semana)
        try:
            if pd.notna(row['ENTREGA']) and str(row['ENTREGA']).startswith('S'):
                fecha_entrega = semana_a_fecha(str(row['ENTREGA']))
                
                # Determinar color según estatus
                if row['ESTATUS'] == 'LIBERADO':
                    color = col_liberado
                    estatus = 'LIBERADO'
                elif row['ESTATUS'] == 'OBSERVADO':
                    color = col_observado
                    estatus = 'OBSERVADO'
                elif row['ESTATUS'] == 'EN_REVISIÓN':
                    color = col_revision
                    estatus = 'EN REVISIÓN'
                else:  # PLANEADO u otros
                    color = col_planeado
                    estatus = 'PLANEADO'
                
                # Obtener nivel de revisión (si no existe, usar 0)
                nivel_revision = 0
                if 'No. REVISIÓN' in row.index:
                    try:
                        nivel_revision = int(row['No. REVISIÓN']) if pd.notna(row['No. REVISIÓN']) else 0
                    except:
                        nivel_revision = 0
                
                gantt_data.append({
                    'Bloque': row['BLOQUE'],
                    'Fecha_Entrega': fecha_entrega,
                    'Estatus': estatus,
                    'Color': color,
                    'Peso': row['PESO'] / 1000,  # Convertir kg a ton
                    'Semana': row['ENTREGA'],
                    'Nivel_Revision': nivel_revision
                })
        except:
            continue
    
    if len(gantt_data) == 0:
        return None
    
    df_gantt = pd.DataFrame(gantt_data)
    # Ordenar por fecha de entrega (mayor a menor) para que S186 aparezca arriba en el Gantt
    df_gantt = df_gantt.sort_values(['Fecha_Entrega', 'Bloque'], ascending=[False, False])
    
    # Crear figura Gantt
    fig = go.Figure()
    
    for idx, row in df_gantt.iterrows():
        # Preparar texto para mostrar en la barra
        if row['Nivel_Revision'] > 0:
            texto_barra = f"{row['Semana']}<br>{row['Peso']:,.0f} ton<br>Rev: {row['Nivel_Revision']}"
        else:
            texto_barra = f"{row['Semana']}<br>{row['Peso']:,.0f} ton"
        
        fig.add_trace(go.Bar(
            name=row['Estatus'],
            x=[row['Fecha_Entrega']],
            y=[row['Bloque']],
            orientation='h',
            marker=dict(color=row['Color'], line=dict(color='#2C2C2C', width=0.5)),
            text=texto_barra,
            textposition='inside',
            textfont=dict(size=10, family=font_family, color='white'),
            hovertemplate=f"<b>{row['Bloque']}</b><br>Entrega: {row['Semana']}<br>Fecha: {row['Fecha_Entrega'].strftime('%d/%m/%y')}<br>Peso: {row['Peso']:,.0f} ton<br>Estatus: {row['Estatus']}<br>Revisión: {row['Nivel_Revision']}<extra></extra>",
            showlegend=False
        ))
    
    fig.update_layout(
        title=dict(
            text='<b>Gantt de Entregas Programadas - BAYSA</b><br><span style="font-size:12px; color:#666;">Cronograma de Entregas por Semana de Proyecto</span>',
            x=0.5,
            xanchor='center',
            font=dict(size=20, family=font_family, color='#2C2C2C')
        ),
        xaxis=dict(
            title=dict(
                text='<b>Semana de Entrega (Fecha Inicio)</b>',
                font=dict(size=14, family=font_family)
            ),
            tickfont=dict(size=12, family=font_family),
            gridcolor='#E0E0E0',
            showgrid=True,
            tickformat='%d/%m/%y'
        ),
        yaxis=dict(
            title=dict(
                text='<b>Bloque</b>',
                font=dict(size=14, family=font_family)
            ),
            tickfont=dict(size=10, family=font_family),
            categoryorder='array',
            categoryarray=df_gantt['Bloque'].tolist()
        ),
        height=max(600, len(df_gantt) * 25),
        margin=dict(l=30, r=30, t=60, b=70, pad=0),
        paper_bgcolor='white',
        plot_bgcolor='#F8F9FA',
        barmode='overlay',
        bargap=0.2
    )
    
    return fig


def generar_dashboard_consolidado(df: pd.DataFrame, config: dict, semana_corte: str = "S186") -> Tuple[go.Figure, go.Figure]:
    """Genera el dashboard consolidado con métricas totales y tabla IBCS."""
    
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
    
    # Crear tabla IBCS
    fig_tabla = crear_tabla_resumen_ibcs(df, config, semana_corte)
    
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
    subtitulo = f"<b style='color:#0F7C3F'>📅 SEMANA DE CORTE: {semana_corte}</b> | Total: {metricas['total_dossiers']} dossieres | Liberados: {metricas['dossiers_liberados']} ({metricas['pct_liberado']:.1f}%) | Peso: {metricas['peso_total']:,.0f} ton | Peso Liberado: {metricas['peso_liberado']:,.0f} ton ({metricas['pct_peso_liberado']:.1f}%)"
    
    fig.update_layout(
        title={
            'text': f"<b>DASHBOARD CONSOLIDADO - JAMAR & BAYSA</b><br><span style='font-size:14px'>{subtitulo}</span>",
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
        margin=dict(l=30, r=30, t=60, b=70, pad=0),

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
    
    return fig, fig_tabla

def obtener_semana():
    semana = os.environ.get("SEMANA_CORTE")
    if semana:
        print(f"Usando semana de entorno: {semana}")
        return semana.strip().upper()
    else:
        return input("📅 Ingresa el número de semana (ej: S183): ").strip().upper()


def regenerar_poster_principal_baysa(semana_corte: str, output_dir: Path | None = None) -> Path | None:
    """Regenera solo el poster principal BAYSA sin ejecutar toda la corrida completa."""
    output_dir = output_dir or Path('output')
    config = cargar_configuracion()
    df = cargar_datos_consolidados(config)

    from grafico_etapa_estatus_baysa import crear_grafico_etapa_estatus_baysa

    df_baysa = df[df['CONTRATISTA'] == 'BAYSA']
    if df_baysa.empty:
        return None

    timestamp_simple = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_archivo = output_dir / 'tablas' / f"analisis_completo_baysa_{timestamp_simple}.html"
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)

    def _plotly_download_config(filename: str) -> dict:
        config_interactive = dict(PLOTLY_CONFIG_INTERACTIVE)
        config_interactive["toImageButtonOptions"] = dict(
            PLOTLY_CONFIG_INTERACTIVE.get("toImageButtonOptions", {})
        )
        config_interactive["toImageButtonOptions"]["filename"] = filename
        return config_interactive

    fig_baysa = crear_tabla_individual_contratista(df, 'BAYSA', config, semana_corte, include_nota_descarga=False)
    fig_grafico = crear_grafico_etapa_estatus_baysa(df_baysa, config)

    temp_html1 = ruta_archivo.with_suffix('.temp1.html')
    temp_html3 = ruta_archivo.with_suffix('.temp3.html')
    fig_baysa.write_html(
        str(temp_html1),
        include_plotlyjs='cdn',
        full_html=False,
        config=_plotly_download_config("resumen_baysa")
    )
    if fig_grafico is not None:
        fig_grafico.write_html(
            str(temp_html3),
            include_plotlyjs=False,
            full_html=False,
            config=_plotly_download_config("resumen_conteo_baysa")
        )

    nota_ejecutiva = '''
    <div style="background:#FFF6EA; border-left:4px solid #F6A623; padding:10px 18px; margin:12px 0 18px 0; font-family:Segoe UI,Arial,sans-serif;">
        <span style="font-size:17px; font-weight:bold; color:#E67C00; vertical-align:middle; display:inline-block;">
            <span style="font-size:1.3em; margin-right:7px; vertical-align:middle;">&#9888;</span> Nota Ejecutiva: Observaciones Críticas
        </span>
        <div style="font-size:14px; color:#222; margin-top:2px;">
        <p style="margin:0 0 8px 0;">Las observaciones identificadas en la columna OBSERVADO se concentran principalmente en tres categorías críticas para la trazabilidad del dossier: <b>TOPOGRAFÍA</b>, <b>PLANOS AS-BUILT</b> y <b>PRODUCTO TERMINADO</b>. La ausencia de estas secciones compromete directamente la verificación de trazabilidad y cumplimiento normativo, representando un riesgo de no conformidad en auditorías y revisiones de calidad.</p>
        <p style="margin:0;"><b>Peso (ton):</b> El indicador registra el peso total del bloque, pendiente la homologación de entregas parciales una vez se integren los registros del dossier para asegurar la integridad metrológica de la medición.</p>
        </div>
    </div>
    '''
    encabezado = '''
    <div style="text-align:center; margin-top:24px; margin-bottom:8px;">
        <span style="font-size:2.1em; font-weight:bold; color:#222; font-family:Segoe UI,Arial,sans-serif; vertical-align:middle;">
            <span style="vertical-align:middle;">&#128202;</span> Análisis Completo - BAYSA
        </span>
        <div style="font-size:1.08em; color:#444; margin-top:3px;">Resumen ejecutivo y cronograma</div>
    </div>
    '''

    with open(temp_html1, encoding='utf-8') as f:
        tabla1_html = f.read()
    grafico_html = ''
    if fig_grafico is not None:
        with open(temp_html3, encoding='utf-8') as f:
            grafico_html = f.read()

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><title>Análisis Completo BAYSA</title>')
        f.write('<style>body{background:#fafbfc;} .baysa-panel{max-width:1200px;margin:0 auto 6px auto;padding:0 0 0 0;background:#fff;border-radius:10px;box-shadow:0 2px 8px #0001;overflow:hidden;} .baysa-table{padding:18px 18px 0 18px; min-width:1050px; max-width:1150px;} .nota-ejecutiva-panel{margin:0;padding:0;border-radius:0 0 10px 10px;} .baysa-table .js-plotly-plot{overflow:visible!important;} .baysa-table .modebar{pointer-events:auto!important;} </style>')
        f.write('</head><body>')
        f.write(encabezado)
        f.write('<div style="max-width:1200px; margin:0 auto;">')
        f.write('<div class="baysa-panel">')
        f.write('<div class="baysa-table baysa-plot-interactive">')
        f.write(tabla1_html)
        f.write('</div>')
        f.write(nota_ejecutiva.replace('<div ', '<div class="nota-ejecutiva-panel" ', 1))
        f.write('</div>')
        if grafico_html:
            f.write('<div class="baysa-panel"><div class="baysa-table baysa-plot-interactive">')
            f.write(grafico_html)
            f.write('</div></div>')
        f.write('</div></body></html>')

    temp_html1.unlink(missing_ok=True)
    if temp_html3.exists():
        temp_html3.unlink(missing_ok=True)
    return ruta_archivo

def main():
    """Genera el dashboard consolidado."""
    
    # Definir output_dir antes de usarlo
    output_dir = Path('output')
    # Capturar semana de corte: SIEMPRE interactivo
    semana_corte = obtener_semana()
    if not re.fullmatch(r"S\d{1,4}", semana_corte):
        print(f"❌ Formato inválido: {semana_corte}. Usa, por ejemplo: S186")
        return 1
    # Preparar estructura de directorios
    dirs = obtener_estructura_directorios(output_dir)
    crear_directorios(dirs)

    # Mostrar estadísticas consolidadas
    config = cargar_configuracion()
    df = cargar_datos_consolidados(config)
    metricas = calcular_metricas_consolidadas(df)

    # Generar dashboard y tabla resumen
    fig_dashboard, fig_tabla_resumen = generar_dashboard_consolidado(df, config, semana_corte)

    # Generar tablas individuales por contratista
    tablas_individuales = {}
    for contratista in sorted(df['CONTRATISTA'].unique()):
        fig_tabla = crear_tabla_individual_contratista(df, contratista, config, semana_corte)
        if fig_tabla is not None:
            tablas_individuales[contratista] = fig_tabla


    # Guardar archivos consolidados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    rutas = guardar_archivos_consolidados(
        fig_dashboard=fig_dashboard,
        fig_tabla_resumen=fig_tabla_resumen,
        tablas_individuales=tablas_individuales,
        timestamp=timestamp,
        semana=semana_corte,
        dirs=dirs,
        df_consolidado=df
    )


    ruta_archivo = regenerar_poster_principal_baysa(semana_corte, output_dir=output_dir)
    if ruta_archivo is not None:
        print(f"✅ Tabla ejecutiva y gráfico BAYSA generados: {ruta_archivo}")

    print(f"{'='*60}")
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
        print(f"    • Dossieres: {m['total_dossiers']}")
        print(f"    • Liberados: {m['dossiers_liberados']} ({m['pct_liberado']:.1f}%)")
        print(f"    • Peso Total: {m['peso_total']:,.0f} ton")
        print(f"    • Peso Liberado: {m['peso_liberado']:,.0f} ton ({m['pct_peso_liberado']:.1f}%)")

    print(f"\n{'='*60}")
    print(f"\n{'='*60}")
    # Mostrar resumen usando la función unificada
    semana = semana_corte
    mostrar_resumen_archivos(
        rutas=rutas,
        output_dir=output_dir,
        semana=semana
    )

    # Export automático de bloques liberados en output/exports
    try:
        exports_dir = output_dir / "exports"
        json_path, html_path = generar_bloques_liberados_html_json_desde_df(df, exports_dir)
        print(f"✅ bloques_liberados.html generado: {html_path}")
        print(f"✅ bloques_liberados.json generado: {json_path}")

        # ===== ASSERTS (control de integridad) =====
        def _assert(cond: bool, msg: str):
            if not cond:
                raise AssertionError(msg)

        import re as _re

        def _canon_etapa(v: object) -> str:
            """
            Canoniza ETAPA:
            - Acepta ETAPA_1, ETAPA-1, ETAPA 1, ETAPA_01 -> ETAPA_01
            - SIN_ETAPA -> SIN_ETAPA
            """
            t = "" if pd.isna(v) else str(v)
            t = t.strip().upper().replace(" ", "_").replace("-", "_")
            if not t:
                return ""
            if t in {"SIN_ETAPA", "SINETAPA", "NA", "N/A"}:
                return "SIN_ETAPA"
            m = _re.match(r"^ETAPA_?(\d+)$", t)
            if m:
                return f"ETAPA_{int(m.group(1)):02d}"
            return t

        def _calc_expected(df_: pd.DataFrame):
            dfx = df_.copy()
            dfx["PESO"] = pd.to_numeric(dfx["PESO"], errors="coerce").fillna(0)

            lib = dfx[dfx["ESTATUS"] == "LIBERADO"][["CONTRATISTA", "ETAPA", "BLOQUE", "PESO"]].copy()
            lib = (
                lib.groupby(["CONTRATISTA", "ETAPA", "BLOQUE"], as_index=False)["PESO"]
                .sum()
            )

            # kg -> ton
            lib["PESO"] = lib["PESO"] / 1000.0

            etapas_set = { _canon_etapa(x) for x in lib["ETAPA"].tolist() }
            etapas_set.discard("")  # quita vacíos

            conteo_etapas = int(len(etapas_set))
            total_bloques = int(len(lib))
            total_peso = float(lib["PESO"].sum())
            return total_bloques, total_peso, etapas_set, conteo_etapas

        exp_bloques, exp_peso, exp_etapas_set, exp_conteo_etapas = _calc_expected(df)

        # --- Validación HTML: fila final TOTALES ---
        import pathlib
        s = pathlib.Path(html_path).read_text(encoding="utf-8")

        rows = _re.findall(r"<tr[^>]*>.*?</tr>", s, flags=_re.S | _re.I)
        _assert(len(rows) > 0, "bloques_liberados.html no contiene filas <tr>.")

        last = _re.sub(r"\s+", " ", rows[-1]).strip()

        m = _re.search(
            r"<td>\s*TOTALES\s*</td>\s*"
            r"<td>\s*([0-9]+)\s*</td>\s*"
            r"<td>\s*([0-9]+)\s*</td>\s*"
            r"<td>\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*</td>",
            last,
            flags=_re.I
        )
        _assert(m is not None, f"Fila TOTALES no encontrada o formato inesperado. last_row={last}")

        got_etapas = int(m.group(1))
        got_bloques = int(m.group(2))
        got_peso = float(m.group(3).replace(",", ""))

        _assert(got_etapas == exp_conteo_etapas, f"ETAPAS mismatch (HTML): html={got_etapas} vs esperado={exp_conteo_etapas}")
        _assert(got_bloques == exp_bloques, f"BLOQUES mismatch (HTML): html={got_bloques} vs esperado={exp_bloques}")
        _assert(abs(got_peso - exp_peso) <= 0.02, f"PESO mismatch (HTML): html={got_peso:.2f} vs esperado={exp_peso:.2f}")

        # --- Validación JSON: etapas + conteo + peso ---
        import json
        data = json.loads(pathlib.Path(json_path).read_text(encoding="utf-8"))
        _assert(isinstance(data, list) and len(data) > 0, "bloques_liberados.json está vacío o no es una lista.")

        got_etapas_set = { _canon_etapa(x.get("ETAPA", "")) for x in data }
        got_etapas_set.discard("")

        _assert(got_etapas_set == exp_etapas_set,
                f"ETAPAS mismatch (JSON): {sorted(got_etapas_set)} vs esperado {sorted(exp_etapas_set)}")

        _assert(len(data) == exp_bloques, f"Conteo registros JSON mismatch: json={len(data)} vs esperado={exp_bloques}")

        got_peso_json = sum(float(x.get("PESO", 0) or 0) for x in data)
        _assert(abs(got_peso_json - exp_peso) <= 0.02, f"PESO mismatch (JSON): json={got_peso_json:.2f} vs esperado={exp_peso:.2f}")

        # --- Consistencia con resumen global (opcional) ---
        try:
            resumen_liberados = int(metricas.get("dossiers_liberados", exp_bloques))
            _assert(exp_bloques == resumen_liberados,
                    f"Liberados (resumen) vs Bloques liberados difieren: resumen={resumen_liberados} vs bloques={exp_bloques}")
        except Exception:
            pass

        print("✅ ASSERT OK: Export 'bloques_liberados' consistente (HTML/JSON vs dataframe).")

    except Exception as e:
        print(f"❌ ASSERT/EXPORT falló en bloques_liberados (HTML/JSON): {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

