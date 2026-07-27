import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.analyses import router as analyses_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.repositories import router as repositories_router
from app.core.config import get_settings
from app.core.dependencies import get_request_id_dependency
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware
from app.core.response import build_error_payload, build_success_payload

configure_logging()
logger = logging.getLogger("repoinsight.api")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="RepoInsight AI backend foundation",
    debug=settings.debug,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
app.include_router(repositories_router, prefix="/api/v1/repositories", tags=["repositories"])
app.include_router(analyses_router, prefix="/api/v1/analyses", tags=["analyses"])


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(exc.message, exc.code, request_id=request_id, details=exc.details),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if exc.status_code == 404:
        message = "Resource not found"
        code = "not_found"
    elif exc.status_code == 405:
        message = "Method not allowed"
        code = "method_not_allowed"
    else:
        message = exc.detail or "Request failed"
        code = "http_error"

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(message, code, request_id=request_id),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    import json as _json
    request_id = getattr(request.state, "request_id", None)
    try:
        safe_errors = _json.loads(_json.dumps(exc.errors(), default=str))
    except Exception:
        safe_errors = str(exc)
    return JSONResponse(
        status_code=422,
        content=build_error_payload("Invalid request payload", "validation_error", request_id=request_id, details=safe_errors),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=build_error_payload("Internal server error", "internal_server_error", request_id=request_id),
    )


@app.get("/", tags=["meta"])
async def root(request: Request, request_id: str = Depends(get_request_id_dependency)) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=build_success_payload({"service": settings.app_name, "status": "ok"}, request_id=request_id),
    )
