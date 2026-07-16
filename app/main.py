from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="RepoInsight AI backend foundation",
    debug=settings.debug,
)

app.include_router(health_router, prefix="/api/v1/health", tags=["health"])


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "ok"}
