"""
Dependency Injection — auth-ready FastAPI dependencies
======================================================
Drop-in security: set API_ACCESS_KEY env var to enable key auth.
Add a JWT layer here when upgrading to full auth.
"""

from fastapi import HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader

from .config import get_settings

_API_KEY_HEADER = APIKeyHeader(name="X-Access-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key_header: str | None = Security(_API_KEY_HEADER),
) -> None:
    """Optional API-key guard.

    If ``API_ACCESS_KEY`` is not set the dependency is a no-op, which is safe
    for local/LAN deployments behind a firewall.  Set the env var on production
    to enforce key-based access for every /api/* route.
    """
    settings = get_settings()
    expected = settings.api_access_key.strip()
    if not expected:
        return  # auth disabled

    provided = (api_key_header or "").strip()
    if not provided:
        # Also accept key as query param for browser/curl convenience
        provided = request.query_params.get("k", "").strip()

    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
