from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_github_client
from app.db.models import AnalysisStatus
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
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_analysis_history(client: TestClient, mock_github: AsyncMock) -> None:
    repo_data = _make_mock_github_data()
    mock_github.get_repository.return_value = repo_data

    # Register Repo
    resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
    assert resp.status_code == 201
    repo_id = resp.json()["data"]["id"]

    # Create analyses directly in DB
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

    # Fetch history
    resp = client.get(f"/api/v1/repositories/{repo_id}/analyses?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    items = data["data"]
    assert len(items) == 3

    # Ordered descending by created_at (which matches auto-incrementing ID in this fast synchronous DB insert)
    assert items[0]["id"] == a3.id
    assert items[0]["status"] == "COMPLETED"
    assert items[0]["score"] == 90  # average of 95, 85, 90

    assert items[1]["id"] == a2.id
    assert items[1]["status"] == "FAILED"
    assert items[1]["score"] is None

    assert items[2]["id"] == a1.id
    assert items[2]["status"] == "COMPLETED"
    assert items[2]["score"] == 85  # average of 80, 90

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

    # Fetch page 1
    resp = client.get(f"/api/v1/repositories/{repo_id}/analyses?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 5
    assert data["meta"]["total_pages"] == 3

    # Fetch page 3
    resp = client.get(f"/api/v1/repositories/{repo_id}/analyses?page=3&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["meta"]["page"] == 3


@pytest.mark.asyncio
async def test_get_analysis_history_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/repositories/999999/analyses")
    assert resp.status_code == 404
