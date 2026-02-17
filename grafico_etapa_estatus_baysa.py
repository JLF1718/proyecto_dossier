# grafico_etapa_estatus_baysa.py
import pandas as pd
import plotly.graph_objects as go


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convierte '#RRGGBB' o '#RGB' a 'rgba(r,g,b,a)' con alpha [0..1]."""
    if hex_color is None:
        hex_color = "#808080"
    hex_color = str(hex_color).strip()

    try:
        alpha = float(alpha)
    except Exception:
        alpha = 0.22
    alpha = max(0.0, min(1.0, alpha))

    # Expandir #RGB -> #RRGGBB
    if hex_color.startswith("#") and len(hex_color) == 4:
        hex_color = "#" + "".join([c * 2 for c in hex_color[1:]])

    if not (hex_color.startswith("#") and len(hex_color) == 7):
        hex_color = "#808080"

    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def crear_grafico_etapa_estatus_baysa(df: pd.DataFrame, config: dict) -> go.Figure:
    if df is None or df.empty:
        return None

    df = df.copy()

    # --- Robustez mínima (ETAPA) ---
    # Regla:
    # - INFO_GENERAL solo si ya viene en datos.
    # - Vacíos / nulos -> SIN_ETAPA (calidad de datos)
    if "ETAPA" not in df.columns:
        df["ETAPA"] = "SIN_ETAPA"
    else:
        df["ETAPA"] = df["ETAPA"].astype(str)

    df["ETAPA"] = df["ETAPA"].replace(["None", "nan", "NaN"], "").fillna("")
    df.loc[df["ETAPA"].str.strip() == "", "ETAPA"] = "SIN_ETAPA"
    df["ETAPA"] = df["ETAPA"].str.strip()

    # --- Pivot conteos ---
    pivot = (
        df.groupby(["ETAPA", "ESTATUS"], dropna=False)
        .size()
        .unstack(fill_value=0)
    )

    # --- Orden canónico desde YAML (si existe) ---
    dash_cfg = (config.get("dashboard", {}) or {})
    status_order = dash_cfg.get("status_order") or ["LIBERADO", "OBSERVADO", "EN_REVISIÓN", "PLANEADO"]

    for s in status_order:
        if s not in pivot.columns:
            pivot[s] = 0
    pivot = pivot[status_order]

    totals = pivot.sum(axis=1)
    denom = totals.replace(0, pd.NA)
    pct = (pivot.div(denom, axis=0).fillna(0) * 100)

    etapas = pivot.index.tolist()

    # Mandar SIN_ETAPA al final si existe
    if "SIN_ETAPA" in etapas:
        etapas = [e for e in etapas if e != "SIN_ETAPA"] + ["SIN_ETAPA"]
        pivot = pivot.reindex(etapas)
        totals = pivot.sum(axis=1)
        denom = totals.replace(0, pd.NA)
        pct = (pivot.div(denom, axis=0).fillna(0) * 100)

    # --- Estilo / Config ---
    tipo = (dash_cfg.get("tipografia", {}) or {})
    font_family = tipo.get("familia_principal", "Segoe UI, Arial, sans-serif")

    colores = (config.get("colores", {}) or {})

    col_total_hex = colores.get("TOTALES", colores.get("PLANEADO", "#808080"))
    totales_opacity = float(colores.get("totales_opacity", 0.22))
    col_total = hex_to_rgba(col_total_hex, totales_opacity)

    col_liberado = hex_to_rgba(colores.get("LIBERADO", "#0F7C3F"), 1.0)
    col_obs = hex_to_rgba(colores.get("OBSERVADO", "#D0021B"), 1.0)
    col_rev = hex_to_rgba(colores.get("EN_REVISIÓN", "#F5A623"), 1.0)
    col_plan = hex_to_rgba(colores.get("PLANEADO", "#808080"), 1.0)

    # Umbrales “sostenibles”: inside vs outside (sin offsets manuales)
    chart_cfg = (dash_cfg.get("grafico_etapa_estatus_baysa", {}) or {})
    min_pct_inside = float(chart_cfg.get("min_pct_inside", 12.0))     # % mínimo para ir dentro
    min_count_inside = int(chart_cfg.get("min_count_inside", 4))      # conteo mínimo para ir dentro

    bargap = float(chart_cfg.get("bargap", 0.10))
    bargroupgap = float(chart_cfg.get("bargroupgap", 0.05))

    fig = go.Figure()

    # --- TOTALES (gris) ---

    fig.add_trace(go.Bar(
        x=etapas,
        y=totals.astype(int).tolist(),
        name="TOTALES",
        marker=dict(color=col_total),
        text=[f"{int(v)}<br>100%" for v in totals.tolist()],  # <- aquí
        textposition="inside",
        textangle=0,
        insidetextanchor="end",
        insidetextfont=dict(color="rgba(0,0,0,1)", size=12, family=font_family),
        hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>",
        cliponaxis=False,
    ))


    # --- Función interna (CORRECTAMENTE ANIDADA) ---
    def add_status_trace(key: str, display: str, color: str) -> bool:
        y_vals = pivot[key].astype(int).tolist()

        texts = []
        positions = []
        used_outside = False

        for e, v in zip(etapas, y_vals):
            p = float(pct.loc[e, key]) if (e in pct.index and key in pct.columns) else 0.0

            if v <= 0:
                texts.append("")
                positions.append("inside")
                continue

            # % SIEMPRE VISIBLE:
            # - si hay cuerpo suficiente -> inside (minimalista)
            # - si no -> outside (no se pierde el %)
            label = f"{v}<br>{p:.1f}%"
            if (p >= min_pct_inside) and (v >= min_count_inside):
                texts.append(label)
                positions.append("inside")
            else:
                texts.append(label)
                positions.append("outside")
                used_outside = True

        fig.add_trace(go.Bar(
            x=etapas,
            y=y_vals,
            name=display,
            marker=dict(color=color),
            text=texts,
            textposition=positions,     # array dinámico por barra
            textangle=0,                # SIEMPRE horizontal
            insidetextfont=dict(color="white", size=12, family=font_family),
            outsidetextfont=dict(color="black", size=12, family=font_family),
            cliponaxis=False,
            hovertemplate=f"<b>%{{x}}</b><br>{display}: %{{y}}<extra></extra>",
        ))

        return used_outside

    # Mapeos (evitan hardcode repetido y mantienen orden desde YAML)
    display_map = {"EN_REVISIÓN": "EN REVISIÓN"}
    color_map = {
        "LIBERADO": col_liberado,
        "OBSERVADO": col_obs,
        "EN_REVISIÓN": col_rev,
        "PLANEADO": col_plan,
    }

    any_outside = False
    for st in status_order:
        any_outside = add_status_trace(st, display_map.get(st, st), color_map.get(st, col_plan)) or any_outside

    # Headroom dinámico: solo “crece” si realmente hay textos afuera
    headroom_inside = float(chart_cfg.get("ymax_headroom_inside", 1.35))
    headroom_outside = float(chart_cfg.get("ymax_headroom_outside", 1.55))
    headroom = headroom_outside if any_outside else headroom_inside
    ymax = max(float(totals.max()) * headroom, 1.0)

    # Margen opcional por YAML
    m_cfg = (chart_cfg.get("margin", {}) or {})
    m_l = int(m_cfg.get("l", 30))
    m_r = int(m_cfg.get("r", 30))
    m_t = int(m_cfg.get("t", 60))
    m_b = int(m_cfg.get("b", 70))
    m_pad = int(m_cfg.get("pad", 0))

    fig.update_layout(
        title=dict(text="<b>Dossieres por Etapa y Estatus - BAYSA</b>", x=0.5, xanchor="center"),
        barmode="group",
        bargap=bargap,
        bargroupgap=bargroupgap,
        uniformtext=dict(minsize=10, mode="show"),  # requisito: % siempre visible
        height=400,
        plot_bgcolor="#fff",
        paper_bgcolor="#fff",
        font=dict(family=font_family),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        margin=dict(l=m_l, r=m_r, t=m_t, b=m_b, pad=m_pad),
        xaxis=dict(title=None, tickangle=0),
        yaxis=dict(visible=False, showticklabels=False, showgrid=False, zeroline=False, range=[0, ymax]),
    )

    return fig
