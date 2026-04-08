"""Shared FastAPI dependencies (optional API key for mutating routes).

Manager vs technician access is enforced in the UI (Work orders vs My work). Server-side
roles are not required for this MVP; use ``API_KEY`` when you need to protect writes.
"""

from fastapi import Header, HTTPException

from app.core.config import settings


def verify_api_key_if_configured(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
) -> None:
    """When ``API_KEY`` is set in the environment, require a matching key or Bearer token."""
    expected = (settings.API_KEY or "").strip()
    if not expected:
        return
    provided = (x_api_key or "").strip()
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if provided != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Send X-API-Key or Authorization: Bearer <key>.",
        )
