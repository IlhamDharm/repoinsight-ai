import logging
import re
import time
import uuid
from contextvars import ContextVar
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_CONTEXT: Final[ContextVar[str]] = ContextVar("request_id", default="")
logger = logging.getLogger("repoinsight.api")

# Only allow safe characters in request ID (alphanumeric, hyphens, underscores)
_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        raw_id = request.headers.get("X-Request-ID", "")
        if _REQUEST_ID_PATTERN.match(raw_id):
            request_id = raw_id
        else:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = REQUEST_ID_CONTEXT.set(request_id)
        try:
            response = await call_next(request)
        finally:
            REQUEST_ID_CONTEXT.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = time.perf_counter()
        logger.info("request_started method=%s path=%s", request.method, request.url.path)
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def get_request_id() -> str:
    return REQUEST_ID_CONTEXT.get()
