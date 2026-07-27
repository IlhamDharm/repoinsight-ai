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
            email=f"compare_{uuid.uuid4().hex[:8]}@example.com",
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
async def test_compare_analyses_success(client: TestClient, mock_github: AsyncMock) -> None:
    repo_data = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data

    resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
    repo_id = resp.json()["data"]["id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        a1 = await analysis_repo.create_analysis(repo_id)
        await analysis_repo.update_status(
            a1.id,
            AnalysisStatus.COMPLETED,
            scores={"code_quality": 70, "architecture": 70, "maintainability": 70},
            findings=[{"id": 1}, {"id": 2}, {"id": 3}]
        )

        a2 = await analysis_repo.create_analysis(repo_id)
        await analysis_repo.update_status(
            a2.id,
            AnalysisStatus.COMPLETED,
            scores={"code_quality": 80, "architecture": 90, "maintainability": 70},
            findings=[{"id": 1}]
        )

    resp = client.get(f"/api/v1/analyses/{a2.id}/compare/{a1.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    comp = data["data"]
    assert comp["current_analysis_id"] == a2.id
    assert comp["previous_analysis_id"] == a1.id
    
    assert comp["current_score"] == 80
    assert comp["previous_score"] == 70
    assert comp["score_change"] == 10
    
    assert comp["findings_change"] == -2
    
    assert comp["category_changes"]["code_quality"] == 10
    assert comp["category_changes"]["architecture"] == 20
    assert comp["category_changes"]["maintainability"] == 0

@pytest.mark.asyncio
async def test_compare_different_repositories(client: TestClient, mock_github: AsyncMock) -> None:
    repo_data1 = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data1
    repo_id1 = client.post("/api/v1/repositories", json={"url": repo_data1.html_url}).json()["data"]["id"]

    repo_data2 = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data2
    repo_id2 = client.post("/api/v1/repositories", json={"url": repo_data2.html_url}).json()["data"]["id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        a1 = await analysis_repo.create_analysis(repo_id1)
        await analysis_repo.update_status(a1.id, AnalysisStatus.COMPLETED)
        
        a2 = await analysis_repo.create_analysis(repo_id2)
        await analysis_repo.update_status(a2.id, AnalysisStatus.COMPLETED)
        
    resp = client.get(f"/api/v1/analyses/{a2.id}/compare/{a1.id}")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "different_repository"

@pytest.mark.asyncio
async def test_compare_incomplete_analysis(client: TestClient, mock_github: AsyncMock) -> None:
    repo_data = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data
    repo_id = client.post("/api/v1/repositories", json={"url": repo_data.html_url}).json()["data"]["id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        a1 = await analysis_repo.create_analysis(repo_id)
        await analysis_repo.update_status(a1.id, AnalysisStatus.COMPLETED)
        
        a2 = await analysis_repo.create_analysis(repo_id)
        await session.commit()
        
    resp = client.get(f"/api/v1/analyses/{a2.id}/compare/{a1.id}")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "incomplete_analysis"

@pytest.mark.asyncio
async def test_compare_not_found(client: TestClient) -> None:
    resp = client.get(f"/api/v1/analyses/9999/compare/8888")
    assert resp.status_code == 404
