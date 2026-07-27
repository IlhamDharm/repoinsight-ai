from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.security import hash_password
from app.db.models import AnalysisStatus, User
from app.integrations.github.client import GitHubRepoData
from app.main import app
from app.repositories.analysis import AnalysisRepository


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def _make_mock_github_data() -> GitHubRepoData:
    _id = _random_github_repo_id()
    owner = f"owner_{uuid.uuid4().hex[:6]}"
    name = f"repo_{uuid.uuid4().hex[:6]}"
    full_name = f"{owner}/{name}"
    return GitHubRepoData(
        id=_id,
        name=name,
        full_name=full_name,
        owner_login=owner,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Test repository",
    )


async def _create_test_user() -> User:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=f"history_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPassword123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _setup_auth(user: User):
    async def _get_user() -> User:
        return user
    app.dependency_overrides[get_current_user] = _get_user


@pytest.fixture
def mock_github() -> AsyncMock:
    with patch("app.core.dependencies.get_github_client") as mock:
        mock_client = AsyncMock()
        mock.return_value = mock_client
        app.dependency_overrides[get_github_client] = lambda: mock_client
        yield mock_client
        app.dependency_overrides.pop(get_github_client, None)


@pytest.fixture
def client() -> TestClient:
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())
    _setup_auth(user)
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_analysis_history(client: TestClient, mock_github: AsyncMock) -> None:
    repo_data = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data

    resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
    assert resp.status_code == 201
    repo_id = resp.json()["data"]["id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        a1 = await analysis_repo.create_analysis(repo_id)
        await analysis_repo.update_status(
            a1.id,
            AnalysisStatus.COMPLETED,
            scores={"code_quality": 80, "architecture": 90},
        )

        a2 = await analysis_repo.create_analysis(repo_id)
        await analysis_repo.update_status(
            a2.id,
            AnalysisStatus.FAILED,
            error_message="failed to run",
        )

        a3 = await analysis_repo.create_analysis(repo_id)
        await analysis_repo.update_status(
            a3.id,
            AnalysisStatus.COMPLETED,
            scores={"code_quality": 95, "architecture": 85, "maintainability": 90},
        )

    resp = client.get(f"/api/v1/repositories/{repo_id}/analyses?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    items = data["data"]
    assert len(items) == 3

    assert items[0]["id"] == a3.id
    assert items[0]["status"] == "COMPLETED"
    assert items[0]["score"] == 90

    assert items[1]["id"] == a2.id
    assert items[1]["status"] == "FAILED"
    assert items[1]["score"] is None

    assert items[2]["id"] == a1.id
    assert items[2]["status"] == "COMPLETED"
    assert items[2]["score"] == 85

    meta = data["meta"]
    assert meta["total"] == 3
    assert meta["page"] == 1
    assert meta["page_size"] == 10
    assert meta["total_pages"] == 1


@pytest.mark.asyncio
async def test_get_analysis_history_pagination(client: TestClient, mock_github: AsyncMock) -> None:
    repo_data = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data
    resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
    repo_id = resp.json()["data"]["id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        for _ in range(5):
            await analysis_repo.create_analysis(repo_id)
        await session.commit()

    resp = client.get(f"/api/v1/repositories/{repo_id}/analyses?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 5
    assert data["meta"]["total_pages"] == 3

    resp = client.get(f"/api/v1/repositories/{repo_id}/analyses?page=3&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["meta"]["page"] == 3


@pytest.mark.asyncio
async def test_get_analysis_history_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/repositories/999999/analyses")
    assert resp.status_code == 404
