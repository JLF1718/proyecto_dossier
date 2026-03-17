"""Document-oriented export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from backend.dependencies import verify_api_key
from backend.services.dossier_service import build_executive_report_payload
from backend.services.executive_pack_service import (
    PPTX_MEDIA_TYPE,
    executive_pack_filename,
    generate_executive_pack_pptx,
)

router = APIRouter(
    prefix="/export",
    tags=["Export"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/executive-pack.pptx", summary="Download executive board pack as PPTX")
def download_executive_pack_pptx(
    week: int | None = Query(None, description="Analysis week from live BAYSA data"),
    comparison_week: int | None = Query(None, description="Stored snapshot week for comparison"),
    lang: str = Query("en", description="Language hint (en or es)"),
) -> Response:
    try:
        report = build_executive_report_payload(
            selected_week=week,
            comparison_week=comparison_week,
            language=lang,
        )
        analysis_week = report.get("report_meta", {}).get("analysis_week")
        payload = generate_executive_pack_pptx(week=week, comparison_week=comparison_week, language=lang)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = executive_pack_filename(analysis_week)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type=PPTX_MEDIA_TYPE, headers=headers)
