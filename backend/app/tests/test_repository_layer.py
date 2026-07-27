import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db_session, get_session_factory
from app.core.security import hash_password
from app.db.models import User, Repository, Analysis, AnalysisStatus
from app.repositories.analysis import AnalysisRepository
from app.repositories.repository import RepositoryRepository
from app.repositories.user import UserRepository


def _random_github_username() -> str:
    return f"user_{uuid.uuid4().hex}"


def _random_repository_full_name() -> str:
    return f"repo_{uuid.uuid4().hex}/test"


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


async def _create_user(session, email: str | None = None, github_username: str | None = None) -> User:
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
        github_username=github_username,
    )
    return await UserRepository(session).create(user)


@pytest.mark.asyncio
async def test_user_repository_create_get_by_id_and_unique_identifier() -> None:
    async for session in get_db_session():
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=email,
            password_hash=hash_password("TestPassword123!"),
            is_active=True,
        )
        repository = UserRepository(session)
        created_user = await repository.create(user)

        assert created_user.id is not None
        assert created_user.email == email
        assert created_user.password_hash != "TestPassword123!"
        assert created_user.is_active is True
        assert created_user.created_at is not None
        assert created_user.updated_at is not None

        fetched_by_id = await repository.get_by_id(created_user.id)
        fetched_by_email = await repository.get_by_email(email)

        assert fetched_by_id is not None
        assert fetched_by_email is not None
        assert fetched_by_id.id == created_user.id
        assert fetched_by_email.email == email


@pytest.mark.asyncio
async def test_repository_repository_create_get_by_id_and_unique_identifiers() -> None:
    github_username = _random_github_username()
    repository_full_name = _random_repository_full_name()
    github_repo_id = _random_github_repo_id()

    async for session in get_db_session():
        user = await _create_user(session, github_username=github_username)

        repository_repo = RepositoryRepository(session)
        repository = Repository(
            owner_id=user.id,
            github_repo_id=github_repo_id,
            name="repo-test",
            full_name=repository_full_name,
            url=f"https://github.com/{repository_full_name}",
            default_branch="main",
            visibility="public",
        )
        created_repository = await repository_repo.create(repository)

        assert created_repository.id is not None
        assert created_repository.owner_id == user.id
        assert created_repository.full_name == repository_full_name

        fetched_by_id = await repository_repo.get_by_id(created_repository.id)
        fetched_by_repo_id = await repository_repo.get_by_github_repo_id(github_repo_id)
        fetched_by_full_name = await repository_repo.get_by_full_name(repository_full_name)

        assert fetched_by_id is not None
        assert fetched_by_repo_id is not None
        assert fetched_by_full_name is not None
        assert fetched_by_full_name.full_name == repository_full_name
        assert fetched_by_full_name.owner_id == user.id


@pytest.mark.asyncio
async def test_analysis_repository_create_and_relationships() -> None:
    github_username = _random_github_username()
    repository_full_name = _random_repository_full_name()
    github_repo_id = _random_github_repo_id()

    async for session in get_db_session():
        user = await _create_user(session, github_username=github_username)

        repository_repo = RepositoryRepository(session)
        created_repository = await repository_repo.create(
            Repository(
                owner_id=user.id,
                github_repo_id=github_repo_id,
                name="repo-test",
                full_name=repository_full_name,
                url=f"https://github.com/{repository_full_name}",
                default_branch="main",
                visibility="private",
            )
        )

        analysis_repo = AnalysisRepository(session)
        created_analysis = await analysis_repo.create(
            Analysis(
                repository_id=created_repository.id,
                status=AnalysisStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
        )

        assert created_analysis.id is not None
        assert created_analysis.repository_id == created_repository.id
        assert created_analysis.status == AnalysisStatus.RUNNING

        fetched_by_id = await analysis_repo.get_by_id(created_analysis.id)
        assert fetched_by_id is not None
        assert fetched_by_id.repository_id == created_repository.id
        assert fetched_by_id.status == AnalysisStatus.RUNNING

        repository_list = await analysis_repo.list_by_repository(created_repository.id)
        assert len(repository_list) == 1
        assert repository_list[0].id == created_analysis.id

        status_list = await analysis_repo.list_by_status(AnalysisStatus.RUNNING)
        assert any(item.id == created_analysis.id for item in status_list)


@pytest.mark.asyncio
async def test_unique_constraints_for_user_and_repository() -> None:
    repository_full_name = _random_repository_full_name()
    github_repo_id = _random_github_repo_id()

    async for session in get_db_session():
        email1 = f"unique_{uuid.uuid4().hex[:8]}@example.com"
        user = await _create_user(session, email=email1)
        await session.commit()

        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                await _create_user(session, email=email1)

        repository_repo = RepositoryRepository(session)
        await repository_repo.create(
            Repository(
                owner_id=user.id,
                github_repo_id=github_repo_id,
                name="repo-test",
                full_name=repository_full_name,
                url=f"https://github.com/{repository_full_name}",
                default_branch="main",
                visibility="public",
            )
        )
        await session.commit()

        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                await repository_repo.create(
                    Repository(
                        owner_id=user.id,
                        github_repo_id=github_repo_id,
                        name="repo-test-2",
                        full_name=f"{repository_full_name}-other",
                        url=f"https://github.com/{repository_full_name}-other",
                        default_branch="main",
                        visibility="public",
                    )
                )


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    async for session in get_db_session():
        user_repo = UserRepository(session)
        repository_repo = RepositoryRepository(session)
        analysis_repo = AnalysisRepository(session)

        assert await user_repo.get_by_id(-1) is None
        assert await repository_repo.get_by_id(-1) is None
        assert await analysis_repo.get_by_id(-1) is None
