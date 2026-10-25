from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import check_database_health
from app.core.dependencies import get_request_id_dependency
from app.core.response import build_error_payload, build_success_payload
from app.schemas.health import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get(
    "",
    summary="Health summary",
    description="Returns application liveness and database connectivity.",
)
async def health_summary(
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
) -> JSONResponse:
    try:
        database = await check_database_health()
        return JSONResponse(
            status_code=200,
            content=build_success_payload(
                {"service": settings.app_name, "environment": settings.environment, **database},
                request_id=request_id,
            ),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=build_error_payload(
                "Database unavailable", "database_unavailable", request_id=request_id,
                details={"detail": str(exc)},
            ),
        )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns application status. Use for Kubernetes liveness probes.",
)
async def health_live(
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
) -> JSONResponse:
    payload = HealthResponse(service=settings.app_name, environment=settings.environment)
    return JSONResponse(
        status_code=200,
        content=build_success_payload(payload.model_dump(), request_id=request_id),
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns application readiness status. Use for Kubernetes readiness probes.",
)
async def health_ready(
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
) -> JSONResponse:
    payload = HealthResponse(service=settings.app_name, environment=settings.environment)
    return JSONResponse(
        status_code=200,
        content=build_success_payload(payload.model_dump(), request_id=request_id),
    )


@router.get(
    "/db",
    summary="Database health check",
    description="Executes `SELECT 1` against PostgreSQL to verify database connectivity.",
    responses={
        200: {"description": "Database is healthy"},
        503: {"description": "Database unavailable"},
    },
)
async def database_health(
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
) -> JSONResponse:
    try:
        payload = await check_database_health()
        return JSONResponse(
            status_code=200,
            content=build_success_payload(payload, request_id=request_id),
        )
    except Exception as exc:  # pragma: no cover - defensive path
        return JSONResponse(
            status_code=503,
            content=build_error_payload(
                "Database unavailable",
                "database_unavailable",
                request_id=request_id,
                details={"detail": str(exc)},
            ),
        )
