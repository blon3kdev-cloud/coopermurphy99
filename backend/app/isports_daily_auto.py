"""Midnight job: resolve finished markets, then auto-import new ones."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from .isports_auto_bets import (
    _build_variants,
    _match_by_id,
    create_markets_from_variants,
    create_session,
)
from .isports_api_client import IsportsNotConfiguredError
from .isports_resolution import resolve_isports_markets

log = logging.getLogger(__name__)

FOOTBALL_MATCH_COUNT = 5
NBA_MATCH_COUNT = 5


def _auto_variant_keys(variants: list[dict], *, sport: str) -> list[str]:
    """Main winner + whitelisted top scorers (football only)."""
    keys: list[str] = []
    main = next((v for v in variants if v.get("isMain")), None)
    if main:
        keys.append(str(main["key"]))
    if sport == "football":
        for v in variants:
            if v.get("category") == "player_scorer" and v.get("isTopPlayer"):
                keys.append(str(v["key"]))
    return keys


async def _import_sport(sport: str, amount: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "sport": sport,
        "requested": amount,
        "matches": [],
        "createdTotal": 0,
        "skippedTotal": 0,
        "errors": [],
    }
    try:
        session_meta = await create_session(sport, amount)
    except HTTPException as exc:
        summary["errors"].append(f"session: {exc.detail}")
        return summary
    except IsportsNotConfiguredError:
        summary["errors"].append("isports_api_not_configured")
        return summary
    except Exception as exc:
        summary["errors"].append(f"session: {exc}")
        return summary

    session_id = str(session_meta.get("sessionId", ""))
    if not session_id:
        summary["errors"].append("session: missing sessionId")
        return summary

    from .isports_auto_bets import _load_session

    session = await _load_session(session_id)
    match_ids = list(session.get("match_ids") or [])

    for mid in match_ids:
        match = _match_by_id(session, str(mid))
        if not match:
            summary["matches"].append({"matchId": mid, "error": "match_not_found"})
            continue
        home = str(match.get("homeName", ""))
        away = str(match.get("awayName", ""))
        row: dict[str, Any] = {
            "matchId": mid,
            "home": home,
            "away": away,
            "created": 0,
            "skipped": [],
            "variantKeys": [],
        }
        try:
            variants = await _build_variants(match, sport=sport)
            keys = _auto_variant_keys(variants, sport=sport)
            row["variantKeys"] = keys
            if not keys:
                row["skipped"].append("no_variants")
                summary["matches"].append(row)
                continue
            result = await create_markets_from_variants(session_id, str(mid), keys)
            row["created"] = int(result.get("count") or 0)
            row["skipped"] = list(result.get("skipped") or [])
            summary["createdTotal"] += row["created"]
            summary["skippedTotal"] += len(row["skipped"])
        except HTTPException as exc:
            detail = exc.detail
            row["error"] = detail if isinstance(detail, str) else str(detail)
            summary["errors"].append(f"{mid}: {row['error']}")
        except Exception as exc:
            row["error"] = str(exc)
            summary["errors"].append(f"{mid}: {exc}")
        summary["matches"].append(row)

    return summary


async def run_daily_isports_auto_import() -> dict[str, Any]:
    """Fetch 5 football + 5 NBA games and create default markets for each."""
    log.info("daily isports auto-import starting")
    football = await _import_sport("football", FOOTBALL_MATCH_COUNT)
    basketball = await _import_sport("basketball", NBA_MATCH_COUNT)
    out = {
        "football": football,
        "basketball": basketball,
        "createdTotal": int(football.get("createdTotal", 0)) + int(basketball.get("createdTotal", 0)),
    }
    log.info(
        "daily isports auto-import done: %d markets created (%d errors)",
        out["createdTotal"],
        len(football.get("errors", [])) + len(basketball.get("errors", [])),
    )
    return out


async def run_daily_isports_maintenance() -> dict[str, Any]:
    """00:00 job: resolve ended matches, then import new markets."""
    log.info("daily isports maintenance starting")
    resolve_result = await resolve_isports_markets()
    resolved = int(resolve_result.get("resolved", 0))
    imported = await run_daily_isports_auto_import()
    out = {"resolved": resolved, "resolve": resolve_result, "import": imported}
    log.info("daily isports maintenance done: resolved=%d, created=%d", resolved, imported.get("createdTotal", 0))
    return out
