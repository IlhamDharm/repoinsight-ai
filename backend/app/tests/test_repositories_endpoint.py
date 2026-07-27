"""Test untuk endpoint POST /api/v1/repositories.

Menggunakan TestClient (sync) dengan dependency override untuk mock GitHubClient dan auth.
Database real digunakan (tabel sudah dibuat oleh conftest.py session fixture).
Tidak ada request ke GitHub API asli.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.exceptions import (
    ExternalServiceError,
    GitHubAuthError,
    GitHubConnectionError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from app.core.security import hash_password
from app.db.models import User
from app.integrations.github.client import GitHubClient, GitHubRepoData
from app.main import app


# ─── Helper ────────────────────────────────────────────────────────────────────

def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def _make_mock_github_data(
    github_repo_id: int | None = None,
    owner_login: str = "testowner",
    repo_name: str = "test-repo",
) -> GitHubRepoData:
    _id = github_repo_id or _random_github_repo_id()
    full_name = f"{owner_login}/{repo_name}"
    return GitHubRepoData(
        id=_id,
        name=repo_name,
        full_name=full_name,
        owner_login=owner_login,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="A test repository",
    )


def _make_mock_client(
    repo_data: GitHubRepoData | None = None,
    side_effect: Exception | None = None,
) -> GitHubClient:
    """Buat mock GitHubClient dengan return value atau side_effect."""
    mock = AsyncMock(spec=GitHubClient)
    if side_effect:
        mock.get_repository.side_effect = side_effect
    else:
        mock.get_repository.return_value = repo_data or _make_mock_github_data()
    return mock


async def _create_test_user() -> User:
    """Buat user test di database dan return user object."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPassword123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _setup_auth(user: User):
    """Override get_current_user dependency."""
    async def _get_user() -> User:
        return user
    app.dependency_overrides[get_current_user] = _get_user


# ─── Success: Repository Baru ─────────────────────────────────────────────────

def test_register_repository_creates_new_returns_201() -> None:
    github_repo_id = _random_github_repo_id()
    owner_login = f"owner_{uuid.uuid4().hex[:8]}"
    repo_name = f"repo_{uuid.uuid4().hex[:8]}"
    full_name = f"{owner_login}/{repo_name}"

    mock_data = _make_mock_github_data(
        github_repo_id=github_repo_id,
        owner_login=owner_login,
        repo_name=repo_name,
    )
    mock_client = _make_mock_client(repo_data=mock_data)

    user = _create_test_user().__await__.__next__() if False else None
    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": f"https://github.com/{full_name}"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["success"] is True
        data = payload["data"]
        assert data["github_repo_id"] == github_repo_id
        assert data["name"] == repo_name
        assert data["full_name"] == full_name
        assert data["default_branch"] == "main"
        assert data["visibility"] == "public"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "meta" in payload
        assert "request_id" in payload["meta"]
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── Success: Idempotent (repository sudah ada, update metadata) ──────────────

def test_register_same_repository_twice_idempotent() -> None:
    github_repo_id = _random_github_repo_id()
    owner_login = f"owner_{uuid.uuid4().hex[:8]}"
    repo_name = f"repo_{uuid.uuid4().hex[:8]}"

    mock_data = _make_mock_github_data(
        github_repo_id=github_repo_id,
        owner_login=owner_login,
        repo_name=repo_name,
    )
    mock_client = _make_mock_client(repo_data=mock_data)

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        url_payload = {"url": f"https://github.com/{owner_login}/{repo_name}"}

        first = client.post("/api/v1/repositories", json=url_payload)
        second = client.post("/api/v1/repositories", json=url_payload)

        assert first.status_code == 201
        assert second.status_code == 201

        first_id = first.json()["data"]["id"]
        second_id = second.json()["data"]["id"]
        assert first_id == second_id  # Same record updated, not duplicated
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── Request Validation Error ─────────────────────────────────────────────────

def test_register_repository_empty_url_returns_422() -> None:
    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: _make_mock_client()
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post("/api/v1/repositories", json={"url": ""})

        assert response.status_code == 422
        payload = response.json()
        assert payload["success"] is False
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_register_repository_missing_url_field_returns_422() -> None:
    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: _make_mock_client()
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post("/api/v1/repositories", json={})

        assert response.status_code == 422
        payload = response.json()
        assert payload["success"] is False
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_register_repository_invalid_github_url_returns_422() -> None:
    """URL non-GitHub yang lolos Pydantic validation tapi gagal di parser."""
    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: _make_mock_client()
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://gitlab.com/owner/repo"},
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "validation_error"
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── GitHub 404 ───────────────────────────────────────────────────────────────

def test_register_repository_github_not_found_returns_404() -> None:
    mock_client = _make_mock_client(
        side_effect=GitHubNotFoundError("Repository tidak ditemukan")
    )

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/nonexistent-repo"},
        )

        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "not_found"
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── GitHub Rate Limit ────────────────────────────────────────────────────────

def test_register_repository_github_rate_limit_returns_429() -> None:
    mock_client = _make_mock_client(
        side_effect=GitHubRateLimitError("Rate limit exceeded")
    )

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 429
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "github_rate_limit"
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── GitHub Auth Error ────────────────────────────────────────────────────────

def test_register_repository_github_auth_error_returns_401() -> None:
    mock_client = _make_mock_client(
        side_effect=GitHubAuthError("Authentication failed")
    )

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "github_auth_error"
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── GitHub API Error (5xx) ───────────────────────────────────────────────────

def test_register_repository_github_server_error_returns_502() -> None:
    mock_client = _make_mock_client(
        side_effect=ExternalServiceError("GitHub API error")
    )

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 502
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "external_service_error"
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── GitHub Timeout ───────────────────────────────────────────────────────────

def test_register_repository_github_timeout_returns_504() -> None:
    mock_client = _make_mock_client(
        side_effect=GitHubTimeoutError("Request timeout")
    )

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 504
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "github_timeout"
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── GitHub Connection Error ──────────────────────────────────────────────────

def test_register_repository_github_connection_error_returns_502() -> None:
    mock_client = _make_mock_client(
        side_effect=GitHubConnectionError("Cannot connect to GitHub")
    )

    import asyncio
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    app.dependency_overrides[get_github_client] = lambda: mock_client
    _setup_auth(user)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 502
        payload = response.json()
        assert payload["success"] is False
    finally:
        app.dependency_overrides.pop(get_github_client, None)
        app.dependency_overrides.pop(get_current_user, None)


# ─── Unauthorized: No Token ──────────────────────────────────────────────────

def test_register_repository_without_token_returns_401() -> None:
    mock_client = _make_mock_client()
    app.dependency_overrides[get_github_client] = lambda: mock_client
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False
    finally:
        app.dependency_overrides.pop(get_github_client, None)
