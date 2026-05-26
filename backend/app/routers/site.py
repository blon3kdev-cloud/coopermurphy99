"""Public site status (maintenance mode)."""
from __future__ import annotations

from fastapi import APIRouter

from ..blik.settings_store import get_admin_flags

router = APIRouter(prefix="/api/site", tags=["site"])


@router.get("/status")
async def site_status() -> dict:
    flags = await get_admin_flags()
    return {"siteUnavailable": bool(flags.get("siteUnavailable"))}
