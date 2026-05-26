"""HttpOnly session cookies + double-submit CSRF."""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import HTTPException, Request, Response

from .config import get_settings
from .security import constant_time_eq

USER_SESSION_COOKIE = "cz_session"
ADMIN_SESSION_COOKIE = "cz_admin"
CSRF_COOKIE = "cz_csrf"
BLIK_PROOF_COOKIE = "blik_proof"

API_COOKIE_PATH = "/api"
BLIK_COOKIE_PATH = "/api/blik/confirm"


def _secure() -> bool:
    return not get_settings().is_development


def _cookie_kwargs(max_age: int, path: str = API_COOKIE_PATH) -> dict:
    return {
        "path": path,
        "httponly": True,
        "secure": _secure(),
        "samesite": "lax",
        "max_age": max_age,
    }


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        path="/",
        httponly=False,
        secure=_secure(),
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
    )


def set_user_session_cookie(response: Response, plaintext_token: str, ttl: timedelta) -> str:
    csrf = issue_csrf_token()
    response.set_cookie(
        USER_SESSION_COOKIE,
        plaintext_token,
        **_cookie_kwargs(int(ttl.total_seconds())),
    )
    set_csrf_cookie(response, csrf)
    return csrf


def set_admin_session_cookie(response: Response, plaintext_token: str, ttl: timedelta) -> str:
    csrf = issue_csrf_token()
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        plaintext_token,
        **_cookie_kwargs(int(ttl.total_seconds())),
    )
    set_csrf_cookie(response, csrf)
    return csrf


def clear_user_session_cookies(response: Response) -> None:
    response.delete_cookie(USER_SESSION_COOKIE, path=API_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def clear_admin_session_cookies(response: Response) -> None:
    response.delete_cookie(ADMIN_SESSION_COOKIE, path=API_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def set_blik_proof_cookie(response: Response, token: str, max_age: int = 1800) -> None:
    response.set_cookie(
        BLIK_PROOF_COOKIE,
        token,
        **_cookie_kwargs(max_age, path=BLIK_COOKIE_PATH),
    )


def clear_blik_proof_cookie(response: Response) -> None:
    response.delete_cookie(BLIK_PROOF_COOKIE, path=BLIK_COOKIE_PATH)


def get_user_token_from_request(request: Request) -> str | None:
    cookie = request.cookies.get(USER_SESSION_COOKIE, "").strip()
    if cookie:
        return cookie
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip() or None
    return None


def get_admin_token_from_request(request: Request) -> str | None:
    cookie = request.cookies.get(ADMIN_SESSION_COOKIE, "").strip()
    if cookie:
        return cookie
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip() or None
    return None


def get_blik_proof_token(request: Request) -> str | None:
    t = request.cookies.get(BLIK_PROOF_COOKIE, "").strip()
    return t or None


_CSRF_EXEMPT_PREFIXES = (
    "/api/blik/confirm",
    "/api/auth/verify-otp",
    "/api/auth/dev-login",
    "/api/auth/internal",
    "/api/blik/internal",
    "/api/payments/internal",
    "/api/admin/login",
    "/api/health",
)


def path_requires_csrf(path: str, method: str) -> bool:
    if method in ("GET", "HEAD", "OPTIONS"):
        return False
    for prefix in _CSRF_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return False
    if not path.startswith("/api/"):
        return False
    return True


def validate_csrf(request: Request) -> None:
    if not path_requires_csrf(request.url.path, request.method):
        return
    header = request.headers.get("X-CSRF-Token", "").strip()
    cookie = request.cookies.get(CSRF_COOKIE, "").strip()
    if not header or not cookie or not constant_time_eq(header, cookie):
        raise HTTPException(status_code=403, detail="csrf_required")
