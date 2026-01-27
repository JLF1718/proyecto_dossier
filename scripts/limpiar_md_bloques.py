from pathlib import Path

input_md = Path('bloques_liberados.md')
output_md = Path('bloques_liberados.md')

with open(input_md, encoding='utf-8') as f:
    lines = f.readlines()


# Generar tabla Markdown limpia con encabezado y separador estándar
tabla = []
tabla.append('| Bloque | Peso (ton) | Semana |\n')
tabla.append('|--------|------------|--------|\n')
for line in lines:
    if line.startswith('|') and '|' in line[1:]:
        parts = [p.strip() for p in line.strip().split('|')]
        if len(parts) >= 4:
            bloque = parts[1]
            peso = parts[3]
            semana = parts[2] if len(parts) > 4 else ''
            if bloque and peso and bloque != 'Bloque' and peso != 'Peso (ton)':
                if semana == 'nan':
                    semana = ''
                if peso == 'nan':
                    peso = ''
                tabla.append(f'| {bloque} | {peso} | {semana} |\n')

with open(output_md, 'w', encoding='utf-8') as f:
    f.writelines(tabla)

print('Archivo bloques_liberados.md actualizado sin columnas de fecha ni nivel de revisión.')
