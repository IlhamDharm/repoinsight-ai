"""Service untuk sinkronisasi GitHub repository ke database lokal.

Workflow:
1. Parse URL GitHub
2. Ambil metadata dari GitHub API
3. Cari atau buat User berdasarkan owner GitHub
4. Cari repository berdasarkan github_repo_id (identifier unik dari GitHub)
5. Jika belum ada → buat record baru
6. Jika sudah ada → update metadata yang mungkin berubah
7. Commit transaksi
8. Return domain object Repository
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Repository, User
from app.integrations.github.client import GitHubClient, GitHubRepoData
from app.integrations.github.parser import parse_github_url
from app.repositories.repository import RepositoryRepository
from app.repositories.user import UserRepository

logger = logging.getLogger("repoinsight.services.github_sync")


class RepositorySyncService:
    """Service yang mengorkestrasi sinkronisasi GitHub repository ke database.

    Service ini menerima GitHub client dan session via dependency injection.
    Service tidak melakukan HTTP request secara langsung — semua request
    didelegasikan ke GitHubClient.

    Args:
        session: Async database session.
        github_client: Async GitHub API client yang sudah dikonfigurasi.
    """

    def __init__(
        self,
        session: AsyncSession,
        github_client: GitHubClient,
    ) -> None:
        self._session = session
        self._github_client = github_client
        self._repo_repo = RepositoryRepository(session)
        self._user_repo = UserRepository(session)

    async def sync_repository(self, url: str) -> Repository:
        """Sinkronisasi GitHub repository berdasarkan URL.

        Parsing URL → Fetch GitHub metadata → Find or create User →
        Find or create/update Repository → Commit → Return Repository.

        Args:
            url: URL GitHub repository (mis. https://github.com/owner/repo).

        Returns:
            Domain object Repository yang sudah disimpan/diperbarui.

        Raises:
            ValidationError: Jika URL tidak valid.
            GitHubNotFoundError: Jika repository tidak ditemukan di GitHub.
            GitHubRateLimitError: Jika GitHub API rate limit terlampaui.
            GitHubAuthError: Jika autentikasi GitHub gagal.
            GitHubTimeoutError: Jika request ke GitHub timeout.
            GitHubConnectionError: Jika tidak bisa terhubung ke GitHub.
            ExternalServiceError: Jika GitHub mengembalikan error server.
        """
        # Step 1: Parse URL — dapat melempar ValidationError
        parsed = parse_github_url(url)
        logger.info(
            "Memulai sync repository: %s/%s", parsed.owner, parsed.name
        )

        # Step 2: Ambil metadata dari GitHub — dapat melempar GitHub exceptions
        github_data: GitHubRepoData = await self._github_client.get_repository(
            parsed.owner, parsed.name
        )

        # Step 3: Cari atau buat User berdasarkan owner GitHub
        owner = await self._user_repo.get_by_github_username(github_data.owner_login)
        if owner is None:
            logger.debug(
                "User '%s' belum ada, membuat record baru", github_data.owner_login
            )
            owner = await self._user_repo.create(
                User(github_username=github_data.owner_login)
            )

        # Step 4: Cari repository berdasarkan github_repo_id (identifier stabil dari GitHub)
        existing = await self._repo_repo.get_by_github_repo_id(github_data.id)

        if existing is None:
            # Step 5a: Buat record baru
            logger.info(
                "Repository baru: %s (github_id=%d)", github_data.full_name, github_data.id
            )
            repository = await self._repo_repo.create(
                Repository(
                    owner_id=owner.id,
                    github_repo_id=github_data.id,
                    name=github_data.name,
                    full_name=github_data.full_name,
                    url=github_data.html_url,
                    default_branch=github_data.default_branch,
                    visibility=github_data.visibility,
                )
            )
        else:
            # Step 5b: Update metadata yang mungkin berubah
            logger.info(
                "Update repository yang sudah ada: %s (github_id=%d)",
                github_data.full_name,
                github_data.id,
            )
            existing.name = github_data.name
            existing.full_name = github_data.full_name
            existing.url = github_data.html_url
            existing.default_branch = github_data.default_branch
            existing.visibility = github_data.visibility
            repository = await self._repo_repo.save(existing)

        # Step 6: Commit transaksi
        await self._session.commit()
        logger.info(
            "Sync selesai: repository id=%d, full_name=%s",
            repository.id,
            repository.full_name,
        )
        return repository
