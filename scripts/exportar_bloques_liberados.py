import pandas as pd
from pathlib import Path

# Cargar datos consolidados
archivos = {
    'JAMAR': 'data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv',
    'BAYSA': 'data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv'
}

dfs = []
for contratista, archivo in archivos.items():
    if Path(archivo).exists():
        df = pd.read_csv(archivo)
        df['CONTRATISTA'] = contratista
        dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# Filtrar bloques liberados
liberados = df[df['ESTATUS'] == 'LIBERADO']

# Seleccionar columnas relevantes
cols = ['CONTRATISTA', 'BLOQUE', 'ENTREGA', 'PESO', 'No. REVISIÓN']
liberados = liberados[cols]

# Convertir peso a toneladas
liberados['PESO'] = liberados['PESO'] / 1000

# Guardar en Markdown
with open('bloques_liberados.md', 'a', encoding='utf-8') as f:
    for _, row in liberados.iterrows():
        f.write(f"| {row['BLOQUE']} | {row['ENTREGA']} | {row['PESO']:.2f} | {row['CONTRATISTA']} | {row['No. REVISIÓN']} |\n")

print("Archivo bloques_liberados.md actualizado con bloques liberados.")
