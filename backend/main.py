"""
QA Platform — FastAPI Backend
==============================
Entry point: ``uvicorn backend.main:app --reload``

Incorporates all existing analytics logic from core/ and generators/
through the analytics and modules layers.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure the project root is importable regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.config import get_settings
from backend.routers import concrete, dossiers, export, metrics, ncforms, welds
from database.session import init_db

# ── App instance ─────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Modular QA Management Platform for construction quality control. "
        "Covers dossier tracking, welding inspection, concrete QA, and NC management."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# ── Security headers middleware ───────────────────────────────────────────────

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(dossiers.router)
app.include_router(metrics.router)
app.include_router(welds.router)
app.include_router(concrete.router)
app.include_router(ncforms.router)
app.include_router(export.router)


@app.on_event("startup")
def _startup_init_db() -> None:
    """Ensure database tables exist before serving requests."""
    init_db()

# ── Root endpoints ────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root() -> Dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs",
    }


@app.get("/api/health", tags=["System"])
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.app_version,
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
