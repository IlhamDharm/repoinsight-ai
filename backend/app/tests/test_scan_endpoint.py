from __future__ import annotations

import asyncio
import base64
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.exceptions import GitHubNotFoundError
from app.core.security import hash_password
from app.db.models import User
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


async def _create_test_user() -> User:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=f"scan_{uuid.uuid4().hex[:8]}@example.com",
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


def test_scan_repository_endpoint_success():
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

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
    _setup_auth(user)

    reg_resp = client.post("/api/v1/repositories", json={"url": f"https://github.com/{full_name}"})
    assert reg_resp.status_code == 201
    db_id = reg_resp.json()["data"]["id"]

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
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

    client = TestClient(app)
    mock_github = AsyncMock(spec=GitHubClient)
    app.dependency_overrides[get_github_client] = lambda: mock_github
    _setup_auth(user)

    scan_resp = client.post("/api/v1/repositories/999999/scan")
    app.dependency_overrides.clear()

    assert scan_resp.status_code == 404
    json_body = scan_resp.json()
    assert json_body["success"] is False
    assert json_body["error"]["code"] == "not_found"


def test_scan_repository_endpoint_github_404():
    user = asyncio.get_event_loop().run_until_complete(_create_test_user())

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
    _setup_auth(user)

    reg_resp = client.post("/api/v1/repositories", json={"url": f"https://github.com/{full_name}"})
    db_id = reg_resp.json()["data"]["id"]

    mock_github.get_tree.side_effect = GitHubNotFoundError("Tree not found")

    scan_resp = client.post(f"/api/v1/repositories/{db_id}/scan")
    app.dependency_overrides.clear()

    assert scan_resp.status_code == 404
    json_body = scan_resp.json()
    assert json_body["success"] is False
    assert json_body["error"]["code"] == "not_found"
