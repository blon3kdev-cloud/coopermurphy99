"""iSports API job queue + Mongo/in-memory schedule cache."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

from .db import get_db, now
from .isports_api_client import (
    fetch_basketball_schedule_by_date,
    fetch_basketball_schedule_by_match_ids,
    fetch_liveanimation_schedule,
    fetch_odds_main,
    fetch_player_stats_match,
    fetch_schedule_by_date,
    fetch_schedule_by_match_ids,
)

log = logging.getLogger(__name__)

SCHEDULE_CACHE_TTL = timedelta(hours=6)
SCHEDULE_LOOKAHEAD_DAYS = 7
MATCH_ID_CHUNK = 100

# Hot in-process cache so repeated session opens do not hit Mongo/API.
_mem_schedule: dict[str, tuple[datetime, list[dict]]] = {}
_inflight_schedule: dict[str, asyncio.Task] = {}

_job_queue: asyncio.Queue | None = None
_worker_task: asyncio.Task | None = None


def _chunk_ids(ids: list[str], size: int = MATCH_ID_CHUNK) -> list[list[str]]:
    clean = [str(i) for i in ids if i]
    return [clean[i : i + size] for i in range(0, len(clean), size)]


async def _ensure_worker() -> None:
    global _job_queue, _worker_task
    if _job_queue is None:
        _job_queue = asyncio.Queue()
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop())


async def _worker_loop() -> None:
    assert _job_queue is not None
    while True:
        fn, fut = await _job_queue.get()
        try:
            result = await fn()
            if not fut.done():
                fut.set_result(result)
        except Exception as exc:
            if not fut.done():
                fut.set_exception(exc)
        finally:
            _job_queue.task_done()


async def enqueue(coro_factory: Callable[[], Awaitable[Any]]) -> Any:
    """Run one API job at a time through the shared worker."""
    await _ensure_worker()
    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    await _job_queue.put((coro_factory, fut))
    return await fut


async def enqueue_schedule_by_match_ids(
    match_ids: list[str],
    *,
    sport: str = "football",
) -> dict[str, dict]:
    """Fetch schedule rows in chunks via the shared queue."""
    if not match_ids:
        return {}
    fetch_fn = (
        fetch_basketball_schedule_by_match_ids
        if sport.strip().lower() == "basketball"
        else fetch_schedule_by_match_ids
    )
    out: dict[str, dict] = {}
    for chunk in _chunk_ids(match_ids):
        chunk_copy = list(chunk)

        async def _job(c: list[str] = chunk_copy) -> list[dict]:
            return await fetch_fn(c)

        rows = await enqueue(_job)
        for row in rows:
            mid = str(row.get("matchId", ""))
            if mid:
                out[mid] = row
    return out


async def enqueue_liveanimation_by_match_ids(match_ids: list[str]) -> dict[str, dict]:
    """Single liveanimation fetch (queued), filtered to wanted match IDs."""
    if not match_ids:
        return {}
    wanted = {str(m) for m in match_ids}

    async def _job() -> list[dict]:
        return await fetch_liveanimation_schedule()

    rows = await enqueue(_job)
    return {
        str(r.get("matchId")): r
        for r in rows
        if str(r.get("matchId")) in wanted
    }


async def enqueue_player_goals_by_match_ids(match_ids: list[str]) -> dict[str, dict[str, int]]:
    """Player goal stats per match — one queued API call per match."""
    out: dict[str, dict[str, int]] = {}
    for mid in match_ids:
        match_id = str(mid)

        async def _job(m: str = match_id) -> list[dict]:
            return await fetch_player_stats_match(m)

        try:
            rows = await enqueue(_job)
        except Exception as exc:
            log.warning("isports playerstats failed for %s: %s", match_id, exc)
            continue
        goals: dict[str, int] = {}
        for row in rows:
            pid = str(row.get("playerId", ""))
            if not pid:
                continue
            try:
                goals[pid] = int(row.get("goals") or 0) + int(row.get("penaltyGoals") or 0)
            except (TypeError, ValueError):
                goals[pid] = 0
        out[match_id] = goals
    return out


async def enqueue_odds_main_by_match_ids(match_ids: list[str]) -> dict[str, Any]:
    """Merge odds/main payloads from chunked queued fetches."""
    if not match_ids:
        return {}
    merged: dict[str, Any] = {
        "handicap": [],
        "europeOdds": [],
        "overUnder": [],
        "handicapHalf": [],
        "overUnderHalf": [],
    }
    for chunk in _chunk_ids(match_ids):
        chunk_copy = list(chunk)

        async def _job(c: list[str] = chunk_copy) -> dict[str, Any]:
            return await fetch_odds_main(c)

        data = await enqueue(_job)
        if not isinstance(data, dict):
            continue
        for key in merged:
            rows = data.get(key)
            if isinstance(rows, list):
                merged[key].extend(rows)
    return merged


def _schedule_cache_key(sport: str, day: date) -> str:
    return f"{sport.strip().lower()}:{day.isoformat()}"


def _fetch_schedule_for_sport(sport: str):
    sport = sport.strip().lower()
    if sport == "basketball":
        return fetch_basketball_schedule_by_date
    return fetch_schedule_by_date


async def _read_schedule_cache_only(sport: str, day: date) -> Optional[list[dict]]:
    """Return cached rows if fresh; None if cache miss (no API call)."""
    key = _schedule_cache_key(sport, day)
    mem = _mem_schedule.get(key)
    if mem is not None:
        fetched_at, rows = mem
        if now() - fetched_at < SCHEDULE_CACHE_TTL:
            return list(rows)

    db = get_db()
    doc = await db.isports_schedule_cache.find_one({"date": key})
    if doc and doc.get("fetched_at"):
        fetched = doc["fetched_at"]
        if isinstance(fetched, datetime):
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=timezone.utc)
            if now() - fetched < SCHEDULE_CACHE_TTL:
                rows = list(doc.get("matches") or [])
                _mem_schedule[key] = (fetched, rows)
                return rows
    return None


async def get_cached_schedule_for_date(day: date, *, sport: str = "football") -> list[dict]:
    """Return schedule rows for a calendar day (GMT), using memory + Mongo cache."""
    key = _schedule_cache_key(sport, day)
    mem = _mem_schedule.get(key)
    if mem is not None:
        fetched_at, rows = mem
        if now() - fetched_at < SCHEDULE_CACHE_TTL:
            return list(rows)

    db = get_db()
    doc = await db.isports_schedule_cache.find_one({"date": key})
    if doc and doc.get("fetched_at"):
        fetched = doc["fetched_at"]
        if isinstance(fetched, datetime):
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=timezone.utc)
            if now() - fetched < SCHEDULE_CACHE_TTL:
                rows = list(doc.get("matches") or [])
                _mem_schedule[key] = (fetched, rows)
                return rows

    if key in _inflight_schedule:
        return await _inflight_schedule[key]

    async def _fetch_and_store() -> list[dict]:
        iso_day = day.isoformat()
        sport_norm = sport.strip().lower()

        async def _api_job() -> list[dict]:
            data = await _fetch_schedule_for_sport(sport_norm)(iso_day)
            return data if isinstance(data, list) else []

        rows = await enqueue(_api_job)
        fetched_at = now()
        _mem_schedule[key] = (fetched_at, rows)
        await db.isports_schedule_cache.update_one(
            {"date": key},
            {
                "$set": {
                    "date": key,
                    "matches": rows,
                    "fetched_at": fetched_at,
                }
            },
            upsert=True,
        )
        return rows

    task = asyncio.create_task(_fetch_and_store())
    _inflight_schedule[key] = task
    try:
        return await task
    finally:
        _inflight_schedule.pop(key, None)


async def load_upcoming_schedule_days(
    days: int = SCHEDULE_LOOKAHEAD_DAYS,
    *,
    sport: str = "football",
) -> list[dict]:
    """Load and merge schedule for today + next days (UTC dates)."""
    merged, _ = await load_schedule_until_enough(
        min_filtered=0,
        max_days=days,
        filter_fn=lambda rows: rows,
        sport=sport,
    )
    return merged


def _merge_schedule_rows(
    merged: list[dict],
    seen: set[str],
    rows: list[dict],
) -> None:
    for row in rows:
        mid = str(row.get("matchId", ""))
        if not mid or mid in seen:
            continue
        seen.add(mid)
        merged.append(row)


async def load_schedule_until_enough(
    *,
    min_filtered: int,
    max_days: int = SCHEDULE_LOOKAHEAD_DAYS,
    filter_fn: Callable[[list[dict]], list[dict]],
    sport: str = "football",
) -> tuple[list[dict], list[dict]]:
    """Use warm cache first; only call schedule API (60s cooldown) for missing days."""
    today = datetime.now(timezone.utc).date()
    days = max(1, max_days)
    merged: list[dict] = []
    seen: set[str] = set()
    api_fetches = 0

    for offset in range(days):
        day = today + timedelta(days=offset)
        cached = await _read_schedule_cache_only(sport, day)
        if cached is not None:
            _merge_schedule_rows(merged, seen, cached)
        filtered = filter_fn(merged)
        if min_filtered <= 0 or len(filtered) >= min_filtered:
            log.info(
                "isports schedule: cache hit through day+%d, %d matches, %d filtered (need %d)",
                offset,
                len(merged),
                len(filtered),
                min_filtered,
            )
            return merged, filtered

    for offset in range(days):
        day = today + timedelta(days=offset)
        if await _read_schedule_cache_only(sport, day) is not None:
            continue
        rows = await get_cached_schedule_for_date(day, sport=sport)
        api_fetches += 1
        _merge_schedule_rows(merged, seen, rows)
        filtered = filter_fn(merged)
        if min_filtered <= 0 or len(filtered) >= min_filtered:
            log.info(
                "isports schedule: %d API day(s), %d matches, %d filtered (need %d)",
                api_fetches,
                len(merged),
                len(filtered),
                min_filtered,
            )
            return merged, filtered

    return merged, filter_fn(merged)


async def prewarm_schedule_cache() -> None:
    """Background: fill schedule cache for upcoming days (60s between API calls)."""
    try:
        today = datetime.now(timezone.utc).date()
        for offset in range(SCHEDULE_LOOKAHEAD_DAYS):
            day = today + timedelta(days=offset)
            if await _read_schedule_cache_only("football", day) is not None:
                continue
            await get_cached_schedule_for_date(day, sport="football")
            log.info("isports prewarm cached schedule for %s", day.isoformat())
    except Exception as exc:
        log.warning("isports schedule prewarm failed: %s", exc)
