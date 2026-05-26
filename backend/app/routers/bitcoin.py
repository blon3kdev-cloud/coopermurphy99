"""Public BTC price snapshot + SSE stream."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from .. import btc_price
from ..rate_limit import limiter

router = APIRouter(prefix="/api/bitcoin", tags=["bitcoin"])


@router.get("")
@limiter.exempt
async def get_state() -> dict:
    snap = btc_price.snapshot()
    return {
        "price": snap["price"],
        "windows": snap["windows"],
        "priceSamples": snap.get("priceSamples"),
        "fairOdds": snap.get("fairOdds"),
        "updatedAt": datetime.fromtimestamp(snap["ts"] / 1000, tz=timezone.utc).isoformat()
        if snap["ts"] else None,
    }


@router.get("/stream")
@limiter.exempt
async def stream_state():
    import json
    q = btc_price.subscribe()

    async def event_gen():
        try:
            snap = btc_price.snapshot()
            if snap["price"] is not None:
                yield {"data": json.dumps(snap)}
            while True:
                yield {"data": await q.get()}
        except asyncio.CancelledError:
            raise
        finally:
            btc_price.unsubscribe(q)

    return EventSourceResponse(event_gen())
