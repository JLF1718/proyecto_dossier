# grafico_etapa_estatus_baysa.py
import pandas as pd
import plotly.graph_objects as go

def crear_grafico_etapa_estatus_baysa(df: pd.DataFrame, config: dict, contratista: str = "BAYSA") -> go.Figure:
    """
    Gráfico de barras agrupadas: Totales vs Estatus por ETAPA.
    Diseñado para consumir ESTATUS ya CANONIZADO (LIBERADO/OBSERVADO/EN_REVISIÓN/PLANEADO).
    """

    if df is None or len(df) == 0:
        return None

    df = df.copy()

    # Si viene consolidado, filtra por contratista; si ya viene filtrado, no afecta
    if "CONTRATISTA" in df.columns:
        df = df[df["CONTRATISTA"] == contratista].copy()

    if df.empty:
        return None

    # Normalizar columnas mínimas (por robustez)
    if "ETAPA" not in df.columns:
        df["ETAPA"] = "INFO_GENERAL"
    df["ETAPA"] = df["ETAPA"].fillna("INFO_GENERAL").astype(str)
    df.loc[df["ETAPA"].str.strip() == "", "ETAPA"] = "INFO_GENERAL"

    if "ESTATUS" not in df.columns:
        df["ESTATUS"] = "PLANEADO"
    df["ESTATUS"] = df["ESTATUS"].fillna("PLANEADO").astype(str)

    # Pivot conteos por ETAPA y ESTATUS
    pivot = (
        df.groupby(["ETAPA", "ESTATUS"], dropna=False)
          .size()
          .unstack(fill_value=0)
    )

    # Orden canónico (clave interna = exactamente como tu df normalizado)
    status_order = ["LIBERADO", "OBSERVADO", "EN_REVISIÓN", "PLANEADO"]
    for s in status_order:
        if s not in pivot.columns:
            pivot[s] = 0
    pivot = pivot[status_order]

    totals = pivot.sum(axis=1)

    # % por etapa (para etiquetas)
    denom = totals.replace(0, pd.NA)
    pct = (pivot.div(denom, axis=0).fillna(0) * 100)

    etapas = pivot.index.tolist()

    # Estilo
    tipo = (config.get("dashboard", {}) or {}).get("tipografia", {}) or {}
    font_family = tipo.get("familia_principal", "Segoe UI, Arial, sans-serif")

    colores = config.get("colores", {}) or {}
    col_total = "#D9D9D9"
    col_liberado = colores.get("LIBERADO", "#0F7C3F")
    col_obs = colores.get("OBSERVADO", "#D0021B")
    col_rev = colores.get("EN_REVISIÓN", "#F5A623")
    col_plan = colores.get("PLANEADO", "#808080")

    fig = go.Figure()

    # Totales (gris, detrás)
    fig.add_trace(go.Bar(
        x=etapas,
        y=totals.tolist(),
        name="TOTALES",
        marker=dict(color=col_total),
        opacity=0.35,
        text=[f"<b><span style='color:black'>{int(v)}</span></b><br><b><span style='color:black'>100%</span></b>"
              for v in totals.tolist()],
        textposition="outside",
        textfont=dict(color="black", size=13),
        hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>"
    ))

    def add_status_trace(key: str, display: str, color: str):
        y_vals = pivot[key].astype(int).tolist()
        txt = [f"{int(v)}<br>{pct.loc[e, key]:.1f}%" for e, v in zip(etapas, y_vals)]
        fig.add_trace(go.Bar(
            x=etapas,
            y=y_vals,
            name=display,
            marker=dict(color=color),
            text=txt,
            textposition="auto",
            textfont=dict(color="black", size=12),
            hovertemplate=f"<b>%{{x}}</b><br>{display}: %{{y}}<extra></extra>",
        ))

    add_status_trace("LIBERADO", "LIBERADO", col_liberado)
    add_status_trace("OBSERVADO", "OBSERVADO", col_obs)
    # OJO: clave interna EN_REVISIÓN, etiqueta visible "EN REVISIÓN"
    add_status_trace("EN_REVISIÓN", "EN REVISIÓN", col_rev)
    add_status_trace("PLANEADO", "PLANEADO", col_plan)

    # Layout
    ymax = max(float(totals.max()) * 1.20, 1.0)

    fig.update_layout(
        title=dict(text=f"<b>Dossieres por Etapa y Estatus - {contratista}</b>", x=0.5, xanchor="center"),
        barmode="group",
        bargap=0.18,
        height=400,
        plot_bgcolor="#fff",
        paper_bgcolor="#fff",
        font=dict(family=font_family),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        margin=dict(l=30, r=30, t=60, b=70),
        xaxis=dict(title="Etapa"),
        yaxis=dict(visible=False, showticklabels=False, showgrid=False, zeroline=False, range=[0, ymax]),
    )

    return fig
