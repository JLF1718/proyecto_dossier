import pandas as pd

# Cargar datos 
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
        df['CONTRATISTA'] = contratista
        dfs.append(df)
    except Exception as e:
        print(f'Error {contratista}: {e}')

df = pd.concat(dfs, ignore_index=True)

# Normalizar CONTRATISTA
if 'Contratista' in df.columns and 'CONTRATISTA' not in df.columns:
    df.rename(columns={'Contratista': 'CONTRATISTA'}, inplace=True)

# Filtrar entregas BAYSA
df_filtrado = df[(df['CONTRATISTA'] == 'BAYSA') & 
                 (df['ENTREGA'].notna()) & 
                 (df['ENTREGA'] != '')].copy()

# Calcular entregas
def contar_liberados(estatus_col):
    return (estatus_col == 'LIBERADO').sum()

def contar_entregados(estatus_col):
    return estatus_col.isin(['LIBERADO', 'ENTREGADO']).sum()

entregas = df_filtrado.groupby('ENTREGA').agg({
    'BLOQUE': 'count',
    'PESO': lambda x: x.sum() / 1000,
}).reset_index()

entregas['Liberados'] = df_filtrado.groupby('ENTREGA')['ESTATUS'].apply(contar_liberados).values
entregas['Entregados'] = df_filtrado.groupby('ENTREGA')['ESTATUS'].apply(contar_entregados).values

entregas.columns = ['Semana', 'Planeados', 'Peso', 'Liberados', 'Entregados']
entregas = entregas.sort_values('Semana')

print("TABLA DE ENTREGAS ACTUALIZADA:")
print(entregas.to_string())
print("\nDetalle por semana:")
for _, row in entregas.iterrows():
    print(f"  {row['Semana']}: Planeados={row['Planeados']}, Liberados={row['Liberados']}, Entregados={row['Entregados']}, Peso={row['Peso']:.0f} ton")
