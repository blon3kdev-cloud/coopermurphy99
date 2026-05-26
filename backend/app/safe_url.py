"""URL and username validation — mirrors frontend safeUrl.js rules."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException

from .config import get_settings
from .security import constant_time_eq

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")

DEFAULT_ADMIN_LOGIN = "jrm8"
DEFAULT_ADMIN_PIN = "9990"
DEFAULT_ADMIN_PASSWORD = "8qq104"
EXAMPLE_INTERNAL_SECRET = "change-me-to-32-random-bytes-min"

_BLOCKED_SCHEMES = frozenset({"javascript", "blob", "file"})
_DATA_IMAGE_RE = re.compile(r"^data:image/(png|jpe?g|webp|gif);base64,", re.I)
_MAX_DATA_IMAGE_LEN = 3_000_000


def normalize_username(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if not key or not USERNAME_RE.match(key):
        return None
    return key


def validate_username_or_400(raw: str | None, *, field: str = "username") -> str:
    key = normalize_username(raw)
    if key is None:
        raise HTTPException(status_code=400, detail=f"invalid {field}")
    return key


def _allowed_image_hosts() -> set[str]:
    s = get_settings()
    hosts: set[str] = {
        "czutkabet.com",
        "www.czutkabet.com",
        "localhost",
        "127.0.0.1",
    }
    for origin in s.allowed_origins:
        try:
            if "://" in origin:
                hosts.add(urlparse(origin).hostname or "")
        except Exception:
            pass
    extra = getattr(s, "image_host_allowlist", "") or ""
    for part in extra.replace(",", " ").split():
        h = part.strip()
        if h:
            hosts.add(h.lstrip("."))
    hosts.discard("")
    return hosts


def _safe_data_image_url(text: str) -> str | None:
    if not _DATA_IMAGE_RE.match(text) or len(text) > _MAX_DATA_IMAGE_LEN:
        return None
    return text


def safe_image_url(raw: str | None) -> str | None:
    """Return a safe absolute https URL, inline data:image, or None if empty/invalid."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    inline = _safe_data_image_url(text)
    if inline is not None:
        return inline

    s = get_settings()
    allowed_hosts = _allowed_image_hosts()

    if text.startswith("/"):
        base = s.allowed_origins[0] if s.allowed_origins else "https://czutkabet.com"
        if "://" not in base:
            base = f"https://{base}"
        text = base.rstrip("/") + text

    try:
        parsed = urlparse(text)
    except Exception:
        return None

    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        return None
    if scheme == "https":
        pass
    elif scheme == "http" and s.is_development:
        pass
    else:
        return None

    host = (parsed.hostname or "").lower()
    if not host or host not in allowed_hosts:
        return None

    return text


def assert_no_user_fetch_url(url: str) -> None:
    """Guard for future server-side fetches of user-supplied URLs (SSRF)."""
    safe = safe_image_url(url)
    if safe is None:
        raise HTTPException(status_code=422, detail="url not allowed for fetch")


def validate_image_url_or_422(raw: str | None, *, field: str = "image") -> str | None:
    """None/empty allowed; non-empty must pass safe_image_url."""
    if raw is None or not str(raw).strip():
        return None
    safe = safe_image_url(raw)
    if safe is None:
        raise HTTPException(status_code=422, detail=f"invalid {field} url")
    return safe


def validate_production_secrets() -> None:
    """Fail fast in production if admin credentials are weak or defaults."""
    s = get_settings()
    if s.is_development:
        return

    if not s.admin_uses_hashes:
        raise RuntimeError(
            "Production requires ADMIN_PIN_HASH and ADMIN_PASSWORD_HASH (Argon2). "
            "Run: python scripts/hash_admin_credentials.py"
        )

    if not s.admin_login.strip() or s.admin_login == DEFAULT_ADMIN_LOGIN:
        raise RuntimeError(
            "Production requires non-default ADMIN_LOGIN and "
            "ADMIN_PIN_HASH + ADMIN_PASSWORD_HASH (Argon2)."
        )

    if not s.internal_secret.strip() or len(s.internal_secret) < 16:
        raise RuntimeError("Production requires INTERNAL_SECRET (min 16 chars).")

    if constant_time_eq(s.internal_secret.strip(), EXAMPLE_INTERNAL_SECRET):
        raise RuntimeError(
            "Production INTERNAL_SECRET must not be the .env.example placeholder."
        )

    if not s.blik_verify_strict:
        raise RuntimeError("Production requires BLIK_VERIFY_STRICT=true.")

    if s.payments_enabled:
        mnemonic = s.payment_wallet_mnemonic.strip()
        if len(mnemonic.split()) < 12:
            raise RuntimeError(
                "Production with payments enabled requires a valid PAYMENT_WALLET_MNEMONIC."
            )
