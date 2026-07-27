"""Test untuk RepositorySyncService.

Menguji logika bisnis sinkronisasi repository:
- Membuat repository baru jika belum ada di database
- Memperbarui repository jika sudah ada (update metadata)
- Menangani user owner (mencari atau membuat baru)
- Meneruskan exception dari parser dan GitHub client
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.database import get_db_session, get_session_factory
from app.core.exceptions import GitHubNotFoundError, ValidationError
from app.core.security import hash_password
from app.db.models import Repository, User
from app.integrations.github.client import GitHubClient, GitHubRepoData
from app.repositories.user import UserRepository
from app.services.github_sync import RepositorySyncService


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


async def _create_owner_user(session, email: str | None = None) -> User:
    if email is None:
        email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    return await UserRepository(session).create(user)


@pytest.mark.asyncio
async def test_sync_repository_create_new() -> None:
    github_repo_id = _random_github_repo_id()
    owner_login = f"owner_{uuid.uuid4().hex[:8]}"
    repo_name = f"repo_{uuid.uuid4().hex[:8]}"
    full_name = f"{owner_login}/{repo_name}"

    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_repository.return_value = GitHubRepoData(
        id=github_repo_id,
        name=repo_name,
        full_name=full_name,
        owner_login=owner_login,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Sample repository",
    )

    async for session in get_db_session():
        owner_user = await _create_owner_user(session)
        await session.commit()

        service = RepositorySyncService(session=session, github_client=mock_client)
        url = f"https://github.com/{full_name}"

        repo = await service.sync_repository(url, owner_id=owner_user.id)

        assert repo.id is not None
        assert repo.github_repo_id == github_repo_id
        assert repo.name == repo_name
        assert repo.full_name == full_name
        assert repo.url == f"https://github.com/{full_name}"
        assert repo.default_branch == "main"
        assert repo.visibility == "public"
        assert repo.owner_id == owner_user.id


@pytest.mark.asyncio
async def test_sync_repository_update_existing() -> None:
    github_repo_id = _random_github_repo_id()
    owner_login = f"owner_{uuid.uuid4().hex[:8]}"
    repo_name = f"repo_{uuid.uuid4().hex[:8]}"
    full_name = f"{owner_login}/{repo_name}"

    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_repository.return_value = GitHubRepoData(
        id=github_repo_id,
        name=repo_name,
        full_name=full_name,
        owner_login=owner_login,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Initial description",
    )

    async for session in get_db_session():
        owner_user = await _create_owner_user(session)
        await session.commit()

        service = RepositorySyncService(session=session, github_client=mock_client)
        url = f"https://github.com/{full_name}"

        first_sync = await service.sync_repository(url, owner_id=owner_user.id)
        first_id = first_sync.id

        mock_client.get_repository.return_value = GitHubRepoData(
            id=github_repo_id,
            name=repo_name,
            full_name=full_name,
            owner_login=owner_login,
            html_url=f"https://github.com/{full_name}",
            default_branch="master",
            visibility="private",
            private=True,
            description="Updated description",
        )

        second_sync = await service.sync_repository(url, owner_id=owner_user.id)

        assert second_sync.id == first_id
        assert second_sync.github_repo_id == github_repo_id
        assert second_sync.default_branch == "master"
        assert second_sync.visibility == "private"


@pytest.mark.asyncio
async def test_sync_repository_invalid_url_raises_validation_error() -> None:
    mock_client = AsyncMock(spec=GitHubClient)

    async for session in get_db_session():
        service = RepositorySyncService(session=session, github_client=mock_client)

        with pytest.raises(ValidationError):
            await service.sync_repository("https://gitlab.com/owner/repo")

        mock_client.get_repository.assert_not_called()


@pytest.mark.asyncio
async def test_sync_repository_not_found_on_github() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_repository.side_effect = GitHubNotFoundError("Repository not found")

    async for session in get_db_session():
        service = RepositorySyncService(session=session, github_client=mock_client)

        with pytest.raises(GitHubNotFoundError):
            await service.sync_repository("https://github.com/owner/nonexistent")
