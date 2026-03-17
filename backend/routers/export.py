"""Server-side executive PDF export routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.services.pdf_export_service import generate_executive_pdf

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/executive-pdf")
def export_executive_pdf(
    lang: str | None = Query(default=None),
    contractor: str | None = Query(default=None),
    discipline: str | None = Query(default=None),
    system: str | None = Query(default=None),
    week: str | None = Query(default=None),
    compare_week: str | None = Query(default=None),
    history_mode: str | None = Query(default=None),
) -> Response:
    try:
        pdf_bytes = generate_executive_pdf(
            lang=lang,
            contractor=contractor,
            discipline=discipline,
            system=system,
            week=week,
            compare_week=compare_week,
            history_mode=history_mode,
        )
    except Exception as exc:  # pragma: no cover - protects endpoint contract
        raise HTTPException(status_code=500, detail=f"Failed to generate executive PDF: {exc}") from exc

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"executive-dashboard-{timestamp}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
