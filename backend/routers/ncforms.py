"""
/api/ncforms — Non-Conformance (NC) management endpoints
=========================================================
Endpoints for creating, listing and closing NC reports.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import verify_api_key
from modules.nc_management.api import create_nc_record, list_nc_records_data, nc_kpis

router = APIRouter(
    prefix="/api/ncforms",
    tags=["NC Management"],
    dependencies=[Depends(verify_api_key)],
)


class NCFormCreate(BaseModel):
    """Schema for creating a new NC form."""
    numero_nc: str = Field(..., description="NC number e.g. NC-2026-001")
    contratista: str
    descripcion: str
    disciplina: str = Field(..., description="Welding, Civil, Piping …")
    sistema: Optional[str] = None
    responsable: Optional[str] = None
    fecha_emision: datetime = Field(default_factory=datetime.utcnow)


@router.get("", summary="List NC forms")
def list_nc_forms(
    contratista: Optional[str] = Query(None),
    estado: Optional[str] = Query(None, description="ABIERTA, EN_PROCESO, CERRADA"),
    disciplina: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
) -> Dict[str, Any]:
    try:
        return list_nc_records_data(
            contratista=contratista,
            estado=estado,
            disciplina=disciplina,
            skip=skip,
            limit=limit,
        )
    except FileNotFoundError:
        return {"total": 0, "skip": skip, "limit": limit, "items": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/metrics", summary="NC KPIs")
def nc_metrics(contratista: Optional[str] = Query(None)) -> Dict[str, Any]:
    try:
        return nc_kpis(contratista)
    except FileNotFoundError:
        return {"message": "No NC data available yet."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("", summary="Register a new NC form", status_code=201)
def create_nc_form(payload: NCFormCreate) -> Dict[str, Any]:
    """
    Persist a new Non-Conformance record.
    Currently writes to the SQLite database via the nc_management module.
    """
    try:
        record = create_nc_record(payload.model_dump())
        return {"ok": True, "record": record}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
