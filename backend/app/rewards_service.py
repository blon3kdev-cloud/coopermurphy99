"""VIP bonuses, referral tiers, redeem codes — shared reward logic."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pymongo import ReturnDocument

from .bonus_calculation_service import BONUS_RATES, calculate_bonus
from .db import as_utc, get_db, now

WARSAW = ZoneInfo("Europe/Warsaw")

# Rank XP thresholds — total VIP XP from wagering (see _vip_xp).
VIP_TIERS: list[tuple[str, Decimal]] = [
    ("Bronze", Decimal("0")),
    ("Silver", Decimal("10000")),
    ("Gold", Decimal("50000")),
    ("Platinum", Decimal("250000")),
]

# Net loss contributes at this fraction toward rank XP (wager always counts 1:1).
VIP_XP_NET_LOSS_FACTOR = Decimal("0.15")

REFERRAL_TIERS: list[dict[str, Any]] = [
    {"id": 1, "label": "Tier 1", "amount_pln": Decimal("50"), "required": 10},
    {"id": 2, "label": "Tier 2", "amount_pln": Decimal("125"), "required": 50},
    {"id": 3, "label": "Tier 3", "amount_pln": Decimal("250"), "required": 100},
    {"id": 4, "label": "Tier 4", "amount_pln": Decimal("500"), "required": 250},
]

REFERRAL_ATTACH_WINDOW = timedelta(days=7)
RANK_MIN_TIER_INDEX = 2  # Gold


def _warsaw_now() -> datetime:
    return now().astimezone(WARSAW)


def _warsaw_today() -> date:
    return _warsaw_now().date()


def _daily_period_key(d: date | None = None) -> str:
    d = d or _warsaw_today()
    return d.isoformat()


def _weekly_period_key(d: date | None = None) -> str:
    d = d or _warsaw_today()
    if d.day < 7:
        anchor = 1
    elif d.day < 14:
        anchor = 7
    elif d.day < 21:
        anchor = 14
    else:
        anchor = 21
    return f"{d.year}-{d.month:02d}-{anchor:02d}"


def _monthly_period_key(d: date | None = None) -> str:
    d = d or _warsaw_today()
    return f"{d.year}-{d.month:02d}"


def _period_key(kind: str, d: date | None = None) -> str:
    if kind == "daily":
        return _daily_period_key(d)
    if kind == "weekly":
        return _weekly_period_key(d)
    if kind == "monthly":
        return _monthly_period_key(d)
    raise ValueError(kind)


def _next_midnight_warsaw_utc(from_dt: datetime | None = None) -> datetime:
    local = (from_dt or now()).astimezone(WARSAW)
    nxt = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.astimezone(timezone.utc)


def _weekly_reset_candidates(from_local: datetime) -> list[datetime]:
    y, m = from_local.year, from_local.month
    out: list[datetime] = []
    for day in (1, 7, 14, 21):
        out.append(datetime(y, m, day, 0, 0, 0, tzinfo=WARSAW))
    if m == 12:
        out.append(datetime(y + 1, 1, 1, 0, 0, 0, tzinfo=WARSAW))
    else:
        out.append(datetime(y, m + 1, 1, 0, 0, 0, tzinfo=WARSAW))
    return sorted(out)


def _next_weekly_reset_utc() -> datetime:
    local = _warsaw_now()
    for candidate in _weekly_reset_candidates(local):
        if candidate > local:
            return candidate.astimezone(timezone.utc)
    y, m = local.year, local.month
    if m == 12:
        nxt = datetime(y + 1, 2, 1, 0, 0, 0, tzinfo=WARSAW)
    else:
        nxt = datetime(y, m + 1, 1, 0, 0, 0, tzinfo=WARSAW)
    return nxt.astimezone(timezone.utc)


def _next_monthly_reset_utc() -> datetime:
    d = _warsaw_today()
    if d.month == 12:
        nxt = date(d.year + 1, 1, 1)
    else:
        nxt = date(d.year, d.month + 1, 1)
    return datetime(nxt.year, nxt.month, nxt.day, 0, 0, 0, tzinfo=WARSAW).astimezone(timezone.utc)


def _wagered(user: dict) -> Decimal:
    return Decimal(str(user.get("vip_wagered_pln") or 0))


def _won(user: dict) -> Decimal:
    return Decimal(str(user.get("vip_won_pln") or 0))


def _vip_xp(user: dict) -> Decimal:
    from .bonus_calculation_service import net_loss_pln

    w = _wagered(user)
    return w + net_loss_pln(w, _won(user)) * VIP_XP_NET_LOSS_FACTOR


def vip_tier_info(user: dict) -> tuple[int, dict]:
    xp = _vip_xp(user)
    idx = 0
    for i in range(len(VIP_TIERS) - 1, -1, -1):
        if xp >= VIP_TIERS[i][1]:
            idx = i
            break
    if idx >= len(VIP_TIERS) - 1:
        from_name = to_name = VIP_TIERS[-1][0]
        pct = 100.0
    else:
        from_name, from_thresh = VIP_TIERS[idx]
        to_name, to_thresh = VIP_TIERS[idx + 1]
        span = to_thresh - from_thresh
        pct = float((xp - from_thresh) / span * 100) if span > 0 else 0.0
        pct = max(0.0, min(100.0, pct))
    return idx, {"pct": round(pct, 2), "fromTier": from_name, "toTier": to_name}


def _period_stats(user: dict, kind: str) -> tuple[Decimal, Decimal]:
    stats = user.get("vip_period_stats") or {}
    bucket = stats.get(kind) or {}
    if bucket.get("period") != _period_key(kind):
        return Decimal(0), Decimal(0)
    return Decimal(str(bucket.get("wagered") or 0)), Decimal(str(bucket.get("won") or 0))


def _calc_bonus_amount(kind: str, wagered: Decimal, won: Decimal) -> Decimal:
    return calculate_bonus(kind, wagered, won).amount_pln


def signup_vip_bonus_claims() -> dict[str, str]:
    """Weekly/monthly locked until the next Warsaw reset after registration."""
    return {
        "weekly": _period_key("weekly"),
        "monthly": _period_key("monthly"),
    }


def _claim_period_stored(user: dict, kind: str) -> str | None:
    claims: dict = user.get("vip_bonus_claims") or {}
    raw = claims.get(kind)
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, datetime):
        dt = as_utc(raw)
        if dt is None:
            return None
        local = dt.astimezone(WARSAW)
        if kind == "daily":
            return _daily_period_key(local.date())
        if kind == "weekly":
            return _weekly_period_key(local.date())
        if kind == "monthly":
            return _monthly_period_key(local.date())
    return None


def _fmt_cooldown(remaining: timedelta) -> str:
    secs = max(0, int(remaining.total_seconds()))
    if secs <= 0:
        return "0m"
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _bonus_status(user: dict, kind: str, tier_idx: int) -> dict:
    if kind == "rank":
        if tier_idx < RANK_MIN_TIER_INDEX:
            return {"status": "locked", "requirement": "Required: Gold"}
        claimed_tiers = set(user.get("vip_rank_claimed_tiers") or [])
        if tier_idx in claimed_tiers:
            return {"status": "claimed", "countdown": "Odebrano"}
        w, won = _wagered(user), _won(user)
        preview = _calc_bonus_amount("rank", w, won)
        out: dict[str, Any] = {"status": "ready"}
        if preview > 0:
            out["amountPreview"] = float(preview)
        return out

    current = _period_key(kind)
    stored = _claim_period_stored(user, kind)
    if stored == current:
        reset_at = {
            "daily": _next_midnight_warsaw_utc,
            "weekly": _next_weekly_reset_utc,
            "monthly": _next_monthly_reset_utc,
        }[kind]()
        return {
            "status": "cooldown",
            "countdown": _fmt_cooldown(reset_at - now()),
        }

    w, won = _period_stats(user, kind)
    preview = _calc_bonus_amount(kind, w, won)
    if preview <= 0:
        return {"status": "locked", "requirement": "Brak aktywności w tym okresie"}
    return {"status": "ready", "amountPreview": float(preview)}


async def build_vip_payload(user: dict) -> dict:
    tier_idx, progress = vip_tier_info(user)
    bonuses = {k: _bonus_status(user, k, tier_idx) for k in ("daily", "weekly", "monthly", "rank")}
    return {"progress": progress, "bonuses": bonuses}


async def referral_count(referrer_id: int) -> int:
    return await get_db().users.count_documents({"referred_by_id": referrer_id})


async def build_referral_payload(user: dict) -> dict:
    count = await referral_count(user["id"])
    claimed = set(user.get("referral_claimed_tiers") or [])
    tiers = []
    for t in REFERRAL_TIERS:
        tid = t["id"]
        amount = str(int(t["amount_pln"]))
        if tid in claimed:
            tiers.append({"id": tid, "label": t["label"], "amount": amount, "status": "claimed"})
        elif count >= t["required"]:
            tiers.append({"id": tid, "label": t["label"], "amount": amount, "status": "ready"})
        else:
            tiers.append({
                "id": tid,
                "label": t["label"],
                "amount": amount,
                "status": "progress",
                "countdown": f"{count}/{t['required']}",
            })
    return {"code": user["username"], "tiers": tiers}


async def claim_vip_bonus(user: dict, kind: str) -> dict:
    if kind not in BONUS_RATES:
        raise HTTPException(status_code=400, detail="unknown bonus kind")
    tier_idx, _ = vip_tier_info(user)
    status = _bonus_status(user, kind, tier_idx)
    if status["status"] == "locked":
        raise HTTPException(status_code=403, detail=status.get("requirement", "locked"))
    if status["status"] == "claimed":
        raise HTTPException(status_code=400, detail="already claimed")
    if status["status"] != "ready":
        raise HTTPException(status_code=429, detail="cooldown")

    if kind == "rank":
        wagered, won = _wagered(user), _won(user)
        claim_key = tier_idx
        update_filter: dict[str, Any] = {
            "id": user["id"],
            "vip_rank_claimed_tiers": {"$ne": tier_idx},
        }
        claim_set: dict[str, Any] = {"$addToSet": {"vip_rank_claimed_tiers": tier_idx}}
    else:
        wagered, won = _period_stats(user, kind)
        claim_key = _period_key(kind)
        update_filter = {"id": user["id"]}
        claim_set = {"$set": {f"vip_bonus_claims.{kind}": claim_key}}

    amount = _calc_bonus_amount(kind, wagered, won)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="no activity in period")

    db = get_db()
    updated = await db.users.find_one_and_update(
        update_filter,
        {
            "$inc": {"balance_pln": amount, "playthrough_base_pln": amount},
            **claim_set,
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        if kind == "rank":
            raise HTTPException(status_code=409, detail="already claimed")
        raise HTTPException(status_code=404, detail="user not found")
    return {"ok": True, "amount": float(amount), "balance": float(updated["balance_pln"])}


async def claim_referral_tier(user: dict, tier_id: int) -> dict:
    tier = next((t for t in REFERRAL_TIERS if t["id"] == tier_id), None)
    if tier is None:
        raise HTTPException(status_code=400, detail="unknown tier")
    claimed = set(user.get("referral_claimed_tiers") or [])
    if tier_id in claimed:
        raise HTTPException(status_code=400, detail="already claimed")
    count = await referral_count(user["id"])
    if count < tier["required"]:
        raise HTTPException(status_code=403, detail="requirements not met")

    amount = tier["amount_pln"]
    db = get_db()
    updated = await db.users.find_one_and_update(
        {"id": user["id"], "referral_claimed_tiers": {"$ne": tier_id}},
        {
            "$inc": {"balance_pln": amount, "playthrough_base_pln": amount},
            "$addToSet": {"referral_claimed_tiers": tier_id},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="already claimed")
    return {"ok": True, "amount": float(amount), "balance": float(updated["balance_pln"])}


async def attach_referrer(user: dict, ref_username: str) -> dict:
    if user.get("referred_by_id"):
        raise HTTPException(status_code=400, detail="already referred")
    raw_created = user.get("created_at")
    created = as_utc(raw_created) if isinstance(raw_created, datetime) else None
    if created and now() - created > REFERRAL_ATTACH_WINDOW:
        raise HTTPException(status_code=400, detail="referral window closed")

    from .safe_url import normalize_username

    ref_key = normalize_username(ref_username)
    if not ref_key or ref_key == user["username"].lower():
        raise HTTPException(status_code=400, detail="invalid referrer")

    db = get_db()
    referrer = await db.users.find_one({"username": ref_key})
    if referrer is None:
        raise HTTPException(status_code=404, detail="referrer not found")

    await db.users.update_one(
        {"id": user["id"], "referred_by_id": None},
        {"$set": {"referred_by_id": referrer["id"]}},
    )
    return {"ok": True}


async def redeem_code(user: dict, code: str) -> dict:
    from .redeem_codes_service import redeem_code as _redeem

    return await _redeem(user, code)


def _touch_period_bucket(stats: dict, kind: str, stake: Decimal, payout: Decimal) -> None:
    key = _period_key(kind)
    bucket = stats.get(kind) or {}
    if bucket.get("period") != key:
        bucket = {"period": key, "wagered": Decimal(0), "won": Decimal(0)}
    bucket["wagered"] = Decimal(str(bucket.get("wagered") or 0)) + stake
    bucket["won"] = Decimal(str(bucket.get("won") or 0)) + payout
    stats[kind] = bucket


async def record_vip_activity(
    user_id: int,
    stake: Decimal,
    payout: Decimal = Decimal(0),
) -> None:
    """Track wager volume and payouts for VIP XP and periodic bonuses."""
    stake = Decimal(str(stake or 0))
    payout = Decimal(str(payout or 0))
    if stake <= 0 and payout <= 0:
        return

    from .playthrough_service import record_playthrough_wager

    await record_playthrough_wager(user_id, stake)

    db = get_db()
    user = await db.users.find_one({"id": user_id})
    if user is None:
        return

    stats = dict(user.get("vip_period_stats") or {})
    for kind in ("daily", "weekly", "monthly"):
        _touch_period_bucket(stats, kind, stake, payout)

    await db.users.update_one(
        {"id": user_id},
        {
            "$inc": {"vip_wagered_pln": stake, "vip_won_pln": payout},
            "$set": {"vip_period_stats": stats},
        },
    )


async def record_vip_wager(user_id: int, amount: Decimal) -> None:
    """Backward-compatible: stake only."""
    await record_vip_activity(user_id, amount, Decimal(0))
