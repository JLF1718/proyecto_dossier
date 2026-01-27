import pandas as pd
from pathlib import Path
import json

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

if not dfs:
    print('No se encontraron archivos de datos normalizados.')
    exit(1)

df = pd.concat(dfs, ignore_index=True)

# Filtrar bloques liberados
liberados = df[df['ESTATUS'] == 'LIBERADO']

# Seleccionar columnas relevantes
cols = ['BLOQUE', 'PESO', 'CONTRATISTA']
liberados = liberados[cols]
liberados['PESO'] = liberados['PESO'] / 1000

# Guardar como JSON
json_data = liberados.to_dict(orient='records')
with open('bloques_liberados.json', 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

from string import Template
html_template = Template("""
<!DOCTYPE html>
<html lang='es'>
<head>
    <meta charset='UTF-8'>
    <title>Lista de Bloques Liberados</title>
    <style>
        body { font-family: Segoe UI, Arial, sans-serif; background: #fafbfc; margin: 0; padding: 0; }
        .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); padding: 32px; }
        h1 { text-align: center; margin-bottom: 0.2em; }
        .total { text-align: center; font-size: 1.2em; margin-bottom: 1.5em; color: #0F7C3F; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 2em; }
        th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: center; }
        th { background: #4A4A4A; color: #fff; font-size: 1.1em; }
        tr:nth-child(even) { background: #f8f9fa; }
        .btn { display: block; margin: 0 auto; padding: 10px 24px; background: #0F7C3F; color: #fff; border: none; border-radius: 5px; font-size: 1em; cursor: pointer; transition: background 0.2s; }
        .btn:hover { background: #0c5c2e; }
    </style>
</head>
<body>
    <div class='container'>
        <h1>Lista de Bloques Liberados</h1>
        <div class='total'>Total de bloques liberados: <b>$total</b></div>
        <table id='tabla-bloques'>
            <thead>
                <tr><th>Bloque</th><th>Peso (ton)</th><th>Contratista</th></tr>
            </thead>
            <tbody>
            $rows
            </tbody>
        </table>
        <button class='btn' onclick='exportarPDF()'>Exportar a PDF</button>
    </div>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'></script>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.7.0/jspdf.plugin.autotable.min.js'></script>
    <script>
    function exportarPDF() {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        doc.setFontSize(18);
        doc.text('Lista de Bloques Liberados', 105, 18, null, null, 'center');
        doc.setFontSize(12);
        doc.text('Total de bloques liberados: $total', 105, 28, null, null, 'center');
        doc.autoTable({
            html: '#tabla-bloques',
            startY: 36,
            headStyles: { fillColor: [74,74,74] },
            styles: { halign: 'center' }
        });
        doc.save('bloques_liberados.pdf');
    }
    </script>
</body>
</html>
""")

rows = '\n'.join(f'<tr><td>{row.BLOQUE}</td><td>{row.PESO:.2f}</td><td>{row.CONTRATISTA}</td></tr>' for row in liberados.itertuples())
html = html_template.substitute(total=len(liberados), rows=rows)

with open('bloques_liberados.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Archivos bloques_liberados.json y bloques_liberados.html generados correctamente.')
