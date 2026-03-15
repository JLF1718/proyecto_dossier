"""
/api/welds — Welding Control endpoints
========================================
Stub endpoints for welding inspection records.
Extend with real data sources as the welding module matures.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_api_key
from modules.welding_control.api import list_weld_records, weld_kpis

router = APIRouter(
    prefix="/api/welds",
    tags=["Welding Control"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", summary="List weld inspection records (filterable)")
def list_welds(
    contratista: Optional[str] = Query(None),
    estado: Optional[str] = Query(None, description="ACEPTADO, RECHAZADO, PENDIENTE"),
    proceso: Optional[str] = Query(None, description="SMAW, GTAW, FCAW …"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
) -> Dict[str, Any]:
    try:
        return list_weld_records(
            contratista=contratista,
            estado=estado,
            proceso=proceso,
            skip=skip,
            limit=limit,
        )
    except FileNotFoundError:
        # Welding data not yet loaded — return empty result set
        return {"total": 0, "skip": skip, "limit": limit, "items": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/metrics", summary="Weld inspection KPIs")
def weld_metrics(
    contratista: Optional[str] = Query(None),
) -> Dict[str, Any]:
    try:
        return weld_kpis(contratista)
    except FileNotFoundError:
        return {"message": "No welding data available yet."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
