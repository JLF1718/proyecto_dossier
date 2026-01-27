import markdown2
import pdfkit
from pathlib import Path

md_file = Path('bloques_liberados.md')
pdf_file = Path('bloques_liberados.pdf')

# Convertir Markdown a HTML
with open(md_file, encoding='utf-8') as f:
    html = markdown2.markdown(f.read())

# Opciones para pdfkit
options = {
    'encoding': 'UTF-8',
    'page-size': 'A4',
    'margin-top': '10mm',
    'margin-bottom': '10mm',
    'margin-left': '10mm',
    'margin-right': '10mm',
}


# Configuración explícita de wkhtmltopdf para Windows
import pdfkit
config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
pdfkit.from_string(html, str(pdf_file), options=options, configuration=config)

print('PDF generado:', pdf_file)
