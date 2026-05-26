"""Normalized API errors and request correlation — avoid leaking validation internals."""
from __future__ import annotations

import logging
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_log = logging.getLogger("app")


async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-Id", "").strip() or uuid.uuid4().hex
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    rid = getattr(request.state, "request_id", None)
    _log.warning(
        "validation_failed request_id=%s path=%s errors=%s",
        rid,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={"error": "validation_failed"},
        headers={"X-Request-Id": rid} if rid else None,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        content = detail
    elif isinstance(detail, list):
        content = {"error": "validation_failed"}
    else:
        content = {"error": detail}
    rid = getattr(request.state, "request_id", None)
    headers = {"X-Request-Id": rid} if rid else None
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)
