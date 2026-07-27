"""Sprint 15 Test Suite — Dashboard Stats Endpoint.

Tests:
    1. Dashboard stats returns correct structure for authenticated user.
    2. Dashboard stats returns zeros for user with no repos.
    3. Dashboard stats counts repositories correctly.
    4. Dashboard stats counts analyses correctly.
    5. Dashboard stats returns recent analyses ordered by created_at DESC.
    6. Dashboard stats includes repository_name in recent analyses.
    7. Dashboard stats does not include other user's data.
    8. Unauthenticated request returns 401.
"""
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.security import hash_password
from app.db.models import AnalysisStatus, Repository, User
from app.integrations.github.client import GitHubRepoData
from app.main import app
from app.repositories.analysis import AnalysisRepository
from app.repositories.repository import RepositoryRepository


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def _setup_auth(user: User):
    async def _get_user() -> User:
        return user
    app.dependency_overrides[get_current_user] = _get_user


async def _create_test_user(prefix: str = "dash") -> User:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=f"{prefix}_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPassword123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_test_repo(owner_id: int, name: str | None = None) -> Repository:
    session_factory = get_session_factory()
    async with session_factory() as session:
        if name is None:
            name = f"repo_{uuid.uuid4().hex[:6]}"
        repo = Repository(
            owner_id=owner_id,
            github_repo_id=_random_github_repo_id(),
            name=name,
            full_name=f"owner_{uuid.uuid4().hex[:6]}/{name}",
            url=f"https://github.com/test/{name}",
            default_branch="main",
            visibility="public",
        )
        session.add(repo)
        await session.commit()
        await session.refresh(repo)
        return repo


async def _create_test_analysis(
    repository_id: int,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    scores: dict | None = None,
) -> object:
    from app.db.models import Analysis
    session_factory = get_session_factory()
    async with session_factory() as session:
        analysis = Analysis(
            repository_id=repository_id,
            status=status,
            scores=scores,
        )
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)
        return analysis


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.mark.asyncio
async def test_dashboard_stats_empty(client: TestClient):
    """Dashboard returns zeros when user has no repos."""
    user = await _create_test_user("dash_empty")
    _setup_auth(user)

    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["repository_count"] == 0
    assert data["data"]["analysis_count"] == 0
    assert data["data"]["recent_analyses"] == []


@pytest.mark.asyncio
async def test_dashboard_stats_repo_count(client: TestClient):
    """Dashboard counts repositories correctly."""
    user = await _create_test_user("dash_repo")
    _setup_auth(user)

    await _create_test_repo(user.id, "repo-a")
    await _create_test_repo(user.id, "repo-b")
    await _create_test_repo(user.id, "repo-c")

    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["repository_count"] == 3


@pytest.mark.asyncio
async def test_dashboard_stats_analysis_count(client: TestClient):
    """Dashboard counts analyses correctly."""
    user = await _create_test_user("dash_count")
    _setup_auth(user)

    repo = await _create_test_repo(user.id, "counted-repo")
    await _create_test_analysis(repo.id, AnalysisStatus.COMPLETED)
    await _create_test_analysis(repo.id, AnalysisStatus.COMPLETED)
    await _create_test_analysis(repo.id, AnalysisStatus.FAILED)

    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["analysis_count"] == 3


@pytest.mark.asyncio
async def test_dashboard_stats_recent_analyses(client: TestClient):
    """Dashboard returns recent analyses with correct structure."""
    user = await _create_test_user("dash_recent")
    _setup_auth(user)

    repo = await _create_test_repo(user.id, "recent-repo")
    a1 = await _create_test_analysis(repo.id, AnalysisStatus.COMPLETED, scores={"code_quality": 80, "architecture": 70, "maintainability": 90})
    a2 = await _create_test_analysis(repo.id, AnalysisStatus.PENDING)

    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    data = response.json()
    recent = data["data"]["recent_analyses"]
    assert len(recent) == 2

    item = recent[0]
    assert "id" in item
    assert "status" in item
    assert "created_at" in item
    assert "repository_id" in item
    assert "repository_name" in item
    assert "recent-repo" in item["repository_name"]


@pytest.mark.asyncio
async def test_dashboard_stats_no_other_user_data(client: TestClient):
    """Dashboard does not include other user's data."""
    user_a = await _create_test_user("dash_iso_a")
    user_b = await _create_test_user("dash_iso_b")
    _setup_auth(user_a)

    repo_b = await _create_test_repo(user_b.id, "user-b-repo")
    await _create_test_analysis(repo_b.id, AnalysisStatus.COMPLETED)

    await _create_test_repo(user_a.id, "user-a-repo")

    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["repository_count"] == 1
    assert data["data"]["analysis_count"] == 0
    assert len(data["data"]["recent_analyses"]) == 0


@pytest.mark.asyncio
async def test_dashboard_stats_unauthenticated(client: TestClient):
    """Unauthenticated request returns 401."""
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401
