"""FastAPI entrypoint — wires DB, BTC price feed, CORS, rate limiting, headers."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from . import btc_price
from .config import get_settings
from .db import close_db, init_db
from .isports_queue import prewarm_schedule_cache
from .isports_daily_auto import run_daily_isports_maintenance
from .isports_odds_refresh import refresh_main_odds, refresh_side_odds
from .crash_engine import get_crash_engine
from .dev_seed import seed_dev_data
from .http_errors import (
    http_exception_handler,
    request_id_middleware,
    request_validation_handler,
)
from .rate_limit import limiter
from .safe_url import validate_production_secrets
from .session_cookies import validate_csrf
from .payments.startup_check import verify_master_addresses
from .blik.settings_store import get_admin_flags
from .routers import (
    admin,
    auth,
    bitcoin,
    blik,
    crypto_bets,
    games,
    crash,
    internal,
    markets,
    payments,
    rewards,
    site,
    user_bets,
    wallet,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

settings = get_settings()
_isports_scheduler: AsyncIOScheduler | None = None

validate_production_secrets()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _isports_scheduler
    if settings.payments_enabled:
        verify_master_addresses()

    async def _pending_sweeps_loop() -> None:
        from .payments.service import PaymentService

        sweep_log = logging.getLogger("payments.sweep")
        interval = max(30, settings.sweep_poll_interval_sec)
        while True:
            try:
                n = await PaymentService.process_pending_sweeps()
                if n:
                    sweep_log.info("checked %s deposit(s) for sweep", n)
            except Exception:
                sweep_log.exception("pending sweep loop error")
            await asyncio.sleep(interval)

    await init_db()
    if settings.payments_enabled and settings.payment_auto_sweep:
        asyncio.create_task(_pending_sweeps_loop())
    await seed_dev_data()
    await get_crash_engine().start()
    await btc_price.start()
    if settings.isports_api_key.strip():
        import asyncio as _asyncio

        _asyncio.create_task(prewarm_schedule_cache())
        _isports_scheduler = AsyncIOScheduler()
        warsaw = ZoneInfo("Europe/Warsaw")

        async def _daily_isports() -> None:
            try:
                await run_daily_isports_maintenance()
            except Exception:
                logging.getLogger("app").exception("daily isports maintenance failed")

        async def _odds_main() -> None:
            try:
                await refresh_main_odds()
            except Exception:
                logging.getLogger("app").exception("isports main odds refresh failed")

        async def _odds_side() -> None:
            try:
                await refresh_side_odds()
            except Exception:
                logging.getLogger("app").exception("isports side odds refresh failed")

        _isports_scheduler.add_job(
            _daily_isports,
            CronTrigger(hour=0, minute=0, timezone=warsaw),
            id="isports_daily",
            replace_existing=True,
        )
        _isports_scheduler.add_job(
            _odds_main,
            "interval",
            hours=1,
            id="isports_odds_main",
            replace_existing=True,
        )
        _isports_scheduler.add_job(
            _odds_side,
            "interval",
            hours=6,
            id="isports_odds_side",
            replace_existing=True,
        )
        _isports_scheduler.start()
    try:
        yield
    finally:
        if _isports_scheduler is not None:
            _isports_scheduler.shutdown(wait=False)
            _isports_scheduler = None
        await btc_price.stop()
        await get_crash_engine().stop()
        await close_db()


app = FastAPI(
    title="czutka backend",
    version="1.0",
    docs_url="/api/docs" if settings.node_env != "production" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.node_env != "production" else None,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=500)
if settings.trusted_proxy:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

_PUBLIC_GET_CACHE_SEC: dict[str, int] = {
    "/api/markets": 30,
    "/api/markets/featured": 30,
    "/api/crypto-bets": 15,
    "/api/crypto-bets/featured": 8,
    "/api/site/status": 5,
}

_MAINTENANCE_BYPASS_PREFIXES = (
    "/api/admin",
    "/api/health",
    "/api/site",
)


# ── CORS — strict origin allowlist ───────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-internal-secret", "X-CSRF-Token"],
    max_age=600,
)


# ── Request ID (correlation, no internals in body) ─────────────────────────────

@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    return await request_id_middleware(request, call_next)


# ── CSRF (cookie sessions) ───────────────────────────────────────────────────

@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    validate_csrf(request)
    return await call_next(request)


@app.middleware("http")
async def site_maintenance_guard(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    for prefix in _MAINTENANCE_BYPASS_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)
    flags = await get_admin_flags()
    if flags.get("siteUnavailable"):
        return JSONResponse(
            status_code=503,
            content={"error": "site_unavailable"},
        )
    return await call_next(request)


# ── Security headers ─────────────────────────────────────────────────────────

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET":
        path = request.url.path.rstrip("/") or "/"
        max_age = _PUBLIC_GET_CACHE_SEC.get(path)
        if max_age is not None:
            response.headers["Cache-Control"] = f"public, max-age={max_age}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["X-Robots-Tag"] = (
        "noindex, nofollow, noarchive, nosnippet, noimageindex"
    )
    if not settings.is_development:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    if not settings.is_development:
        response.headers["Content-Security-Policy-Report-Only"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
    rid = getattr(request.state, "request_id", None)
    if rid:
        response.headers["X-Request-Id"] = rid
    if "server" in response.headers:
        del response.headers["server"]
    return response


# ── Generic error handler — never leak internals ─────────────────────────────

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", None)
    logging.getLogger("app").exception(
        "unhandled request_id=%s path=%s",
        rid,
        request.url.path,
        exc_info=exc,
    )
    headers = {"X-Request-Id": rid} if rid else None
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error"},
        headers=headers,
    )


app.include_router(auth.router)
app.include_router(internal.router)
app.include_router(payments.router)
app.include_router(blik.public_router)
app.include_router(blik.internal_router)
app.include_router(wallet.router)
app.include_router(markets.router)
app.include_router(crypto_bets.router)
app.include_router(user_bets.router)
app.include_router(rewards.router)
app.include_router(games.router)
app.include_router(crash.router)
app.include_router(bitcoin.router)
app.include_router(admin.router)
app.include_router(site.router)


@app.get("/api/health")
async def health() -> dict:
    snap = btc_price.snapshot()
    return {"ok": True, "btc": snap["price"] is not None}
