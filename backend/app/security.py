"""Password hashing, OTP, bearer-token sessions, internal-secret guard.

All comparisons go through `hmac.compare_digest` (constant time).
Bearer tokens are 32 random bytes; only their SHA-256 hash is persisted.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, HTTPException, Request

from .config import get_settings
from .db import get_db, now

SESSION_TTL = timedelta(days=14)
OTP_TTL = timedelta(minutes=5)

_ph = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=1)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, stored: str) -> bool:
    try:
        return _ph.verify(stored, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def generate_token() -> tuple[str, str]:
    """Return `(plaintext_token, token_hash)`. Only the hash is persisted."""
    tok = secrets.token_urlsafe(32)
    return tok, _sha256(tok)


def hash_token(token: str) -> str:
    return _sha256(token)


def generate_otp() -> str:
    return f"{secrets.randbelow(900_000) + 100_000:06d}"


_CRED_WORDS = (
    "alpha", "amber", "apex", "atlas", "blaze", "bolt", "cedar", "comet",
    "coral", "delta", "eagle", "ember", "falcon", "flame", "forest", "frost",
    "galaxy", "ghost", "glide", "harbor", "hawk", "ivory", "jade", "jet",
    "knight", "lake", "lunar", "maple", "matrix", "mint", "nebula", "neon",
    "noble", "nova", "ocean", "onyx", "orbit", "pearl", "phoenix", "pixel",
    "plasma", "prism", "pulse", "quartz", "quest", "rapid", "raven", "river",
    "rocket", "ruby", "sage", "shadow", "sigma", "silver", "solar", "spark",
    "spirit", "storm", "summit", "swift", "tiger", "titan", "torch", "turbo",
    "ultra", "valor", "vector", "venom", "vertex", "violet", "vortex", "wave",
    "wolf", "zenith", "zero", "zone",
)


def _word_number_credential() -> str:
    """``randomword_123`` (3-digit suffix)."""
    word = secrets.choice(_CRED_WORDS)
    suffix = secrets.randbelow(900) + 100
    return f"{word}_{suffix}"


def generate_password() -> str:
    """High-entropy secret shown once at registration (URL-safe, ~128 bits)."""
    return secrets.token_urlsafe(16)


def generate_username() -> str:
    return _word_number_credential()


def generate_pass_key() -> str:
    """Unique recovery key shown once at registration (~192 bits)."""
    return secrets.token_urlsafe(24)


def generate_redeem_code() -> str:
    return secrets.token_hex(8).upper()


def _prefixed_reward_code(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(8).upper()}"


def generate_daily_reward_code() -> str:
    return _prefixed_reward_code("DAILY_")


def generate_nick_reward_code() -> str:
    return _prefixed_reward_code("DISCORD_")


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ── FastAPI dependencies ──────────────────────────────────────────────────────


async def get_optional_user_id(request: Request) -> int | None:
    """Resolve logged-in user id from cookies/headers; ``None`` for guests."""
    from .session_cookies import get_user_token_from_request

    token = get_user_token_from_request(request)
    if not token:
        return None
    db = get_db()
    session = await db.sessions.find_one(
        {"token_hash": hash_token(token), "expires_at": {"$gt": now()}}
    )
    if session is None:
        return None
    user = await db.users.find_one({"id": session["user_id"]})
    if user is None or user.get("banned"):
        return None
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_seen_at": now()}})
    return int(user["id"])


async def get_current_user(request: Request) -> dict:
    from .session_cookies import get_user_token_from_request

    token = get_user_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="auth required")
    db = get_db()
    session = await db.sessions.find_one(
        {"token_hash": hash_token(token), "expires_at": {"$gt": now()}}
    )
    if session is None:
        raise HTTPException(status_code=401, detail="auth required")
    user = await db.users.find_one({"id": session["user_id"]})
    if user is None or user.get("banned"):
        raise HTTPException(status_code=401, detail="auth required")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_seen_at": now()}})
    return user


async def require_admin(request: Request) -> None:
    from .session_cookies import get_admin_token_from_request

    token = get_admin_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="admin required")
    row = await get_db().admin_sessions.find_one(
        {"token_hash": hash_token(token), "expires_at": {"$gt": now()}}
    )
    if row is None:
        raise HTTPException(status_code=401, detail="admin required")


async def revoke_admin_session(request: Request) -> None:
    from .session_cookies import get_admin_token_from_request

    token = get_admin_token_from_request(request)
    if token:
        await get_db().admin_sessions.delete_one({"token_hash": hash_token(token)})


async def require_internal(x_internal_secret: str = Header(default="")) -> None:
    """Guards bot-only endpoints with a constant-time HMAC secret check."""
    expected = get_settings().internal_secret
    if not expected or not constant_time_eq(x_internal_secret, expected):
        raise HTTPException(status_code=403, detail="forbidden")
