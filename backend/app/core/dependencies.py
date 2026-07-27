from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.middleware import get_request_id
from app.core.security import decode_access_token
from app.db.models import User
from app.integrations.github.client import GitHubClient
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """FastAPI dependency untuk mendapatkan user yang terautentikasi dari JWT token.

    Membaca Bearer token, memvalidasi JWT, mengambil user dari database.
    Menolak token invalid, expired, atau user tidak valid/inactive.
    """
    if credentials is None:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Token tidak ditemukan")

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Token tidak valid atau sudah expired")

    user_id = payload.get("sub")
    if user_id is None:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Token tidak valid")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(int(user_id))
    if user is None:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("User tidak ditemukan")
    if not user.is_active:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Akun tidak aktif")
    return user
