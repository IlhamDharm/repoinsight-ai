from __future__ import annotations

import base64
import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.db.models import Repository, User
from app.integrations.github.client import (
    GitHubClient,
    GitHubContentData,
    GitHubTreeData,
    GitHubTreeItem,
)
from app.services.repository_scanner import RepositoryScanService


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


@pytest.mark.asyncio
async def test_repository_scan_service_success():
    github_repo_id = _random_github_repo_id()
    owner_login = f"owner_{uuid.uuid4().hex[:8]}"
    repo_name = f"repo_{uuid.uuid4().hex[:8]}"
    full_name = f"{owner_login}/{repo_name}"

    async for session in get_db_session():
        # Buat user & repo di DB
        user = User(github_username=owner_login)
        session.add(user)
        await session.flush()

        repo = Repository(
            owner_id=user.id,
            github_repo_id=github_repo_id,
            name=repo_name,
            full_name=full_name,
            url=f"https://github.com/{full_name}",
            default_branch="main",
            visibility="public",
        )
        session.add(repo)
        await session.commit()
        await session.refresh(repo)

        # Mock GitHub Client
        mock_client = AsyncMock(spec=GitHubClient)
        mock_client.get_tree.return_value = GitHubTreeData(
            sha="sha_tree",
            url="http://tree",
            tree=[
                GitHubTreeItem(path="app/main.py", mode="100644", type="blob", sha="sha1", size=100),
                GitHubTreeItem(path="README.md", mode="100644", type="blob", sha="sha2", size=50),
            ],
            truncated=False,
        )

        encoded_main = base64.b64encode(b"import os\nprint('hello')").decode("utf-8")
        encoded_readme = base64.b64encode(b"# Title\nWelcome").decode("utf-8")

        async def mock_get_content(owner, name, path, ref="main"):
            if path == "app/main.py":
                return GitHubContentData("main.py", "app/main.py", "sha1", 100, "base64", encoded_main, "file")
            return GitHubContentData("README.md", "README.md", "sha2", 50, "base64", encoded_readme, "file")

        mock_client.get_file_content.side_effect = mock_get_content

        scan_service = RepositoryScanService(session=session, github_client=mock_client)
        result = await scan_service.scan_repository(repo.id)

        assert result.repository == full_name
        assert result.branch == "main"
        assert result.total_files == 2
        assert result.total_source_files == 2
        assert result.total_lines == 4
        assert result.languages == {"Python": 1, "Markdown": 1}
        assert len(result.files) == 2


@pytest.mark.asyncio
async def test_repository_scan_service_repository_not_found():
    mock_client = AsyncMock(spec=GitHubClient)

    async for session in get_db_session():
        scan_service = RepositoryScanService(session=session, github_client=mock_client)
        with pytest.raises(NotFoundError):
            await scan_service.scan_repository(999999)
