import pandas as pd

# Cargar datos consolidados igual como lo hace el script
archivos = {
    'JAMAR': 'data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv',
    'BAYSA': 'data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv'
}

dfs = []
for contratista, archivo in archivos.items():
    try:
        df = pd.read_csv(archivo, encoding='utf-8')
        df['CONTRATISTA'] = contratista
        dfs.append(df)
        print(f'Cargado {contratista}: {len(df)} registros')
    except Exception as e:
        print(f'Error {contratista}: {e}')

df = pd.concat(dfs, ignore_index=True)
print(f'Total consolidado: {len(df)} registros\n')

# Verificar si ENTREGA existe y tiene datos para BAYSA
df_baysa = df[df['CONTRATISTA'] == 'BAYSA']
print(f'BAYSA:')
print(f'  Total: {len(df_baysa)}')
print(f'  ENTREGA existe: {"ENTREGA" in df_baysa.columns}')
if 'ENTREGA' in df_baysa.columns:
    print(f'  Con ENTREGA no nula: {df_baysa[df_baysa["ENTREGA"].notna()].shape[0]}')
    print(f'\n  ENTREGA values:')
    print(df_baysa['ENTREGA'].value_counts(dropna=False))
    
# Simular lo que hace la función crear_tabla_entregas_baysa
df_filtrado = df[(df['CONTRATISTA'] == 'BAYSA') & 
                 (df['ENTREGA'].notna()) & 
                 (df['ENTREGA'] != '')].copy()

print(f'\nDatos filtrados para tabla entregas: {len(df_filtrado)} registros')
print(f'Columnas disponibles: {df_filtrado.columns.tolist()}')
