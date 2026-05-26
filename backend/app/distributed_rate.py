"""MongoDB-backed rate limits — shared across workers."""
from __future__ import annotations

from datetime import timedelta
from time import time

from fastapi import HTTPException
from pymongo import ReturnDocument

from .db import get_db, now


async def enforce_distributed_rate(
    client_key: str,
    route_key: str,
    limit: int,
    window_sec: int = 60,
) -> None:
    db = get_db()
    window_start = int(time()) // window_sec * window_sec
    bucket_id = f"{client_key}:{route_key}:{window_start}"
    doc = await db.rate_limits.find_one_and_update(
        {"_id": bucket_id},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {"expires_at": now() + timedelta(seconds=window_sec + 60)},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    count = doc.get("count", 1) if doc else 1
    if count > limit:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
