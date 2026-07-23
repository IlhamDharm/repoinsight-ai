"""Service untuk mengambil dan mendecode isi file dari GitHub API secara aman."""
from __future__ import annotations

import base64
import logging

from app.core.exceptions import GitHubNotFoundError
from app.integrations.github.client import GitHubClient

logger = logging.getLogger("repoinsight.services.content_fetcher")


class FileContentFetcher:
    """Fetcher aman untuk mengambil isi file dari GitHub API."""

    def __init__(self, github_client: GitHubClient) -> None:
        self._github_client = github_client

    async def fetch_and_decode(
        self,
        owner: str,
        name: str,
        path: str,
        ref: str = "main",
        max_bytes: int = 500 * 1024,
    ) -> str | None:
        """Mengambil dan mendekode konten file dari Base64 ke UTF-8 text.

        Args:
            owner: Username atau org pemilik repository.
            name: Nama repository.
            path: Relative path file di repository.
            ref: Branch, tag, atau commit SHA (default 'main').
            max_bytes: Batas maksimum ukuran file yang diproses.

        Returns:
            String konten file (UTF-8) jika berhasil, atau None jika file
            terlalu besar, binary, tidak valid, atau tidak ditemukan.
        """
        try:
            content_data = await self._github_client.get_file_content(
                owner, name, path, ref=ref
            )
        except GitHubNotFoundError:
            logger.warning("File tidak ditemukan saat fetch content: %s/%s/%s", owner, name, path)
            return None
        except Exception as exc:
            logger.warning(
                "Gagal mengambil content file %s/%s/%s: %s", owner, name, path, exc
            )
            raise

        if content_data.size > max_bytes:
            logger.debug(
                "File %s melebihi batas ukuran (%d bytes > %d bytes)",
                path,
                content_data.size,
                max_bytes,
            )
            return None

        raw_content = content_data.content
        if not raw_content:
            return ""

        if content_data.encoding == "base64":
            try:
                decoded_bytes = base64.b64decode(raw_content.encode("utf-8"))
                return decoded_bytes.decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                logger.warning(
                    "Gagal decode content file %s (bukan UTF-8 / binary): %s", path, exc
                )
                return None
        else:
            # Fallback jika encoding bukan base64
            try:
                return raw_content
            except Exception:
                return None
