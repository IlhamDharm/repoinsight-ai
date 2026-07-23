"""Service yang mengorkestrasi repository content & code scanning."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.integrations.github.client import GitHubClient
from app.repositories.repository import RepositoryRepository
from app.services.code_scanner import CodeScanner, NormalizedRepositoryStructure
from app.services.content_fetcher import FileContentFetcher
from app.services.file_filter import FileFilter

logger = logging.getLogger("repoinsight.services.repository_scanner")


class RepositoryScanService:
    """Service untuk mengorkestrasi basic repository scanning:

    1. Ambil repository dari database
    2. Ambil tree dari GitHub API
    3. Filter file yang relevan
    4. Ambil content file yang diperlukan
    5. Hitung metadata dasar
    6. Kembalikan normalized analysis result
    """

    def __init__(
        self,
        session: AsyncSession,
        github_client: GitHubClient,
        file_filter: FileFilter | None = None,
        max_content_files: int = 100,
    ) -> None:
        self._session = session
        self._github_client = github_client
        self._repo_repo = RepositoryRepository(session)
        self._file_filter = file_filter or FileFilter()
        self._content_fetcher = FileContentFetcher(github_client)
        self._code_scanner = CodeScanner()
        self._max_content_files = max_content_files

    async def scan_repository(self, repository_id: int) -> NormalizedRepositoryStructure:
        """Menjalankan basic repository scan berdasarkan ID repository di database.

        Args:
            repository_id: ID repository di database lokal.

        Returns:
            NormalizedRepositoryStructure berisi hasil scan.

        Raises:
            NotFoundError: Jika repository tidak ditemukan di database.
            GitHubNotFoundError: Jika repository/tree tidak ditemukan di GitHub.
            GitHubRateLimitError, GitHubAuthError, dll.
        """
        repository = await self._repo_repo.get_by_id(repository_id)
        if repository is None:
            raise NotFoundError(f"Repository dengan ID {repository_id} tidak ditemukan")

        logger.info(
            "Memulai scan repository id=%d full_name=%s",
            repository.id,
            repository.full_name,
        )

        parts = repository.full_name.split("/", 1)
        if len(parts) == 2:
            owner, repo_name = parts[0], parts[1]
        else:
            owner, repo_name = repository.owner.github_username, repository.name

        branch = repository.default_branch or "main"

        # Step 2: Ambil tree dari GitHub
        tree_data = await self._github_client.get_tree(
            owner=owner,
            name=repo_name,
            tree_sha_or_branch=branch,
            recursive=True,
        )

        if tree_data.truncated:
            logger.warning(
                "Struktur tree repository %s terpotong (truncated=true) dari GitHub",
                repository.full_name,
            )

        # Hitung total file (blob) di tree
        all_blobs = [item for item in tree_data.tree if item.type == "blob"]
        total_tree_files = len(all_blobs)

        # Step 3: Filter file yang relevan
        relevant_files = [
            item
            for item in all_blobs
            if self._file_filter.should_process(
                item.path, size=item.size, is_dir=False
            )
        ]

        logger.info(
            "Filtering selesai untuk %s: %d/%d file relevan",
            repository.full_name,
            len(relevant_files),
            total_tree_files,
        )

        # Step 4: Ambil content file (dibatasi max_content_files jika repository sangat besar)
        file_entries: list[tuple[str, int, str | None]] = []
        for item in relevant_files[: self._max_content_files]:
            content = await self._content_fetcher.fetch_and_decode(
                owner=owner,
                name=repo_name,
                path=item.path,
                ref=branch,
            )
            file_entries.append((item.path, item.size or 0, content))

        # Tambahkan file sisa jika melebih max_content_files tanpa content
        for item in relevant_files[self._max_content_files :]:
            file_entries.append((item.path, item.size or 0, None))

        # Step 5 & 6: Hitung metadata dan kembalikan normalized result
        result = self._code_scanner.analyze_scanned_files(
            repository_name=repository.full_name,
            branch=branch,
            total_tree_files=total_tree_files,
            file_entries=file_entries,
        )

        logger.info(
            "Scan selesai untuk %s: %d total files, %d source files, %d total lines",
            repository.full_name,
            result.total_files,
            result.total_source_files,
            result.total_lines,
        )
        return result
