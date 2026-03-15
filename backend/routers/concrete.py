"""
/api/concrete - Concrete Control endpoints
=========================================
Read-oriented API for concrete quality assurance records and KPIs.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_api_key
from modules.concrete_control.api import concrete_kpis, list_concrete_records

router = APIRouter(
    prefix="/api/concrete",
    tags=["Concrete Control"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", summary="List concrete QA records (filterable)")
def list_concrete(
    contratista: Optional[str] = Query(None),
    estado: Optional[str] = Query(None, description="APROBADO, RECHAZADO, PENDIENTE"),
    elemento: Optional[str] = Query(None, description="Element type: COLUMN, BEAM, SLAB ..."),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
) -> Dict[str, Any]:
    try:
        return list_concrete_records(
            contratista=contratista,
            estado=estado,
            elemento=elemento,
            skip=skip,
            limit=limit,
        )
    except FileNotFoundError:
        return {"total": 0, "skip": skip, "limit": limit, "items": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/metrics", summary="Concrete QA KPIs")
def concrete_metrics(contratista: Optional[str] = Query(None)) -> Dict[str, Any]:
    try:
        return concrete_kpis(contratista)
    except FileNotFoundError:
        return {"message": "No concrete QA data available yet."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
