from pathlib import Path

input_md = Path('bloques_liberados.md')
output_md = Path('bloques_liberados.md')

with open(input_md, encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('| Bloque'):
        new_lines.append('| Bloque | Peso (ton) | Semana |\n')
    elif line.startswith('|--------'):
        new_lines.append('|--------|------------|--------|\n')
    elif line.startswith('|') and '|' in line[1:]:
        parts = [p.strip() for p in line.strip().split('|')]
        # parts: ['', 'PRO_03', 'nan', '167.74', 'BAYSA', 'nan', '']
        if len(parts) == 7:
            # Bloque, Fecha, Peso, Semana, Nivel
            bloque = parts[1]
            peso = parts[3]
            semana = parts[4]
            new_lines.append(f'| {bloque} | {peso} | {semana} |\n')
    else:
        new_lines.append(line)

with open(output_md, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Archivo bloques_liberados.md actualizado sin columnas de fecha ni nivel de revisión.')
