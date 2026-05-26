"""Shared Wikipedia image fetch + MongoDB preset helpers for admin scraper scripts."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote

import httpx
from PIL import Image

_WIKI_API = "https://en.wikipedia.org/w/api.php"
_WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/summary"
_USER_AGENT = "kwk-preset-scraper/1.0 (local admin script; contact: admin)"
_THUMB_SIZE = 500
_MAX_IMAGE_PX = 480
_WIKI_PAUSE = 0.6


def norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", norm(name))
    return s.strip("_") or "entity"


def wiki_title(name: str) -> str:
    return name.replace(" ", "_")


def load_named_entries(path: Path, *, key: str) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for entry in raw.get(key, []):
        names = [str(n).strip() for n in entry.get("names", []) if str(n).strip()]
        if not names:
            continue
        out.append({"preset_name": names[0], "names": names})
    return out


async def wiki_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[dict] = None,
    pause: Callable[[], Any],
    log: logging.Logger,
) -> httpx.Response:
    for attempt in range(6):
        await pause()
        r = await client.get(url, params=params)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        retry_after = r.headers.get("Retry-After")
        wait = float(retry_after) if retry_after and retry_after.isdigit() else min(60, 2 ** attempt * 3)
        log.warning("Wikipedia rate limit (429), waiting %.0fs (attempt %d)", wait, attempt + 1)
        await asyncio.sleep(wait)
    r.raise_for_status()
    return r


async def wiki_rest_thumbnail(
    client: httpx.AsyncClient, title: str, pause: Callable[[], Any], log: logging.Logger
) -> Optional[str]:
    path = quote(wiki_title(title), safe="/()")
    try:
        r = await wiki_get(client, f"{_WIKI_REST}/{path}", pause=pause, log=log)
    except httpx.HTTPError:
        return None
    if r.status_code == 404:
        return None
    data = r.json()
    thumb = (data.get("thumbnail") or {}).get("source")
    return str(thumb) if thumb else None


async def wiki_search(
    client: httpx.AsyncClient, query: str, pause: Callable[[], Any], log: logging.Logger
) -> list[dict[str, str]]:
    r = await wiki_get(
        client,
        _WIKI_API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 8,
            "format": "json",
        },
        pause=pause,
        log=log,
    )
    return (r.json().get("query") or {}).get("search") or []


async def wiki_thumbnail(
    client: httpx.AsyncClient, page_title: str, pause: Callable[[], Any], log: logging.Logger
) -> Optional[str]:
    r = await wiki_get(
        client,
        _WIKI_API,
        params={
            "action": "query",
            "titles": page_title,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": _THUMB_SIZE,
            "format": "json",
        },
        pause=pause,
        log=log,
    )
    pages = (r.json().get("query") or {}).get("pages") or {}
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        if thumb:
            return str(thumb)
    return None


async def fetch_image_url(
    client: httpx.AsyncClient,
    entity: dict[str, Any],
    *,
    title_candidates: list[str],
    search_queries: list[str],
    pick_title: Callable[[list[dict[str, str]], str], Optional[str]],
    pause: Callable[[], Any],
    log: logging.Logger,
) -> Optional[str]:
    primary = entity["preset_name"]
    seen: set[str] = set()
    for title in title_candidates:
        t = title.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        thumb = await wiki_rest_thumbnail(client, t, pause, log)
        if thumb:
            log.info("Found %s via REST title %r", primary, t)
            return thumb

    for query in search_queries:
        try:
            hits = await wiki_search(client, query, pause, log)
        except httpx.HTTPError as exc:
            log.warning("Wikipedia search failed for %r: %s", query, exc)
            continue
        title = pick_title(hits, primary)
        if not title:
            continue
        try:
            thumb = await wiki_thumbnail(client, title, pause, log)
        except httpx.HTTPError as exc:
            log.warning("Wikipedia thumbnail failed for %r: %s", title, exc)
            continue
        if thumb:
            log.info("Found %s via search %r", title, query)
            return thumb
    return None


async def download_image(
    client: httpx.AsyncClient, url: str, pause: Callable[[], Any], log: logging.Logger
) -> Optional[bytes]:
    try:
        r = await wiki_get(client, url, pause=pause, log=log)
        if not r.content or not (r.headers.get("content-type") or "").startswith("image"):
            return None
        return r.content
    except httpx.HTTPError as exc:
        log.warning("Image download failed %s: %s", url, exc)
        return None


def prepare_image(raw: bytes) -> tuple[bytes, str]:
    img = Image.open(BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    else:
        img = img.convert("RGB")

    w, h = img.size
    scale = min(1.0, _MAX_IMAGE_PX / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue(), "image/jpeg"


def to_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def existing_name_sets(rows: list[dict]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        payload = row.get("payload") or {}
        for n in payload.get("names") or []:
            n = norm(str(n))
            if n:
                out.add(n)
        name = norm(str(row.get("name") or ""))
        if name:
            out.add(name)
    return out


def entity_has_preset(entity: dict[str, Any], existing: set[str]) -> bool:
    for n in entity["names"]:
        if norm(n) in existing:
            return True
    return False


def find_existing_preset(entity: dict[str, Any], rows: list[dict]) -> Optional[dict]:
    entity_norms = {norm(n) for n in entity["names"]}
    for row in rows:
        payload = row.get("payload") or {}
        row_norms = {norm(str(n)) for n in (payload.get("names") or [])}
        row_norms.add(norm(str(row.get("name") or "")))
        if entity_norms & row_norms:
            return row
    return None


async def load_existing_presets() -> list[dict]:
    from app.db import get_db

    return await get_db().presets.find().to_list(500)


async def save_preset(
    *,
    preset_name: str,
    names: list[str],
    image_url: str,
    dry_run: bool,
    replace: bool,
    existing_row: Optional[dict],
) -> dict[str, Any]:
    if dry_run:
        action = "would_update" if existing_row and replace else "would_create"
        return {"dryRun": True, "action": action, "name": preset_name, "names": names}

    from app.db import get_db, next_id, now
    from app.preset_matching import apply_preset_to_eligible_markets, union_preset_names

    payload = {"imageUrl": image_url, "names": names}

    match_names = names
    if existing_row and replace:
        old_payload = existing_row.get("payload") or {}
        match_names = union_preset_names(
            names,
            old_payload.get("names"),
            preset_name,
            existing_row.get("name"),
        )
    applied = await apply_preset_to_eligible_markets(
        image_url,
        match_names,
        refresh_existing=bool(existing_row and replace),
    )

    if existing_row and replace:
        preset_id = existing_row["id"]
        await get_db().presets.update_one(
            {"id": preset_id},
            {"$set": {"name": preset_name, "payload": payload}},
        )
        return {
            "id": preset_id,
            "name": preset_name,
            "action": "updated",
            "appliedCount": len(applied),
        }

    preset_id = await next_id("presets")
    created = now()
    await get_db().presets.insert_one(
        {
            "id": preset_id,
            "name": preset_name,
            "payload": payload,
            "created_at": created,
        }
    )
    return {
        "id": preset_id,
        "name": preset_name,
        "action": "created",
        "appliedCount": len(applied),
    }


async def process_entity(
    client: httpx.AsyncClient,
    entity: dict[str, Any],
    *,
    entity_label: str,
    image_dir: Path,
    fetch_image: Callable[..., Any],
    existing_names: set[str],
    existing_rows: list[dict],
    dry_run: bool,
    save_files: bool,
    skip_existing: bool,
    replace: bool,
    pause: Callable[[], Any],
    log: logging.Logger,
) -> dict[str, Any]:
    name = entity["preset_name"]
    result: dict[str, Any] = {entity_label: name, "status": "pending"}
    existing_row = find_existing_preset(entity, existing_rows)

    if skip_existing and not replace and entity_has_preset(entity, existing_names):
        result["status"] = "skipped"
        result["reason"] = "preset already exists"
        return result

    thumb_url = await fetch_image(client, entity, pause)
    if not thumb_url:
        result["status"] = "failed"
        result["reason"] = "no image found"
        return result

    raw = await download_image(client, thumb_url, pause, log)
    if not raw:
        result["status"] = "failed"
        result["reason"] = "download failed"
        return result

    jpeg, mime = prepare_image(raw)
    data_url = to_data_url(jpeg, mime)

    if save_files:
        image_dir.mkdir(parents=True, exist_ok=True)
        path = image_dir / f"{slug(name)}.jpg"
        path.write_bytes(jpeg)
        result["savedFile"] = str(path)

    saved = await save_preset(
        preset_name=name,
        names=entity["names"],
        image_url=data_url,
        dry_run=dry_run,
        replace=replace,
        existing_row=existing_row,
    )
    action = saved.get("action", "created")
    if dry_run:
        result["status"] = "dry_run"
    elif action == "updated":
        result["status"] = "updated"
    else:
        result["status"] = "created"
    result.update(saved)
    for alias in entity["names"]:
        existing_names.add(norm(alias))
    return result


def make_wiki_pause() -> tuple[asyncio.Lock, list[float], Callable[[], Any]]:
    wiki_lock = asyncio.Lock()
    last_wiki = [0.0]

    async def wiki_pause() -> None:
        async with wiki_lock:
            elapsed = asyncio.get_event_loop().time() - last_wiki[0]
            if elapsed < _WIKI_PAUSE:
                await asyncio.sleep(_WIKI_PAUSE - elapsed)
            last_wiki[0] = asyncio.get_event_loop().time()

    return wiki_lock, last_wiki, wiki_pause


async def run_scraper(
    *,
    entities: list[dict[str, Any]],
    entity_label: str,
    image_dir: Path,
    fetch_image: Callable[..., Any],
    dry_run: bool,
    replace: bool,
    save_files: bool,
    delay: float,
    log: logging.Logger,
) -> list[dict[str, Any]]:
    from app.db import close_db, init_db

    await init_db()
    try:
        existing_rows = await load_existing_presets()
        existing_names = existing_name_sets(existing_rows)
        mode = "replace" if replace else "skip existing"
        log.info(
            "Loaded %d entities (%d preset aliases, mode=%s, delay=%.1fs)",
            len(entities),
            len(existing_names),
            mode,
            delay,
        )

        headers = {"User-Agent": _USER_AGENT}
        timeout = httpx.Timeout(60.0)
        results: list[dict[str, Any]] = []
        _, _, wiki_pause = make_wiki_pause()

        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            for i, entity in enumerate(entities):
                log.info("[%d/%d] %s", i + 1, len(entities), entity["preset_name"])
                row = await process_entity(
                    client,
                    entity,
                    entity_label=entity_label,
                    image_dir=image_dir,
                    fetch_image=fetch_image,
                    existing_names=existing_names,
                    existing_rows=existing_rows,
                    dry_run=dry_run,
                    save_files=save_files,
                    skip_existing=not replace,
                    replace=replace,
                    pause=wiki_pause,
                    log=log,
                )
                results.append(row)
                extra = f" ({row['reason']})" if row.get("reason") else ""
                log.info("  -> %s%s", row.get("status"), extra)
                if i + 1 < len(entities) and delay > 0:
                    await asyncio.sleep(delay)
        return results
    finally:
        await close_db()


def print_summary(results: list[dict[str, Any]], *, dry_run: bool) -> dict[str, int]:
    summary = {
        "total": len(results),
        "created": sum(1 for r in results if r.get("status") == "created"),
        "updated": sum(1 for r in results if r.get("status") == "updated"),
        "dryRun": sum(1 for r in results if r.get("status") == "dry_run"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
    }
    print(json.dumps({"summary": summary, "results": results}, indent=2, default=str))
    if summary["failed"] and not dry_run:
        raise SystemExit(1)
    return summary


def pick_title_by_score(
    results: list[dict[str, str]],
    primary_name: str,
    *,
    score_hit: Callable[[dict[str, str], str, set[str]], int],
    min_score: int = 10,
) -> Optional[str]:
    if not results:
        return None
    name_l = norm(primary_name)
    name_parts = set(name_l.split())
    ranked = sorted(results, key=lambda hit: score_hit(hit, name_l, name_parts), reverse=True)
    best = ranked[0]
    if score_hit(best, name_l, name_parts) < min_score:
        return None
    return best.get("title")
