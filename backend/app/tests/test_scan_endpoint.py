from __future__ import annotations

import base64
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.dependencies import get_github_client
from app.core.exceptions import GitHubNotFoundError
from app.integrations.github.client import (
    GitHubClient,
    GitHubContentData,
    GitHubRepoData,
    GitHubTreeData,
    GitHubTreeItem,
)
from app.main import app


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def test_scan_repository_endpoint_success():
    client = TestClient(app)

    repo_id = _random_github_repo_id()
    owner = f"owner_{uuid.uuid4().hex[:6]}"
    repo_name = f"repo_{uuid.uuid4().hex[:6]}"
    full_name = f"{owner}/{repo_name}"

    # 1. Register repository via API first
    mock_github = AsyncMock(spec=GitHubClient)
    mock_github.get_repository.return_value = GitHubRepoData(
        id=repo_id,
        name=repo_name,
        full_name=full_name,
        owner_login=owner,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Test repo",
    )

    app.dependency_overrides[get_github_client] = lambda: mock_github

    reg_resp = client.post("/api/v1/repositories", json={"url": f"https://github.com/{full_name}"})
    assert reg_resp.status_code == 201
    db_id = reg_resp.json()["data"]["id"]

    # 2. Setup mock for scan
    mock_github.get_tree.return_value = GitHubTreeData(
        sha="sha_tree",
        url="http://tree",
        tree=[
            GitHubTreeItem(path="app/main.py", mode="100644", type="blob", sha="sha1", size=120),
            GitHubTreeItem(path="src/index.ts", mode="100644", type="blob", sha="sha2", size=80),
        ],
        truncated=False,
    )

    encoded_py = base64.b64encode(b"print('hello')\nline2").decode("utf-8")
    encoded_ts = base64.b64encode(b"console.log('hi');").decode("utf-8")

    async def mock_get_content(o, n, p, ref="main"):
        if p == "app/main.py":
            return GitHubContentData("main.py", "app/main.py", "sha1", 120, "base64", encoded_py, "file")
        return GitHubContentData("index.ts", "src/index.ts", "sha2", 80, "base64", encoded_ts, "file")

    mock_github.get_file_content.side_effect = mock_get_content

    # 3. Call scan endpoint
    scan_resp = client.post(f"/api/v1/repositories/{db_id}/scan")
    app.dependency_overrides.clear()

    assert scan_resp.status_code == 200
    json_body = scan_resp.json()
    assert json_body["success"] is True
    data = json_body["data"]
    assert data["repository"] == full_name
    assert data["branch"] == "main"
    assert data["total_files"] == 2
    assert data["total_source_files"] == 2
    assert data["total_lines"] == 3
    assert data["languages"] == {"Python": 1, "TypeScript": 1}
    assert len(data["files"]) == 2


def test_scan_repository_endpoint_not_found():
    client = TestClient(app)
    mock_github = AsyncMock(spec=GitHubClient)
    app.dependency_overrides[get_github_client] = lambda: mock_github

    scan_resp = client.post("/api/v1/repositories/999999/scan")
    app.dependency_overrides.clear()

    assert scan_resp.status_code == 404
    json_body = scan_resp.json()
    assert json_body["success"] is False
    assert json_body["error"]["code"] == "not_found"


def test_scan_repository_endpoint_github_404():
    client = TestClient(app)

    repo_id = _random_github_repo_id()
    owner = f"owner_{uuid.uuid4().hex[:6]}"
    repo_name = f"repo_{uuid.uuid4().hex[:6]}"
    full_name = f"{owner}/{repo_name}"

    mock_github = AsyncMock(spec=GitHubClient)
    mock_github.get_repository.return_value = GitHubRepoData(
        id=repo_id,
        name=repo_name,
        full_name=full_name,
        owner_login=owner,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Test repo",
    )

    app.dependency_overrides[get_github_client] = lambda: mock_github

    reg_resp = client.post("/api/v1/repositories", json={"url": f"https://github.com/{full_name}"})
    db_id = reg_resp.json()["data"]["id"]

    mock_github.get_tree.side_effect = GitHubNotFoundError("Tree not found")

    scan_resp = client.post(f"/api/v1/repositories/{db_id}/scan")
    app.dependency_overrides.clear()

    assert scan_resp.status_code == 404
    json_body = scan_resp.json()
    assert json_body["success"] is False
    assert json_body["error"]["code"] == "not_found"
