import json
import re
from pathlib import Path
from string import Template

import pandas as pd

import sys

# --- Fix Windows console encoding (evita UnicodeEncodeError por emojis) ---
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_col(df: pd.DataFrame, candidates: list[str]) -> str:
    norm_map = {str(c).strip().upper(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().upper()
        if key in norm_map:
            return norm_map[key]
    raise KeyError(f"No encontré ninguna de estas columnas: {candidates}. Disponibles: {list(df.columns)}")


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce"
    )


def normalize_stage_label(x) -> str:
    s = "" if pd.isna(x) else str(x).strip().upper()
    if not s:
        return "SIN_ETAPA"
    if "SIN_ETAPA" in s:
        return "SIN_ETAPA"
    m = re.search(r"(\d+)", s)
    if m:
        n = int(m.group(1))
        return f"ETAPA_{n:02d}"
    return s


def count_etapas(stage_labels: set[str]) -> int:
    """
    Conteo tipo presencia:
    ETAPA_01..ETAPA_04 => suma 1 por cada una presente
    + SIN_ETAPA => suma 1 si aparece (si algún día se cuela)
    """
    total = 0
    for n in range(1, 5):
        total += 1 if f"ETAPA_{n:02d}" in stage_labels else 0
    if "SIN_ETAPA" in stage_labels:
        total += 1
    return total


def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent  # .../proyecto_dossier

    archivos = {
        "JAMAR": project_root / "data" / "contratistas" / "JAMAR" / "ctrl_dosieres_JAMAR_normalizado.csv",
        "BAYSA": project_root / "data" / "contratistas" / "BAYSA" / "ctrl_dosieres_BAYSA_normalizado.csv",
    }

    dfs = []
    for contratista, path in archivos.items():
        if path.exists():
            df = pd.read_csv(path, encoding="utf-8-sig")
            df["CONTRATISTA"] = contratista
            dfs.append(df)

    if not dfs:
        print("No se encontraron archivos de datos normalizados.")
        return 1

    df = pd.concat(dfs, ignore_index=True)

    col_estatus = find_col(df, ["ESTATUS"])
    col_bloque = find_col(df, ["BLOQUE"])
    col_peso = find_col(df, ["PESO"])
    col_etapa = find_col(df, ["ETAPA"])

    liberados = df[df[col_estatus].astype(str).str.strip().str.upper() == "LIBERADO"].copy()

    liberados["ETAPA_NORM"] = liberados[col_etapa].apply(normalize_stage_label)
    liberados["BLOQUE_NORM"] = liberados[col_bloque].astype(str).str.strip()
    liberados["PESO_NUM"] = to_numeric(liberados[col_peso]).fillna(0.0)
    liberados["PESO_TON"] = liberados["PESO_NUM"] / 1000.0

    # Consolidar (evita duplicados)
    tabla = (
        liberados.groupby(["CONTRATISTA", "ETAPA_NORM", "BLOQUE_NORM"], as_index=False)["PESO_TON"]
        .sum()
        .rename(columns={"ETAPA_NORM": "ETAPA", "BLOQUE_NORM": "BLOQUE", "PESO_TON": "PESO"})
    ).sort_values(["CONTRATISTA", "ETAPA", "BLOQUE"]).reset_index(drop=True)

    total_bloques = int(len(tabla))
    total_peso = float(tabla["PESO"].sum())
    etapas_presentes = set(tabla["ETAPA"].dropna().astype(str))
    etapas_total = count_etapas(etapas_presentes)

    # Outputs
    out_dir = project_root / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "bloques_liberados.json"
    html_path = out_dir / "bloques_liberados.html"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tabla.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    html_template = Template(r"""
<!DOCTYPE html>
<html lang='es'>
<head>
    <meta charset='UTF-8'>
    <title>Lista de Bloques Liberados</title>
    <style>
        body { font-family: Segoe UI, Arial, sans-serif; background: #fafbfc; margin: 0; padding: 0; }
        .container { max-width: 980px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); padding: 32px; }
        h1 { text-align: center; margin-bottom: 0.2em; }
        .total { text-align: center; font-size: 1.05em; margin-bottom: 0.6em; color: #0F7C3F; }
        .sub { text-align:center; font-size:0.95em; color:#555; margin-bottom: 1.6em; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1.8em; }
        th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: center; }
        th { background: #4A4A4A; color: #fff; font-size: 1.02em; }
        tr:nth-child(even) { background: #f8f9fa; }
        tr.totals-row { background: #e6e6e6 !important; font-weight: 700; }
        .btn { display: block; margin: 0 auto; padding: 10px 24px; background: #0F7C3F; color: #fff; border: none; border-radius: 5px; font-size: 1em; cursor: pointer; transition: background 0.2s; }
        .btn:hover { background: #0c5c2e; }
    </style>
</head>
<body>
    <div class='container'>
        <h1>Lista de Bloques Liberados</h1>
        <div class='total'>Total de bloques liberados: <b>$total_bloques</b> | Peso total liberado: <b>$total_peso</b> ton</div>
        <div class='sub'>Etapas detectadas (conteo): <b>$etapas_total</b></div>

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
                $rows
                <tr class="totals-row">
                    <td>TOTALES</td>
                    <td>$etapas_total</td>
                    <td>$total_bloques</td>
                    <td>$total_peso</td>
                </tr>
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
        doc.setFontSize(16);
        doc.text('Lista de Bloques Liberados', 105, 16, null, null, 'center');
        doc.setFontSize(11);
        doc.text('Total bloques: $total_bloques | Peso total: $total_peso ton', 105, 24, null, null, 'center');
        doc.autoTable({
            html: '#tabla-bloques',
            startY: 30,
            headStyles: { fillColor: [74,74,74] },
            styles: { halign: 'center' }
        });
        doc.save('bloques_liberados.pdf');
    }
    </script>
</body>
</html>
""")

    rows = "\n".join(
        f"<tr>"
        f"<td>{r.CONTRATISTA}</td>"
        f"<td>{r.ETAPA}</td>"
        f"<td>{r.BLOQUE}</td>"
        f"<td>{r.PESO:.2f}</td>"
        f"</tr>"
        for r in tabla.itertuples(index=False)
    )

    html = html_template.substitute(
        total_bloques=total_bloques,
        total_peso=f"{total_peso:,.2f}",
        etapas_total=etapas_total,
        rows=rows
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("[OK] Archivos generados correctamente:")
    print(f"   JSON: {json_path.resolve()}")
    print(f"   HTML: {html_path.resolve()}")
    return 0
from pathlib import Path
import pandas as pd

def generar_bloques_liberados_html_json_desde_df(df: pd.DataFrame, out_dir: Path) -> tuple[Path, Path]:
    """
    Genera:
      - out_dir/bloques_liberados.json
      - out_dir/bloques_liberados.html
    usando el DataFrame consolidado (sin releer CSVs).
    """
    import json
    import re
    from string import Template

    def find_col(df, candidates):
        norm = {str(c).strip().upper(): c for c in df.columns}
        for cand in candidates:
            k = cand.strip().upper()
            if k in norm:
                return norm[k]
        raise KeyError(f"No encontré {candidates}. Disponibles: {list(df.columns)}")

    def to_numeric(series):
        return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")

    def normalize_stage_label(x):
        s = "" if pd.isna(x) else str(x).strip().upper()
        if not s:
            return "SIN_ETAPA"
        if "SIN_ETAPA" in s:
            return "SIN_ETAPA"
        m = re.search(r"(\d+)", s)
        if m:
            n = int(m.group(1))
            return f"ETAPA_{n:02d}"
        return s

    def count_etapas(stage_labels: set[str]) -> int:
        total = 0
        for n in range(1, 5):
            total += 1 if f"ETAPA_{n:02d}" in stage_labels else 0
        if "SIN_ETAPA" in stage_labels:
            total += 1
        return total

    col_estatus = find_col(df, ["ESTATUS"])
    col_bloque  = find_col(df, ["BLOQUE"])
    col_peso    = find_col(df, ["PESO"])
    col_etapa   = find_col(df, ["ETAPA"])
    col_contra  = find_col(df, ["CONTRATISTA"])

    liberados = df[df[col_estatus].astype(str).str.strip().str.upper() == "LIBERADO"].copy()

    liberados["ETAPA_NORM"]  = liberados[col_etapa].apply(normalize_stage_label)
    liberados["BLOQUE_NORM"] = liberados[col_bloque].astype(str).str.strip()
    liberados["PESO_NUM"]    = to_numeric(liberados[col_peso]).fillna(0.0)
    liberados["PESO_TON"]    = liberados["PESO_NUM"] / 1000.0
    liberados["CONTRA_NORM"] = liberados[col_contra].astype(str).str.strip().str.upper()

    tabla = (
        liberados.groupby(["CONTRA_NORM", "ETAPA_NORM", "BLOQUE_NORM"], as_index=False)["PESO_TON"]
        .sum()
        .rename(columns={"CONTRA_NORM":"CONTRATISTA","ETAPA_NORM":"ETAPA","BLOQUE_NORM":"BLOQUE","PESO_TON":"PESO"})
        .sort_values(["CONTRATISTA","ETAPA","BLOQUE"])
        .reset_index(drop=True)
    )

    total_bloques = int(len(tabla))
    total_peso    = float(tabla["PESO"].sum())
    etapas_total  = count_etapas(set(tabla["ETAPA"].dropna().astype(str)))

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "bloques_liberados.json"
    html_path = out_dir / "bloques_liberados.html"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tabla.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    html_template = Template(r"""
<!DOCTYPE html>
<html lang='es'>
<head>
    <meta charset='UTF-8'>
    <title>Lista de Bloques Liberados</title>
    <style>
        body { font-family: Segoe UI, Arial, sans-serif; background: #fafbfc; margin: 0; padding: 0; }
        .container { max-width: 980px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); padding: 32px; }
        h1 { text-align: center; margin-bottom: 0.2em; }
        .total { text-align: center; font-size: 1.05em; margin-bottom: 1.6em; color: #0F7C3F; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1.8em; }
        th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: center; }
        th { background: #4A4A4A; color: #fff; font-size: 1.02em; }
        tr:nth-child(even) { background: #f8f9fa; }
        tr.totals-row { background: #e6e6e6 !important; font-weight: 700; }
    </style>
</head>
<body>
    <div class='container'>
        <h1>Lista de Bloques Liberados</h1>
        <div class='total'>Total de bloques liberados: <b>$total_bloques</b> | Peso total liberado: <b>$total_peso</b> ton</div>

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
                $rows
                <tr class="totals-row">
                    <td>TOTALES</td>
                    <td>$etapas_total</td>
                    <td>$total_bloques</td>
                    <td>$total_peso</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>
""")

    rows = "\n".join(
        f"<tr><td>{r.CONTRATISTA}</td><td>{r.ETAPA}</td><td>{r.BLOQUE}</td><td>{r.PESO:.2f}</td></tr>"
        for r in tabla.itertuples(index=False)
    )

    html = html_template.substitute(
        total_bloques=total_bloques,
        total_peso=f"{total_peso:,.2f}",
        etapas_total=etapas_total,
        rows=rows
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return json_path, html_path


if __name__ == "__main__":
    raise SystemExit(main())
