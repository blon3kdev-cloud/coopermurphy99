"""iSports API client — schedule, odds, live data with per-path rate limits."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

import httpx

from .config import get_settings
from .isports_bookmakers import all_eu_company_ids, all_main_company_ids, get_bookmaker_pref

log = logging.getLogger(__name__)

BASE_URLS = ("http://api.isportsapi.com", "http://api2.isportsapi.com")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36"
)

# Minimum seconds between calls per API path (from docs).
_PATH_COOLDOWN_SEC: dict[str, float] = {
    "/sport/football/schedule/basic": 60.0,
    "/sport/football/liveanimation/schedule": 60.0,
    "/sport/football/stats": 10.0,
    "/sport/football/odds/main": 10.0,
    "/sport/football/odds/cornerstotal/prematch": 10.0,
    "/sport/football/odds/bothScore": 10.0,
    "/sport/football/odds/teamGoals": 10.0,
    "/sport/football/topscorer": 10.0,
    "/sport/football/playerstats/match": 10.0,
    "/sport/football/odds/european/all": 60.0,
    "/sport/basketball/schedule/basic": 60.0,
    "/sport/basketball/odds/fulltime": 10.0,
}

_last_call: dict[str, float] = {}
_path_locks: dict[str, asyncio.Lock] = {}


def _path_lock(path: str) -> asyncio.Lock:
    lock = _path_locks.get(path)
    if lock is None:
        lock = asyncio.Lock()
        _path_locks[path] = lock
    return lock


def odds_bookmaker_label() -> str:
    return get_bookmaker_pref().label


def _company_ids_param(ids: tuple[str, ...]) -> Optional[str]:
    return ",".join(ids) if ids else None


def preferred_main_company_ids(*, sub_markets: bool = False) -> tuple[str, ...]:
    pref = get_bookmaker_pref()
    return pref.sub_market_main_ids if sub_markets else (pref.main_ids or pref.sub_market_main_ids)


def preferred_eu_company_ids() -> tuple[str, ...]:
    return get_bookmaker_pref().eu_ids


def to_decimal_odds(raw: float) -> float:
    """Convert iSports HK-style prices (<2) to European decimal odds."""
    if raw <= 0:
        return 0.0
    if raw >= 2.0:
        return raw
    return raw + 1.0


class IsportsNotConfiguredError(ValueError):
    """Raised when I_SPORTS_API_KEY is missing."""


def _parse_json_body(text: str) -> Any:
    """Parse iSports JSON; repair known API typo before changeTime."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = text.replace('""changeTime', '","changeTime')
        if repaired != text:
            return json.loads(repaired)
        raise


def _api_key() -> str:
    key = get_settings().isports_api_key.strip()
    if not key:
        raise IsportsNotConfiguredError("I_SPORTS_API_KEY is not configured")
    return key


async def _throttle(path: str) -> None:
    """Per-endpoint cooldown (docs); different paths may run in parallel."""
    cooldown = _PATH_COOLDOWN_SEC.get(path, 10.0)
    async with _path_lock(path):
        last = _last_call.get(path, 0.0)
        wait = cooldown - (time.monotonic() - last)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call[path] = time.monotonic()


async def _get(path: str, *, params: Optional[dict[str, Any]] = None) -> Any:
    await _throttle(path)
    p = dict(params or {})
    p["api_key"] = _api_key()
    last_exc: Exception | None = None
    for base in BASE_URLS:
        url = f"{base}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(
                    url,
                    params=p,
                    headers={"User-Agent": USER_AGENT},
                )
                res.raise_for_status()
                body = _parse_json_body(res.text)
        except Exception as exc:
            last_exc = exc
            log.warning("isports request failed %s: %s", url, exc)
            continue
        if not isinstance(body, dict):
            raise ValueError("invalid isports response")
        code = body.get("code")
        if code != 0:
            msg = body.get("message") or "isports error"
            raise ValueError(f"isports code {code}: {msg}")
        return body.get("data")
    if last_exc:
        raise last_exc
    raise ValueError("isports unreachable")


def _chunk_ids(ids: list[str], size: int = 100) -> list[str]:
    return [",".join(ids[i : i + size]) for i in range(0, len(ids), size)]


async def fetch_schedule_by_date(date: str) -> list[dict]:
    """date: YYYY-MM-DD (GMT+0 day)."""
    data = await _get("/sport/football/schedule/basic", params={"date": date})
    return data if isinstance(data, list) else []


async def fetch_basketball_schedule_by_date(date: str) -> list[dict]:
    """date: YYYY-MM-DD (GMT+0 day)."""
    data = await _get("/sport/basketball/schedule/basic", params={"date": date})
    return data if isinstance(data, list) else []


async def fetch_basketball_schedule_by_match_ids(match_ids: list[str]) -> list[dict]:
    if not match_ids:
        return []
    out: list[dict] = []
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        data = await _get("/sport/basketball/schedule/basic", params={"matchId": chunk})
        if isinstance(data, list):
            out.extend(data)
    return out


async def fetch_basketball_odds_fulltime() -> dict[str, Any]:
    """Pre-match + in-play money line / spread / total for all open basketball matches."""
    data = await _get("/sport/basketball/odds/fulltime")
    return data if isinstance(data, dict) else {}


async def fetch_schedule_by_match_ids(match_ids: list[str]) -> list[dict]:
    if not match_ids:
        return []
    out: list[dict] = []
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        data = await _get("/sport/football/schedule/basic", params={"matchId": chunk})
        if isinstance(data, list):
            out.extend(data)
    return out


async def fetch_liveanimation_schedule() -> list[dict]:
    data = await _get("/sport/football/liveanimation/schedule")
    return data if isinstance(data, list) else []


async def fetch_odds_main(
    match_ids: list[str],
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> dict[str, Any]:
    if not match_ids:
        return {}
    merged: dict[str, Any] = {
        "handicap": [],
        "europeOdds": [],
        "overUnder": [],
        "handicapHalf": [],
        "overUnderHalf": [],
    }
    cids = company_ids if company_ids is not None else preferred_main_company_ids()
    cid_param = _company_ids_param(cids)
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        params: dict[str, Any] = {"matchId": chunk}
        if cid_param:
            params["companyId"] = cid_param
        data = await _get("/sport/football/odds/main", params=params)
        if not isinstance(data, dict):
            continue
        for key in merged:
            rows = data.get(key)
            if isinstance(rows, list):
                merged[key].extend(rows)
    return merged


async def fetch_european_1x2(
    match_ids: list[str],
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> dict[str, tuple[float, float, float]]:
    """1X2 from European (200+) bookmakers — used for Betclic and similar."""
    cids = company_ids if company_ids is not None else preferred_eu_company_ids()
    if not match_ids or not cids:
        return {}
    out: dict[str, tuple[float, float, float]] = {}
    cid_param = _company_ids_param(cids)
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        params: dict[str, Any] = {"matchId": chunk}
        if cid_param:
            params["companyId"] = cid_param
        try:
            data = await _get("/sport/football/odds/european/all", params=params)
        except Exception as exc:
            log.warning("isports european 1x2 unavailable for %s: %s", chunk, exc)
            continue
        if not isinstance(data, list):
            continue
        for row in data:
            mid = str(row.get("matchId", ""))
            if not mid:
                continue
            triple = _europe_triple_from_eu_row(row, cids)
            if triple:
                out[mid] = triple
    return out


async def fetch_european_rows(match_ids: list[str]) -> list[dict]:
    """Raw European 1X2 rows for all known EU bookmakers (one API round-trip)."""
    cids = all_eu_company_ids()
    if not match_ids or not cids:
        return []
    out: list[dict] = []
    cid_param = _company_ids_param(cids)
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        params: dict[str, Any] = {"matchId": chunk}
        if cid_param:
            params["companyId"] = cid_param
        try:
            data = await _get("/sport/football/odds/european/all", params=params)
        except Exception as exc:
            log.warning("isports european rows unavailable for %s: %s", chunk, exc)
            continue
        if isinstance(data, list):
            out.extend(data)
    return out


def pick_europe_from_rows(
    rows: list[dict],
    match_id: str,
    company_ids: tuple[str, ...],
) -> Optional[tuple[float, float, float]]:
    """Pick 1X2 from cached European API rows for specific bookmaker IDs."""
    if not company_ids:
        return None
    mid = str(match_id)
    for row in rows:
        if str(row.get("matchId", "")) != mid:
            continue
        triple = _europe_triple_from_eu_row(row, company_ids)
        if triple:
            return triple
    return None


def _europe_triple_from_eu_row(
    row: dict,
    company_ids: tuple[str, ...],
) -> Optional[tuple[float, float, float]]:
    for odds_row in row.get("odds") or []:
        detail = str(odds_row.get("oddsDetail", ""))
        parts = _parse_csv_row(detail)
        if len(parts) < 8:
            continue
        cid = parts[0]
        if company_ids and cid not in company_ids:
            continue
        try:
            home = float(parts[5])
            draw = float(parts[6])
            away = float(parts[7])
        except ValueError:
            try:
                home = float(parts[2])
                draw = float(parts[3])
                away = float(parts[4])
            except ValueError:
                continue
        if home > 0 and away > 0:
            return home, draw, away
    return None


async def fetch_corners_total(
    match_ids: list[str],
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> list[dict]:
    if not match_ids:
        return []
    out: list[dict] = []
    cids = company_ids if company_ids is not None else preferred_main_company_ids(sub_markets=True)
    cid_param = _company_ids_param(cids)
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        params: dict[str, Any] = {"matchId": chunk}
        if cid_param:
            params["companyId"] = cid_param
        data = await _get(
            "/sport/football/odds/cornerstotal/prematch",
            params=params,
        )
        if isinstance(data, list):
            out.extend(data)
    return out


async def fetch_top_scorers(league_id: str, season: Optional[str] = None) -> list[dict]:
    params: dict[str, Any] = {"leagueId": str(league_id)}
    if season:
        params["season"] = season
    data = await _get("/sport/football/topscorer", params=params)
    return data if isinstance(data, list) else []


async def fetch_player_stats_match(match_id: str) -> list[dict]:
    data = await _get(
        "/sport/football/playerstats/match",
        params={"matchId": str(match_id)},
    )
    return data if isinstance(data, list) else []


async def fetch_team_goals(match_ids: list[str]) -> list[dict]:
    if not match_ids:
        return []
    out: list[dict] = []
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        try:
            data = await _get("/sport/football/odds/teamGoals", params={"matchId": chunk})
        except Exception as exc:
            log.warning("isports teamGoals unavailable for %s: %s", chunk, exc)
            continue
        if isinstance(data, list):
            out.extend(data)
    return out


async def fetch_both_score(
    match_ids: list[str],
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> list[dict]:
    if not match_ids:
        return []
    out: list[dict] = []
    cids = company_ids if company_ids is not None else preferred_main_company_ids(sub_markets=True)
    cid_param = _company_ids_param(cids)
    for chunk in _chunk_ids([str(m) for m in match_ids]):
        params: dict[str, Any] = {"matchId": chunk}
        if cid_param:
            params["companyId"] = cid_param
        try:
            data = await _get("/sport/football/odds/bothScore", params=params)
        except Exception as exc:
            log.warning("isports bothScore unavailable for %s: %s", chunk, exc)
            continue
        if isinstance(data, list):
            out.extend(data)
    return out


def _parse_csv_row(row: str) -> list[str]:
    return [p.strip() for p in str(row).split(",")]


def _europe_triple(parts: list[str]) -> Optional[tuple[float, float, float]]:
    """Prefer instant 1x2 prices; fall back to initial."""
    try:
        if len(parts) >= 8:
            home, draw, away = float(parts[5]), float(parts[6]), float(parts[7])
        else:
            home, draw, away = float(parts[2]), float(parts[3]), float(parts[4])
    except (ValueError, IndexError):
        return None
    if home > 0 and away > 0:
        return home, draw, away
    return None


def pick_europe_odds(
    rows: list[str],
    match_id: str,
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> Optional[tuple[float, float, float]]:
    """Return (home, draw, away) decimal odds for preferred main-API bookmaker."""
    mid = str(match_id)
    companies = company_ids if company_ids is not None else preferred_main_company_ids()
    for company in companies:
        for row in rows:
            parts = _parse_csv_row(row)
            if len(parts) < 6 or parts[0] != mid or parts[1] != company:
                continue
            triple = _europe_triple(parts)
            if triple:
                return triple
    for row in rows:
        parts = _parse_csv_row(row)
        if len(parts) < 6 or parts[0] != mid:
            continue
        triple = _europe_triple(parts)
        if triple:
            return triple
    return None


def pick_goals_over_lines(
    rows: list[str],
    match_id: str,
    *,
    preferred: tuple[float, ...] = (1.5, 2.5, 3.5),
    max_lines: int = 3,
) -> list[tuple[float, float, float]]:
    """Goal O/U lines: preferred totals first, then other sane match-total lines."""
    all_lines = pick_over_under(rows, match_id)
    if not all_lines:
        return []
    by_line = {line: (line, over, under) for line, over, under in all_lines}
    out: list[tuple[float, float, float]] = []
    for line in preferred:
        if line in by_line:
            out.append(by_line[line])
    if len(out) < max_lines:
        for line, pair in sorted(by_line.items()):
            if line in preferred or line < 0.5 or line > 5.5:
                continue
            if pair not in out:
                out.append(pair)
            if len(out) >= max_lines:
                break
    return out[:max_lines]


def pick_over_under(
    rows: list[str],
    match_id: str,
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> list[tuple[float, float, float]]:
    """Return list of (line, over, under) for match."""
    mid = str(match_id)
    found: list[tuple[float, float, float]] = []
    seen_lines: set[float] = set()
    companies = company_ids if company_ids is not None else preferred_main_company_ids(sub_markets=True)
    for company in companies:
        for row in rows:
            parts = _parse_csv_row(row)
            if len(parts) < 6 or parts[0] != mid or parts[1] != company:
                continue
            try:
                line = float(parts[2])
                if len(parts) >= 8:
                    over_odds = float(parts[6])
                    under_odds = float(parts[7])
                else:
                    over_odds = float(parts[3])
                    under_odds = float(parts[4])
            except ValueError:
                continue
            over_odds = to_decimal_odds(over_odds)
            under_odds = to_decimal_odds(under_odds)
            if line in seen_lines or over_odds <= 1 or under_odds <= 1:
                continue
            seen_lines.add(line)
            found.append((line, over_odds, under_odds))
    if found:
        return found
    for row in rows:
        parts = _parse_csv_row(row)
        if len(parts) < 6 or parts[0] != mid:
            continue
        try:
            line = float(parts[2])
            if len(parts) >= 8:
                over_odds = float(parts[6])
                under_odds = float(parts[7])
            else:
                over_odds = float(parts[3])
                under_odds = float(parts[4])
        except ValueError:
            continue
        over_odds = to_decimal_odds(over_odds)
        under_odds = to_decimal_odds(under_odds)
        if line in seen_lines or over_odds <= 1 or under_odds <= 1:
            continue
        seen_lines.add(line)
        found.append((line, over_odds, under_odds))
    return found


def _company_priority(company_id: str, *, sub_markets: bool = False) -> int:
    pref = preferred_main_company_ids(sub_markets=sub_markets)
    try:
        return pref.index(str(company_id))
    except ValueError:
        return len(pref)


def _parse_btts_pair(row: dict) -> Optional[tuple[float, float]]:
    """Parse BTTS yes/no; skip stale rows (API returns multiple per bookmaker)."""
    try:
        yes_odds = to_decimal_odds(float(row.get("yes", 0)))
        no_odds = to_decimal_odds(float(row.get("no", 0)))
    except (TypeError, ValueError):
        return None
    if yes_odds <= 1 or no_odds <= 1 or yes_odds > 8 or no_odds > 8:
        return None
    # Bad snapshot e.g. yes=4.0, no=1.44 (inverted / closed market).
    if yes_odds >= 3.0 and no_odds < 1.6:
        return None
    if yes_odds > no_odds:
        yes_odds, no_odds = no_odds, yes_odds
    return yes_odds, no_odds


def pick_corners_row(rows: list[dict], match_id: str) -> Optional[tuple[float, float, float]]:
    mid = str(match_id)
    best: Optional[tuple[int, int, float, float, float]] = None
    for row in rows:
        if str(row.get("matchId")) != mid:
            continue
        odds = row.get("odds") or {}
        try:
            line = float(odds.get("totalCorners", 0))
            over_odds = to_decimal_odds(float(odds.get("over", 0)))
            under_odds = to_decimal_odds(float(odds.get("under", 0)))
        except (TypeError, ValueError):
            continue
        if line <= 0 or over_odds <= 1 or under_odds <= 1:
            continue
        try:
            change_time = int(row.get("changeTime") or 0)
        except (TypeError, ValueError):
            change_time = 0
        rank = (_company_priority(str(row.get("companyId", "")), sub_markets=True), -change_time)
        if best is None or rank < best[:2]:
            best = (rank[0], rank[1], line, over_odds, under_odds)
    if best is None:
        return None
    return best[2], best[3], best[4]


def pick_btts_row(rows: list[dict], match_id: str) -> Optional[tuple[float, float]]:
    mid = str(match_id)
    best: Optional[tuple[int, int, float, float]] = None
    for row in rows:
        if str(row.get("matchId")) != mid:
            continue
        pair = _parse_btts_pair(row)
        if not pair:
            continue
        yes_odds, no_odds = pair
        try:
            change_time = int(row.get("changeTime") or 0)
        except (TypeError, ValueError):
            change_time = 0
        rank = (_company_priority(str(row.get("companyId", "")), sub_markets=True), -change_time)
        if best is None or rank < best[:2]:
            best = (rank[0], rank[1], yes_odds, no_odds)
    if best is None:
        return None
    return best[2], best[3]


def _moneyline_pair(parts: list[str]) -> Optional[tuple[float, float]]:
    """Basketball moneyLine CSV: matchId, companyId, initHome, initAway, instantHome, instantAway."""
    try:
        if len(parts) >= 6:
            home = float(parts[4])
            away = float(parts[5])
        else:
            home = float(parts[2])
            away = float(parts[3])
    except (ValueError, IndexError):
        return None
    home = to_decimal_odds(home)
    away = to_decimal_odds(away)
    if home > 1 and away > 1:
        return home, away
    return None


def pick_basketball_moneyline(
    rows: list[str],
    match_id: str,
    *,
    company_ids: Optional[tuple[str, ...]] = None,
) -> Optional[tuple[float, float]]:
    """Return (home, away) decimal money line for preferred bookmaker."""
    mid = str(match_id)
    companies = company_ids if company_ids is not None else preferred_main_company_ids()
    for company in companies:
        for row in rows:
            parts = _parse_csv_row(row)
            if len(parts) < 4 or parts[0] != mid or parts[1] != company:
                continue
            pair = _moneyline_pair(parts)
            if pair:
                return pair
    for row in rows:
        parts = _parse_csv_row(row)
        if len(parts) < 4 or parts[0] != mid:
            continue
        pair = _moneyline_pair(parts)
        if pair:
            return pair
    return None


def pick_match_winner_odds(
    match_id: str,
    *,
    european_1x2: Optional[dict[str, tuple[float, float, float]]] = None,
    main_europe_rows: Optional[list[str]] = None,
) -> Optional[tuple[float, float, float]]:
    """Preferred bookmaker 1X2; European API first (Betclic), then main API."""
    mid = str(match_id)
    if european_1x2 and mid in european_1x2:
        return european_1x2[mid]
    rows = main_europe_rows or []
    return pick_europe_odds(rows, mid)


def pick_team_scores(
    rows: list[dict], match_id: str
) -> Optional[tuple[Optional[tuple[float, float]], Optional[tuple[float, float]]]]:
    """Return ((home_over, home_under), (away_over, away_under)) for team to score (line 0.5)."""
    mid = str(match_id)
    for company in preferred_main_company_ids(sub_markets=True):
        for row in rows:
            if str(row.get("matchId")) != mid or str(row.get("companyId")) != company:
                continue
            home_pair = _team_scores_pair(row.get("home") or {})
            away_pair = _team_scores_pair(row.get("away") or {})
            if home_pair or away_pair:
                return home_pair, away_pair
    for row in rows:
        if str(row.get("matchId")) != mid:
            continue
        home_pair = _team_scores_pair(row.get("home") or {})
        away_pair = _team_scores_pair(row.get("away") or {})
        if home_pair or away_pair:
            return home_pair, away_pair
    return None


def _team_scores_pair(side: dict) -> Optional[tuple[float, float]]:
    """Over/under for team to score at least once (prefer total line 0.5)."""
    try:
        line = float(side.get("total", 0))
        over_o = float(side.get("over", 0))
        under_o = float(side.get("under", 0))
    except (TypeError, ValueError):
        return None
    if line > 1.01:
        return None
    over_o = to_decimal_odds(over_o)
    under_o = to_decimal_odds(under_o)
    if over_o <= 1 or under_o <= 1:
        return None
    return over_o, under_o


def match_time_dt(match: dict):
    from datetime import datetime, timezone

    ts = match.get("matchTime")
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
