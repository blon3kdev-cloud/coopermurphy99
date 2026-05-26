"""Match preset team codes to markets and apply images."""
from __future__ import annotations

from .db import get_db
from .market_utils import is_open_for_betting


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def name_matches(team: str, alias: str) -> bool:
    t, a = _norm(team), _norm(alias)
    if not t or not a:
        return False
    if t == a:
        return True
    if len(a) >= 4 and len(t) >= 4:
        return a in t or t in a
    return False


def _market_name_candidates(market: dict) -> list[str]:
    out: list[str] = []
    for key in ("yes_label", "no_label"):
        v = market.get(key)
        if v:
            out.append(str(v))
    title = str(market.get("title") or "")
    lower = title.lower()
    if " - " in title:
        parts = title.split(" - ", 1)
    elif " vs " in lower:
        normalized = title.replace(" VS ", " vs ")
        parts = normalized.split(" vs ", 1)
    else:
        parts = []
    for part in parts:
        p = part.strip()
        if p:
            out.append(p)
    return out


def market_matches_preset(market: dict, preset_names: list[str]) -> bool:
    if not preset_names:
        return False
    for candidate in _market_name_candidates(market):
        for alias in preset_names:
            if name_matches(candidate, alias):
                return True
    return False


def _market_image(market: dict) -> str:
    img = market.get("image")
    return str(img).strip() if img else ""


def _should_apply_preset_image(market: dict) -> bool:
    """Apply to open markets that do not have an image yet."""
    if _market_image(market):
        return False
    return is_open_for_betting(market)


def union_preset_names(*groups: list[str] | str | None) -> list[str]:
    """Deduped preset aliases (current + previous) for matching markets."""
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        items = [group] if isinstance(group, str) else (group or [])
        for raw in items:
            name = str(raw).strip()
            if not name:
                continue
            key = _norm(name)
            if key in seen:
                continue
            seen.add(key)
            out.append(name)
    return out


async def apply_preset_to_eligible_markets(
    image_url: str,
    preset_names: list[str],
    *,
    refresh_existing: bool = False,
    db=None,
) -> list[dict]:
    """Set image on active markets that match preset names.

    New applications: open markets without an image.
    Preset updates (``refresh_existing``): all matching active markets, even if
    they already have a different image URL from an earlier preset apply.
    """
    from .safe_url import validate_image_url_or_422

    safe_url = validate_image_url_or_422(image_url, field="imageUrl")
    if not safe_url or not preset_names:
        return []

    if db is None:
        db = get_db()
    updated: list[dict] = []
    cursor = db.markets.find({"status": "active"})
    async for market in cursor:
        if not market_matches_preset(market, preset_names):
            continue
        if not refresh_existing and not _should_apply_preset_image(market):
            continue
        await db.markets.update_one({"id": market["id"]}, {"$set": {"image": safe_url}})
        updated.append({"id": market["id"], "title": market.get("title", "")})
    return updated
