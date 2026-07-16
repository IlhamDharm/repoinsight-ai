from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/live", response_model=HealthResponse)
async def health_live() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(service=settings.app_name, environment=settings.environment)


@router.get("/ready", response_model=HealthResponse)
async def health_ready() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(service=settings.app_name, environment=settings.environment)
