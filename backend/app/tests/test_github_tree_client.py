from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import (
    ExternalServiceError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.integrations.github.client import (
    GitHubClient,
    GitHubContentData,
    GitHubTreeData,
)

_GITHUB_API_URL = "https://api.github.com"

_SAMPLE_TREE_JSON = {
    "sha": "tree_sha_123",
    "url": "https://api.github.com/repos/owner/repo/git/trees/tree_sha_123",
    "tree": [
        {
            "path": "app/main.py",
            "mode": "100644",
            "type": "blob",
            "sha": "blob_sha_1",
            "size": 1200,
            "url": "https://api.github.com/repos/owner/repo/git/blobs/blob_sha_1",
        },
        {
            "path": "app",
            "mode": "040000",
            "type": "tree",
            "sha": "tree_sha_dir",
            "size": None,
            "url": "https://api.github.com/repos/owner/repo/git/trees/tree_sha_dir",
        },
    ],
    "truncated": False,
}

_SAMPLE_CONTENT_JSON = {
    "name": "main.py",
    "path": "app/main.py",
    "sha": "blob_sha_1",
    "size": 25,
    "encoding": "base64",
    "content": base64.b64encode(b"print('hello from test')").decode("utf-8"),
    "type": "file",
}


def _make_mock_http_client(
    status_code: int, json_data: dict | list | None = None, headers: dict | None = None
) -> AsyncMock:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data if json_data is not None else {}
    mock_response.headers = headers or {}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


def _make_github_client() -> GitHubClient:
    return GitHubClient(base_url=_GITHUB_API_URL, token="", timeout=5.0)


@pytest.mark.asyncio
async def test_get_tree_success():
    client = _make_github_client()
    mock_http = _make_mock_http_client(200, _SAMPLE_TREE_JSON)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        result = await client.get_tree("owner", "repo", tree_sha_or_branch="main", recursive=True)

    assert isinstance(result, GitHubTreeData)
    assert result.sha == "tree_sha_123"
    assert result.truncated is False
    assert len(result.tree) == 2
    assert result.tree[0].path == "app/main.py"
    assert result.tree[0].type == "blob"
    assert result.tree[0].size == 1200


@pytest.mark.asyncio
async def test_get_tree_not_found_raises_404():
    client = _make_github_client()
    mock_http = _make_mock_http_client(404, {"message": "Not Found"})

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubNotFoundError):
            await client.get_tree("owner", "repo", "nonexistent_branch")


@pytest.mark.asyncio
async def test_get_tree_rate_limit_exceeded_raises_429():
    client = _make_github_client()
    mock_http = _make_mock_http_client(403, {"message": "Rate limit exceeded"}, headers={"x-ratelimit-remaining": "0"})

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubRateLimitError):
            await client.get_tree("owner", "repo")


@pytest.mark.asyncio
async def test_get_file_content_success():
    client = _make_github_client()
    mock_http = _make_mock_http_client(200, _SAMPLE_CONTENT_JSON)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        result = await client.get_file_content("owner", "repo", "app/main.py", ref="main")

    assert isinstance(result, GitHubContentData)
    assert result.name == "main.py"
    assert result.path == "app/main.py"
    assert result.encoding == "base64"


@pytest.mark.asyncio
async def test_get_file_content_directory_path_raises_not_found():
    client = _make_github_client()
    # Directory response is a list
    mock_http = _make_mock_http_client(200, [{"name": "file1.py"}])

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=mock_http):
        with pytest.raises(GitHubNotFoundError):
            await client.get_file_content("owner", "repo", "app", ref="main")
