"""Log every inbound HTTP call to the FastAPI app (API-focused paths by default)."""

from __future__ import annotations

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("api.inbound")

# Set LOG_ALL_HTTP=1 to log static files and redirects too (very noisy).
_LOG_ALL = os.getenv("LOG_ALL_HTTP", "").strip() in ("1", "true", "yes")


def _should_log_path(path: str) -> bool:
    if _LOG_ALL:
        return True
    if path.startswith("/api"):
        return True
    if path.startswith("/generate_"):
        return True
    return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not _should_log_path(request.url.path):
            return await call_next(request)

        t0 = time.perf_counter()
        client = request.client.host if request.client else "-"
        qs = request.url.query
        path_qs = f"{request.url.path}?{qs}" if qs else request.url.path
        log.info('IN  --> %s "%s" client=%s', request.method, path_qs, client)
        try:
            response = await call_next(request)
        except Exception:
            ms = (time.perf_counter() - t0) * 1000
            log.exception('IN  !! %s "%s" failed after %.1fms', request.method, path_qs, ms)
            raise
        ms = (time.perf_counter() - t0) * 1000
        log.info(
            'IN  <-- %s "%s" %s %.1fms',
            request.method,
            path_qs,
            response.status_code,
            ms,
        )
        return response
