import pandas as pd

# Cargar datos consolidados igual como lo hace el script
archivos = {
    'JAMAR': 'data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv',
    'BAYSA': 'data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv'
}

dfs = []
for contratista, archivo in archivos.items():
    try:
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
        print(f'Cargado {contratista}: {len(df)} registros')
    except Exception as e:
        print(f'Error {contratista}: {e}')

df = pd.concat(dfs, ignore_index=True)
print(f'\nTotal consolidado: {len(df)} registros')
print(f'Columnas: {df.columns.tolist()}')

# Verificar si ENTREGA existe y tiene datos para BAYSA
print(f'\nVerificar ENTREGA:')
print(f'  "ENTREGA" in df.columns: {"ENTREGA" in df.columns}')

# Simular lo que hace la función crear_tabla_entregas_baysa
if 'ENTREGA' not in df.columns:
    print("  ⚠️ ENTREGA NO ENCONTRADA")
else:
    df_filtrado = df[(df['CONTRATISTA'] == 'BAYSA') & 
                     (df['ENTREGA'].notna()) & 
                     (df['ENTREGA'] != '')].copy()
    
    print(f'  Datos filtrados BAYSA: {len(df_filtrado)} registros')
    if len(df_filtrado) == 0:
        print("  ⚠️ RETORNARÍA NONE")
    else:
        print("  ✓ Generaría tabla")
