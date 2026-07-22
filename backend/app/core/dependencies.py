from fastapi import Request

from app.core.config import get_settings
from app.core.middleware import get_request_id
from app.integrations.github.client import GitHubClient


def get_request_id_dependency(request: Request) -> str:
    return getattr(request.state, "request_id", get_request_id())


def get_github_client() -> GitHubClient:
    """FastAPI dependency yang menyediakan GitHubClient yang sudah dikonfigurasi.

    Dibuat baru setiap request (stateless). Settings dibaca dari environment
    via get_settings() yang menggunakan lru_cache.
    """
    settings = get_settings()
    return GitHubClient(
        base_url=settings.github_api_url,
        token=settings.github_token,
        timeout=settings.github_timeout,
    )

