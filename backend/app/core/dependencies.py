from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.middleware import get_request_id
from app.core.security import decode_access_token, hash_password
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
    """Resolve the current user, or the first active user in demo mode.

    Authentication remains enabled by default. When explicitly disabled for a
    trusted local/demo deployment, all requests use the first active account so
    existing ownership and foreign-key rules continue to work.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        user_repo = UserRepository(session)
        users = await user_repo.list(limit=1_000_000)
        active_user = next((candidate for candidate in users if candidate.is_active), None)
        if active_user is None:
            active_user = User(
                email="demo@repoinsight.local",
                password_hash=hash_password("disabled-login"),
                is_active=True,
            )
            active_user = await user_repo.create(active_user)
            await session.commit()
            await session.refresh(active_user)
        return active_user

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


async def verify_repository_owner(
    repository_id: int,
    current_user: User,
    session: AsyncSession,
):
    """Verifikasi bahwa repository dimiliki oleh current_user.

    Raises:
        NotFoundError: Repository tidak ditemukan.
        ForbiddenError: User bukan pemilik repository.
    """
    from app.core.exceptions import ForbiddenError, NotFoundError
    from app.repositories.repository import RepositoryRepository

    repo_repo = RepositoryRepository(session)
    repository = await repo_repo.get_by_id(repository_id)
    if repository is None:
        raise NotFoundError(f"Repository dengan ID {repository_id} tidak ditemukan")
    if repository.owner_id != current_user.id:
        raise ForbiddenError("Anda tidak memiliki akses ke repository ini")
    return repository


async def verify_analysis_owner(
    analysis_id: int,
    current_user: User,
    session: AsyncSession,
):
    """Verifikasi bahwa analysis dimiliki oleh current_user melalui ownership repository.

    Raises:
        NotFoundError: Analysis atau repository tidak ditemukan.
        ForbiddenError: User bukan pemilik repository terkait.
    """
    from app.core.exceptions import ForbiddenError, NotFoundError
    from app.repositories.analysis import AnalysisRepository
    from app.repositories.repository import RepositoryRepository

    analysis_repo = AnalysisRepository(session)
    analysis = await analysis_repo.get_by_id(analysis_id)
    if analysis is None:
        raise NotFoundError(f"Analysis dengan ID {analysis_id} tidak ditemukan")

    repo_repo = RepositoryRepository(session)
    repository = await repo_repo.get_by_id(analysis.repository_id)
    if repository is None:
        raise NotFoundError("Repository tidak ditemukan")
    if repository.owner_id != current_user.id:
        raise ForbiddenError("Anda tidak memiliki akses ke analysis ini")
    return analysis
