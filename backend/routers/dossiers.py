"""
/api/dossiers — Dossier Control endpoints
==========================================
CRUD-style read endpoints for dossier records stored in CSV files.
Write operations go through the data-entry app; the API is read-only here.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_api_key
from backend.services.dossier_service import (
    build_executive_report_payload,
    build_historical_comparison_payload,
    list_weekly_snapshots,
    load_dossiers,
    weekly_management_payload,
)

router = APIRouter(
    prefix="/api/dossiers",
    tags=["Dossiers"],
    dependencies=[Depends(verify_api_key)],
)

# ── endpoints ────────────────────────────────────────────────────────────────


def _to_api_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Adapt service schema to legacy /api/dossiers response fields."""
    out = pd.DataFrame(index=df.index)
    out["CONTRATISTA"] = df.get("contractor", pd.Series("BAYSA", index=df.index, dtype="object")).astype(str).str.upper()
    out["ETAPA"] = df.get("stage", pd.Series(index=df.index, dtype="object")).astype(str)

    status_map = {
        "approved": "LIBERADO",
        "pending": "OBSERVADO",
        "in_review": "EN_REVISIÓN",
        "rejected": "RECHAZADO",
        "out_of_scope": "FUERA DE ALCANCE",
    }
    status_series = df.get("status", pd.Series(index=df.index, dtype="object")).astype(str).str.lower().str.strip()
    out["ESTATUS"] = status_series.map(status_map).fillna(status_series.str.upper())

    out["IN_CONTRACT_SCOPE"] = (
        df.get("in_contract_scope", pd.Series(True, index=df.index, dtype="bool"))
        .fillna(True)
        .astype(bool)
    )
    out["PESO_DOSSIER_KG"] = pd.to_numeric(
        df.get("weight_kg", pd.Series(index=df.index, dtype="float64")), errors="coerce"
    ).fillna(0.0)
    return out


def _load_api_dossiers() -> pd.DataFrame:
    return _to_api_schema(load_dossiers())


def _available_contractors(df: Optional[pd.DataFrame] = None) -> List[str]:
    if df is None:
        df = _load_api_dossiers()
    if "CONTRATISTA" not in df.columns or df.empty:
        return []
    return sorted(value for value in df["CONTRATISTA"].dropna().astype(str).str.upper().unique())


def _filter_df(
    df: pd.DataFrame,
    contratista: Optional[str],
    estatus: Optional[str],
    etapa: Optional[str],
    entrega: Optional[str],
) -> pd.DataFrame:
    if contratista and "CONTRATISTA" in df.columns:
        df = df[df["CONTRATISTA"].str.upper() == contratista.upper()]
    if estatus and "ESTATUS" in df.columns:
        df = df[df["ESTATUS"].str.upper() == estatus.upper()]
    if etapa and "ETAPA" in df.columns:
        df = df[df["ETAPA"].str.upper() == etapa.upper()]
    if entrega and "ENTREGA" in df.columns:
        df = df[df["ENTREGA"].str.upper() == entrega.upper()]
    return df


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return df.where(pd.notna(df), other=None).to_dict(orient="records")

@router.get("", summary="List dossiers (paginated, filterable)")
def list_dossiers(
    contratista: Optional[str] = Query(None, description="Filter by contractor key. Active dossier flow is BAYSA-only."),
    estatus: Optional[str] = Query(None, description="Filter by status (PLANEADO, OBSERVADO, EN_REVISIÓN, LIBERADO)"),
    etapa: Optional[str] = Query(None, description="Filter by construction stage"),
    entrega: Optional[str] = Query(None, description="Filter by delivery week (e.g. S186)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=5000, description="Page size"),
) -> Dict[str, Any]:
    try:
        df = _load_api_dossiers()
        df = _filter_df(df, contratista, estatus, etapa, entrega)
        total = len(df)
        page_df = df.iloc[skip : skip + limit]
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": _df_to_records(page_df),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/contractors", summary="List active contractor keys")
def list_contractors() -> List[str]:
    try:
        return _available_contractors()
    except Exception:
        return []


@router.get("/statuses", summary="Canonical status values")
def list_statuses() -> List[str]:
    return ["LIBERADO", "OBSERVADO", "EN_REVISIÓN", "RECHAZADO", "FUERA DE ALCANCE"]


@router.get("/kpis", summary="Contractual KPI counts (in-scope dossiers only)")
def dossier_kpis() -> Dict[str, Any]:
    """Return KPI counts filtered to contractual scope (in_contract_scope == True).

    Blocks with N° == '--' are excluded from all counts but remain in the
    underlying dataset for traceability (in_contract_scope == False).

    Canonical status values:
        - ``approved``   – LIBERADO
        - ``pending``    – OBSERVADO / ATENCIÓN COMENTARIOS / FUERA DE ALCANCE
        - ``in_review``  – REVISIÓN INPROS (internal review, not a rejection)
        - ``rejected``   – explicit rejection (not present in current BAYSA data)
    """
    try:
        from backend.services.dossier_service import load_dossiers, compute_kpis
        df = load_dossiers("BAYSA")
        return compute_kpis(df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/snapshots", summary="List persisted weekly snapshots")
def dossier_snapshots() -> Dict[str, Any]:
    try:
        items = list_weekly_snapshots()
        return {
            "total": len(items),
            "items": items,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/weekly-management", summary="Weekly management payload")
def dossier_weekly_management(
    week: Optional[int] = Query(None, description="Analysis week to evaluate against current BAYSA data"),
) -> Dict[str, Any]:
    try:
        return weekly_management_payload("BAYSA", selected_week=week)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/historical-comparison", summary="Historical weekly comparison payload")
def dossier_historical_comparison(
    week: Optional[int] = Query(None, description="Current analysis week from live BAYSA data"),
    comparison_week: Optional[int] = Query(None, description="Stored snapshot week used as historical comparison"),
) -> Dict[str, Any]:
    try:
        return build_historical_comparison_payload(selected_week=week, comparison_week=comparison_week)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/executive-report", summary="Executive report pack payload")
def dossier_executive_report(
    week: Optional[int] = Query(None, description="Analysis week from live BAYSA data"),
    comparison_week: Optional[int] = Query(None, description="Stored snapshot week used for comparison"),
    lang: str = Query("en", description="Response language hint for consumers (en or es)"),
) -> Dict[str, Any]:
    try:
        return build_executive_report_payload(selected_week=week, comparison_week=comparison_week, language=lang)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{contractor}", summary="Get dossiers for the requested contractor key")
def get_contractor_dossiers(
    contractor: str,
    estatus: Optional[str] = Query(None),
    etapa: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
) -> Dict[str, Any]:
    try:
        key = contractor.upper()
        df = _load_api_dossiers()
        if key not in _available_contractors(df):
            raise ValueError(f"Unsupported contractor key: {contractor}. Active dossier flow is BAYSA-only.")

        df = _filter_df(df, contratista=key, estatus=estatus, etapa=etapa, entrega=None)
        total = len(df)
        page_df = df.iloc[skip : skip + limit]
        return {
            "contractor": key,
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": _df_to_records(page_df),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
