"""
/api/metrics — KPI and metrics endpoints
=========================================
Returns pre-calculated quality metrics from the analytics layer.
All weight values are in metric tonnes (ton).
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import verify_api_key
from backend.services.dossier_service import (
    contractor_dossier_kpis,
    dossier_kpis_by_contractor,
    dossier_kpis_by_stage,
    global_dossier_kpis,
)
from modules.welding_control.api import weld_kpis
from modules.concrete_control.api import concrete_kpis
from modules.nc_management.api import nc_kpis

router = APIRouter(
    prefix="/api/metrics",
    tags=["Metrics"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", summary="Global KPI summary")
def global_metrics() -> Dict[str, Any]:
    """Return aggregated KPIs across all contractors.

    Contract rule: rows flagged with ``in_contract_scope == False`` stay in the
    exported dataset for traceability but are excluded before KPI aggregation.
    """
    try:
        result = global_dossier_kpis()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Enrich with module snapshots when data exists; keep dossier KPI keys intact.
    module_metrics: Dict[str, Any] = {}
    try:
        module_metrics["welding"] = weld_kpis()
    except FileNotFoundError:
        module_metrics["welding"] = {"message": "No welding data available yet."}

    try:
        module_metrics["concrete"] = concrete_kpis()
    except FileNotFoundError:
        module_metrics["concrete"] = {"message": "No concrete QA data available yet."}

    try:
        module_metrics["nc_management"] = nc_kpis()
    except FileNotFoundError:
        module_metrics["nc_management"] = {"message": "No NC data available yet."}

    result["module_metrics"] = module_metrics
    return result


@router.get("/by-contractor", summary="KPIs broken down by contractor")
def metrics_by_contractor() -> Dict[str, Any]:
    try:
        return dossier_kpis_by_contractor()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/by-stage", summary="KPIs broken down by construction stage")
def metrics_by_stage(
    contratista: Optional[str] = Query(None, description="Limit to a single contractor"),
) -> Dict[str, Any]:
    try:
        return dossier_kpis_by_stage(contratista)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{contractor}", summary="KPIs for a single contractor")
def contractor_metrics(contractor: str) -> Dict[str, Any]:
    try:
        return contractor_dossier_kpis(contractor)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
