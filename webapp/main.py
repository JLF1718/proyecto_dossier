from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.metricas import calcular_metricas_basicas
from generators.utils_generator import leer_csv_robusto

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "webapp" / "static"
OUTPUT_DIR = BASE_DIR / "output"
TABLAS_DIR = OUTPUT_DIR / "tablas"
STATUS_AUDIT_LOG = OUTPUT_DIR / "exports" / "status_changes_baysa.jsonl"
API_ACCESS_KEY = os.getenv("DOSSIER_WEB_ACCESS_KEY", "").strip()

CSV_PATHS: Dict[str, Path] = {
    "BAYSA": BASE_DIR / "data" / "contratistas" / "BAYSA" / "ctrl_dosieres_BAYSA_normalizado.csv",
    "JAMAR": BASE_DIR / "data" / "contratistas" / "JAMAR" / "ctrl_dosieres_JAMAR_normalizado.csv",
}

STATUS_CANONICO = {
    "NO_INICIADO": "PLANEADO",
    "POR_ASIGNAR": "PLANEADO",
    "PLANEADO": "PLANEADO",
    "OBSERVADO": "OBSERVADO",
    "EN_REVISION": "EN_REVISIÓN",
    "EN_REVISIÓN": "EN_REVISIÓN",
    "LIBERADO": "LIBERADO",
    "INPROS_REVISANDO": "EN_REVISIÓN",
    "BAYSA_ATENDIENDO_COMENTARIOS": "OBSERVADO",
}

app = FastAPI(
    title="Control Dossieres Web",
    description="Portal web profesional para seguimiento en vivo (Fase 1)",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


@app.middleware("http")
async def optional_api_key_guard(request: Request, call_next):
    if not API_ACCESS_KEY:
        return await call_next(request)

    if request.url.path.startswith("/api"):
        provided_key = request.headers.get("x-access-key") or request.query_params.get("k", "")
        if provided_key != API_ACCESS_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "No autorizado. Usa la clave de acceso del portal."},
            )

    response = await call_next(request)

    # Headers ligeros de endurecimiento para despliegue web local/publicado
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"

    return response


def _normalizar_estatus(df: pd.DataFrame) -> pd.DataFrame:
    if "ESTATUS" not in df.columns:
        return df
    out = df.copy()
    out["ESTATUS"] = out["ESTATUS"].astype(str).str.strip().str.upper()
    out["ESTATUS"] = out["ESTATUS"].map(STATUS_CANONICO).fillna(out["ESTATUS"])
    return out


def _leer_contratista(contratista: str) -> pd.DataFrame:
    ruta = CSV_PATHS.get(contratista)
    if ruta is None:
        raise HTTPException(status_code=400, detail=f"Contratista invalido: {contratista}")
    if not ruta.exists():
        raise HTTPException(status_code=404, detail=f"CSV no encontrado para {contratista}: {ruta}")

    df = leer_csv_robusto(ruta)
    if df.empty:
        return df

    if "PESO" in df.columns:
        df["PESO"] = pd.to_numeric(df["PESO"], errors="coerce").fillna(0.0)
    return _normalizar_estatus(df)


def _serializar_metricas(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {
            "total_dossiers": 0,
            "dossiers_liberados": 0,
            "pct_liberado": 0.0,
            "peso_total": 0.0,
            "peso_liberado": 0.0,
            "pct_peso_liberado": 0.0,
        }
    metricas = calcular_metricas_basicas(df)
    return {
        "total_dossiers": int(metricas["total_dossiers"]),
        "dossiers_liberados": int(metricas["dossiers_liberados"]),
        "pct_liberado": round(float(metricas["pct_liberado"]), 2),
        "peso_total": round(float(metricas["peso_total"]), 2),
        "peso_liberado": round(float(metricas["peso_liberado"]), 2),
        "pct_peso_liberado": round(float(metricas["pct_peso_liberado"]), 2),
    }


def _inferir_semana_actual() -> Optional[str]:
    for var_name in ("SEMANA_CORTE", "SEMANA_PROYECTO"):
        value = os.getenv(var_name, "").strip().upper()
        if re.fullmatch(r"S\d{1,4}", value):
            return value

    historico_dir = OUTPUT_DIR / "historico"
    candidatos: List[tuple[float, str]] = []
    if historico_dir.exists():
        for path in historico_dir.iterdir():
            match = re.match(r"^(S\d{1,4})_", path.name)
            if match:
                candidatos.append((path.stat().st_mtime, match.group(1)))

    if candidatos:
        candidatos.sort(reverse=True)
        return candidatos[0][1]

    return None


def _regenerar_vista_baysa() -> Dict[str, object]:
    semana = _inferir_semana_actual()
    if not semana:
        return {"ok": False, "message": "No se pudo inferir la semana actual para regenerar posters."}

    try:
        ruta = regenerar_poster_principal_baysa(semana, output_dir=OUTPUT_DIR)
        if ruta is None:
            return {"ok": False, "message": "No se encontró información BAYSA para regenerar el poster."}

        posters_baysa = sorted(
            [p for p in TABLAS_DIR.glob("*.html") if p.is_file() and "baysa" in p.name.lower() and "jamar" not in p.name.lower()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for poster_antiguo in posters_baysa[1:]:
            poster_antiguo.unlink(missing_ok=True)

        return {"ok": True, "message": f"Poster principal actualizado para {semana}.", "poster": ruta.name}
    except Exception as exc:
        return {"ok": False, "message": f"CSV actualizado, pero falló la regeneración ligera: {exc}"}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/summary")
def summary() -> Dict[str, object]:
    data: Dict[str, object] = {
        "generated_at": datetime.now().isoformat(),
        "contractors": {},
    }

    consolidados: List[pd.DataFrame] = []
    for contratista in CSV_PATHS.keys():
        df = _leer_contratista(contratista)
        if not df.empty:
            df = df.copy()
            df["CONTRATISTA"] = contratista
            consolidados.append(df)
        data["contractors"][contratista] = _serializar_metricas(df)

    if consolidados:
        df_total = pd.concat(consolidados, ignore_index=True)
        data["global"] = _serializar_metricas(df_total)
    else:
        data["global"] = _serializar_metricas(pd.DataFrame())

    return data


@app.get("/api/status-distribution")
def status_distribution(
    contractor: Optional[str] = Query(default=None, pattern="^(BAYSA|JAMAR)$")
) -> Dict[str, object]:
    if contractor:
        df = _leer_contratista(contractor)
        conteo = (
            df["ESTATUS"].value_counts(dropna=False).to_dict() if "ESTATUS" in df.columns else {}
        )
        return {"contractor": contractor, "counts": conteo}

    counts: Dict[str, Dict[str, int]] = {}
    for contratista in CSV_PATHS.keys():
        df = _leer_contratista(contratista)
        counts[contratista] = (
            df["ESTATUS"].value_counts(dropna=False).to_dict() if "ESTATUS" in df.columns else {}
        )
    return {"contractor": "ALL", "counts": counts}


@app.get("/api/latest-rows")
def latest_rows(
    contractor: str = Query(pattern="^(BAYSA|JAMAR)$"),
    limit: int = Query(default=20, ge=1, le=200),
) -> Dict[str, object]:
    df = _leer_contratista(contractor)
    if df.empty:
        return {"contractor": contractor, "rows": []}

    columnas = [c for c in ["BLOQUE", "ETAPA", "ESTATUS", "PESO", "ENTREGA", "No. REVISIÓN"] if c in df.columns]
    if not columnas:
        columnas = list(df.columns[:8])

    muestra = df.tail(limit).copy()
    muestra = muestra[columnas]
    rows = muestra.fillna("").to_dict(orient="records")

    return {
        "contractor": contractor,
        "columns": columnas,
        "rows": rows,
        "returned": len(rows),
    }


@app.get("/api/tablas-posters")
def tablas_posters(limit: int = Query(default=1, ge=1, le=10)) -> Dict[str, object]:
    if not TABLAS_DIR.exists():
        return {"count": 0, "items": []}

    posters = sorted(
        [
            p
            for p in TABLAS_DIR.glob("*.html")
            if p.is_file() and "baysa" in p.name.lower() and "jamar" not in p.name.lower()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    items = [
        {
            "name": p.name,
            "url": f"/output/tablas/{p.name}",
            "updated_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        }
        for p in posters
    ]
    return {"count": len(items), "items": items}
