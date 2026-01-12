"""
Módulo Core de Métricas - Única Fuente de Verdad
================================================
Este módulo contiene todas las funciones de cálculo de métricas
compartidas entre dashboard.py y dashboard_consolidado.py.

IMPORTANTE: Cualquier modificación a la lógica de métricas
debe hacerse ÚNICAMENTE en este archivo.
"""

import pandas as pd
from typing import Dict, Tuple


def calcular_peso_liberado(df: pd.DataFrame) -> float:
    """
    Calcula el peso liberado total en kilogramos.
    
    REGLA: Usa el PESO completo del dossier con ESTATUS='LIBERADO',
    NO la columna PESO_LIBERADO (que puede ser parcial).
    
    NOTA: Esta función retorna el valor en kg del CSV.
    La conversión a toneladas se hace en calcular_metricas_basicas().
    
    Args:
        df: DataFrame con columnas PESO (en kg) y ESTATUS
        
    Returns:
        float: Suma del PESO de todos los dossieres liberados (en kg)
    """
    df_liberados = df[df['ESTATUS'] == 'LIBERADO']
    return df_liberados['PESO'].sum()


def calcular_metricas_basicas(df: pd.DataFrame) -> Dict:
    """
    Calcula métricas básicas de un DataFrame.
    
    Esta función es la ÚNICA fuente de verdad para métricas.
    Usada por dashboard.py y dashboard_consolidado.py.
    
    IMPORTANTE: Los valores de PESO en el CSV están en kilogramos (kg).
    Esta función convierte automáticamente a toneladas (ton) dividiendo por 1000.
    
    Args:
        df: DataFrame con datos de dossieres (PESO en kg)
        
    Returns:
        dict: Diccionario con métricas calculadas:
            - total_dossiers: Cantidad total de dossieres
            - dossiers_liberados: Cantidad de dossieres con ESTATUS='LIBERADO'
            - pct_liberado: Porcentaje de dossieres liberados
            - peso_total: Suma total de PESO (en toneladas)
            - peso_liberado: Suma de PESO de dossieres liberados (en toneladas)
            - pct_peso_liberado: Porcentaje de peso liberado
    """
    total = len(df)
    liberados = (df['ESTATUS'] == 'LIBERADO').sum()
    # Convertir de kg a toneladas
    peso_total = df['PESO'].sum() / 1000
    peso_liberado = calcular_peso_liberado(df) / 1000
    
    return {
        'total_dossiers': total,
        'dossiers_liberados': liberados,
        'pct_liberado': (liberados / total * 100) if total > 0 else 0,
        'peso_total': peso_total,
        'peso_liberado': peso_liberado,
        'pct_peso_liberado': (peso_liberado / peso_total * 100) if peso_total > 0 else 0,
    }


def calcular_metricas_por_contratista(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Calcula métricas agrupadas por contratista.
    
    Args:
        df: DataFrame con columna CONTRATISTA
        
    Returns:
        dict: Diccionario donde cada key es un contratista y value son sus métricas
    """
    metricas_por_contr = {}
    
    for contratista in df['CONTRATISTA'].unique():
        df_contr = df[df['CONTRATISTA'] == contratista]
        metricas_por_contr[contratista] = calcular_metricas_basicas(df_contr)
    
    return metricas_por_contr


def calcular_metricas_consolidadas(df: pd.DataFrame) -> Dict:
    """
    Calcula métricas consolidadas (globales + por contratista).
    
    Esta función combina métricas globales con métricas por contratista.
    Usada principalmente por dashboard_consolidado.py.
    
    Args:
        df: DataFrame consolidado con datos de múltiples contratistas
        
    Returns:
        dict: Diccionario con:
            - Métricas globales (keys directas)
            - por_contratista: Dict con métricas de cada contratista
    """
    # Métricas globales
    metricas = calcular_metricas_basicas(df)
    
    # Métricas por contratista
    metricas['por_contratista'] = calcular_metricas_por_contratista(df)
    
    return metricas


def calcular_metricas_individuales(df: pd.DataFrame) -> Dict:
    """
    Calcula métricas para un dashboard individual (un solo contratista).
    
    Incluye métricas adicionales específicas para dashboards individuales
    como % de ejecución real y brechas.
    
    Args:
        df: DataFrame de un solo contratista
        
    Returns:
        dict: Métricas básicas + métricas adicionales específicas
    """
    # Métricas básicas
    metricas = calcular_metricas_basicas(df)
    
    # Métricas adicionales para dashboard individual
    df_liberados = df[df['ESTATUS'] == 'LIBERADO'].copy()
    
    # Si existe columna PESO_LIBERADO, calcular % de ejecución real vs planificado
    if 'PESO_LIBERADO' in df_liberados.columns and not df_liberados.empty:
        peso_liberado_real = df_liberados['PESO_LIBERADO'].fillna(0).sum()
        peso_planificado = df_liberados['PESO'].sum()
        pct_ejecucion_real = (peso_liberado_real / peso_planificado * 100) if peso_planificado > 0 else 0
        
        # Calcular brechas
        df_liberados['BRECHA'] = df_liberados['PESO'] - df_liberados['PESO_LIBERADO'].fillna(0)
        
        # Validar brechas inválidas (PRO_* o SUE_* en etapas 1-2)
        bloque_str = df_liberados['BLOQUE'].fillna('').astype(str)
        etapa_vals = df_liberados['ETAPA'].fillna('').astype(str)
        cond_pro = bloque_str.str.startswith('PRO_')
        cond_sue = bloque_str.str.startswith('SUE_') & etapa_vals.isin(['ETAPA_1', 'ETAPA_2'])
        df_liberados['BRECHA_INVALIDA'] = ((cond_pro | cond_sue) & (df_liberados['BRECHA'].abs() > 0.01))
        bloques_brecha_invalida = len(df_liberados[df_liberados['BRECHA_INVALIDA']])
    else:
        pct_ejecucion_real = 100.0
        bloques_brecha_invalida = 0
    
    # Agregar métricas adicionales
    metricas['pct_ejecucion_real'] = pct_ejecucion_real
    metricas['bloques_brecha_invalida'] = bloques_brecha_invalida
    
    return metricas


def validar_consistencia_metricas(metricas: Dict) -> Tuple[bool, str]:
    """
    Valida que las métricas calculadas sean consistentes.
    
    Args:
        metricas: Diccionario de métricas calculadas
        
    Returns:
        Tuple[bool, str]: (es_valido, mensaje_error)
    """
    # Validar que peso_liberado no sea mayor que peso_total
    if metricas['peso_liberado'] > metricas['peso_total']:
        return False, f"Peso liberado ({metricas['peso_liberado']:,.0f}) no puede ser mayor que peso total ({metricas['peso_total']:,.0f})"
    
    # Validar que dossieres liberados no sean mayores que total
    if metricas['dossiers_liberados'] > metricas['total_dossiers']:
        return False, f"Dossieres liberados ({metricas['dossiers_liberados']}) no pueden ser mayores que total ({metricas['total_dossiers']})"
    
    # Validar porcentajes
    if not (0 <= metricas['pct_liberado'] <= 100):
        return False, f"Porcentaje liberado ({metricas['pct_liberado']:.1f}%) fuera de rango 0-100"
    
    if not (0 <= metricas['pct_peso_liberado'] <= 100):
        return False, f"Porcentaje peso liberado ({metricas['pct_peso_liberado']:.1f}%) fuera de rango 0-100"
    
    return True, "OK"


# Función de utilidad para debugging
def imprimir_metricas(metricas: Dict, titulo: str = "MÉTRICAS"):
    """Imprime métricas en formato legible para debugging."""
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")
    print(f"  • Dossieres: {metricas['total_dossiers']}")
    print(f"  • Liberados: {metricas['dossiers_liberados']} ({metricas['pct_liberado']:.1f}%)")
    print(f"  • Peso Total: {metricas['peso_total']:,.0f} ton")
    print(f"  • Peso Liberado: {metricas['peso_liberado']:,.0f} ton ({metricas['pct_peso_liberado']:.1f}%)")
    
    # Validar
    es_valido, mensaje = validar_consistencia_metricas(metricas)
    if not es_valido:
        print(f"  ⚠️  ADVERTENCIA: {mensaje}")
    else:
        print(f"  ✅ Métricas válidas")
    print(f"{'='*60}\n")
