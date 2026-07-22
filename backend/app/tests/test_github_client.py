"""Test untuk GitHubClient.

Menggunakan unittest.mock untuk mock httpx.AsyncClient.
Tidak melakukan request ke GitHub API asli — semua response disimulasikan.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import (
    ExternalServiceError,
    GitHubAuthError,
    GitHubConnectionError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from app.integrations.github.client import GitHubClient, GitHubRepoData

# ─── Helper ────────────────────────────────────────────────────────────────────

_GITHUB_API_URL = "https://api.github.com"

_SAMPLE_REPO_JSON = {
    "id": 123456,
    "name": "test-repo",
    "full_name": "testowner/test-repo",
    "owner": {"login": "testowner"},
    "html_url": "https://github.com/testowner/test-repo",
    "default_branch": "main",
    "visibility": "public",
    "private": False,
    "description": "A test repository",
}


def _make_mock_http_client(status_code: int, json_data: dict | None = None) -> AsyncMock:
    """Buat mock httpx.AsyncClient yang mengembalikan response tertentu."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    mock_response.headers = {}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


def _make_github_client() -> GitHubClient:
    return GitHubClient(base_url=_GITHUB_API_URL, token="", timeout=5.0)


# ─── Sukses ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_success_returns_repo_data() -> None:
    client = _make_github_client()
    mock_http = _make_mock_http_client(200, _SAMPLE_REPO_JSON)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        result = await client.get_repository("testowner", "test-repo")

    assert isinstance(result, GitHubRepoData)
    assert result.id == 123456
    assert result.name == "test-repo"
    assert result.full_name == "testowner/test-repo"
    assert result.owner_login == "testowner"
    assert result.html_url == "https://github.com/testowner/test-repo"
    assert result.default_branch == "main"
    assert result.visibility == "public"
    assert result.private is False
    assert result.description == "A test repository"


@pytest.mark.asyncio
async def test_get_repository_sends_correct_url() -> None:
    client = _make_github_client()
    mock_http = _make_mock_http_client(200, _SAMPLE_REPO_JSON)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        await client.get_repository("myowner", "myrepo")

    call_args = mock_http.get.call_args
    called_url = call_args[0][0]
    assert called_url == f"{_GITHUB_API_URL}/repos/myowner/myrepo"


@pytest.mark.asyncio
async def test_get_repository_with_token_sends_auth_header() -> None:
    client = GitHubClient(base_url=_GITHUB_API_URL, token="ghp_test_token", timeout=5.0)
    mock_http = _make_mock_http_client(200, _SAMPLE_REPO_JSON)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        await client.get_repository("owner", "repo")

    headers = mock_http.get.call_args[1]["headers"]
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer ghp_test_token"


@pytest.mark.asyncio
async def test_get_repository_without_token_no_auth_header() -> None:
    client = GitHubClient(base_url=_GITHUB_API_URL, token="", timeout=5.0)
    mock_http = _make_mock_http_client(200, _SAMPLE_REPO_JSON)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        await client.get_repository("owner", "repo")

    headers = mock_http.get.call_args[1]["headers"]
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_get_repository_visibility_fallback_when_not_in_response() -> None:
    """Jika field 'visibility' tidak ada, fallback ke 'private'/'public' berdasarkan 'private' field."""
    json_data = {k: v for k, v in _SAMPLE_REPO_JSON.items() if k != "visibility"}
    json_data["private"] = True
    client = _make_github_client()
    mock_http = _make_mock_http_client(200, json_data)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        result = await client.get_repository("owner", "repo")

    assert result.visibility == "private"


# ─── Error 404 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_404_raises_github_not_found_error() -> None:
    client = _make_github_client()
    mock_http = _make_mock_http_client(404)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubNotFoundError) as exc_info:
            await client.get_repository("owner", "nonexistent-repo")

    assert exc_info.value.status_code == 404
    assert "nonexistent-repo" in exc_info.value.message


# ─── Error 401 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_401_raises_github_auth_error() -> None:
    client = _make_github_client()
    mock_http = _make_mock_http_client(401)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubAuthError) as exc_info:
            await client.get_repository("owner", "repo")

    assert exc_info.value.status_code == 401


# ─── Error 403 Rate Limit ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_403_rate_limit_raises_github_rate_limit_error() -> None:
    client = _make_github_client()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {"x-ratelimit-remaining": "0"}

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client.get_repository("owner", "repo")

    assert exc_info.value.status_code == 429


# ─── Error 403 Forbidden (bukan rate limit) ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_403_forbidden_raises_github_auth_error() -> None:
    """403 tanpa x-ratelimit-remaining=0 berarti forbidden access."""
    client = _make_github_client()
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {}

    mock_http = AsyncMock()
    mock_http.get.return_value = mock_response
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubAuthError):
            await client.get_repository("owner", "repo")


# ─── Error 500 GitHub Server Error ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_500_raises_external_service_error() -> None:
    client = _make_github_client()
    mock_http = _make_mock_http_client(500)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(ExternalServiceError) as exc_info:
            await client.get_repository("owner", "repo")

    assert exc_info.value.status_code == 502
    assert "500" in exc_info.value.message


# ─── Timeout ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_timeout_raises_github_timeout_error() -> None:
    client = _make_github_client()

    mock_http = AsyncMock()
    mock_http.get.side_effect = httpx.TimeoutException("Request timed out")
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubTimeoutError) as exc_info:
            await client.get_repository("owner", "repo")

    assert exc_info.value.status_code == 504


# ─── Connection Error ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_repository_connect_error_raises_github_connection_error() -> None:
    client = _make_github_client()

    mock_http = AsyncMock()
    mock_http.get.side_effect = httpx.ConnectError("Connection refused")
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubConnectionError) as exc_info:
            await client.get_repository("owner", "repo")

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_get_repository_transport_error_raises_github_connection_error() -> None:
    """TransportError selain ConnectError dan TimeoutException."""
    client = _make_github_client()

    mock_http = AsyncMock()
    mock_http.get.side_effect = httpx.ReadError("Read error")
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubConnectionError):
            await client.get_repository("owner", "repo")
