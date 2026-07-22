"""Async GitHub API client menggunakan httpx.

Client ini bertanggung jawab untuk komunikasi dengan GitHub API.
Semua error dari HTTP layer di-translate ke domain exceptions.

GitHub token tidak pernah di-log atau di-expose ke response.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.exceptions import (
    ExternalServiceError,
    GitHubAuthError,
    GitHubConnectionError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)

logger = logging.getLogger("repoinsight.github")


@dataclass(frozen=True)
class GitHubRepoData:
    """Data mentah dari GitHub API untuk sebuah repository."""

    id: int
    name: str
    full_name: str
    owner_login: str
    html_url: str
    default_branch: str
    visibility: str
    private: bool
    description: str | None


class GitHubClient:
    """Async client untuk GitHub REST API v3.

    Menggunakan httpx.AsyncClient secara internal. Token GitHub tidak
    pernah di-log atau di-expose ke layer lain.

    Usage:
        client = GitHubClient(base_url="https://api.github.com", token="ghp_...", timeout=10.0)
        repo_data = await client.get_repository("owner", "repo")
    """

    def __init__(
        self,
        base_url: str,
        token: str = "",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        """Bangun headers HTTP, termasuk Authorization jika token tersedia.

        Token tidak di-log oleh method ini.
        """
        headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_repository(self, owner: str, name: str) -> GitHubRepoData:
        """Ambil metadata repository dari GitHub API.

        Args:
            owner: Username atau org pemilik repository.
            name: Nama repository.

        Returns:
            GitHubRepoData berisi metadata repository.

        Raises:
            GitHubNotFoundError: Repository tidak ditemukan (404).
            GitHubAuthError: Token tidak valid atau tidak memiliki akses (401).
            GitHubRateLimitError: Rate limit GitHub terlampaui (403).
            ExternalServiceError: GitHub mengembalikan error server (5xx).
            GitHubTimeoutError: Request timeout.
            GitHubConnectionError: Tidak bisa terhubung ke GitHub API.
        """
        url = f"{self._base_url}/repos/{owner}/{name}"
        logger.debug("GitHub API request: GET %s/%s", owner, name)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http_client:
                response = await http_client.get(url, headers=self._build_headers())
        except httpx.TimeoutException as exc:
            raise GitHubTimeoutError(
                f"GitHub API request timeout untuk {owner}/{name}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GitHubConnectionError(
                f"Tidak dapat terhubung ke GitHub API: {exc}"
            ) from exc
        except httpx.TransportError as exc:
            raise GitHubConnectionError(
                f"Transport error saat menghubungi GitHub API: {exc}"
            ) from exc

        return self._handle_response(response, owner, name)

    def _handle_response(
        self,
        response: httpx.Response,
        owner: str,
        name: str,
    ) -> GitHubRepoData:
        """Proses response HTTP dan map ke domain object atau exception."""
        status = response.status_code

        if status == 200:
            logger.debug("GitHub API success untuk %s/%s", owner, name)
            return self._parse_repo_data(response.json())

        if status == 404:
            raise GitHubNotFoundError(
                f"Repository GitHub tidak ditemukan: {owner}/{name}"
            )

        if status == 401:
            raise GitHubAuthError(
                "Autentikasi GitHub API gagal — periksa REPOINSIGHT_GITHUB_TOKEN"
            )

        if status == 403:
            # GitHub menggunakan 403 untuk rate limit dan forbidden
            rate_remaining = response.headers.get("x-ratelimit-remaining", "")
            if rate_remaining == "0":
                raise GitHubRateLimitError("GitHub API rate limit terlampaui")
            raise GitHubAuthError(
                f"Akses ditolak oleh GitHub API (403) untuk {owner}/{name}"
            )

        # 5xx dan lainnya
        logger.warning(
            "GitHub API mengembalikan status tidak terduga: %d untuk %s/%s",
            status,
            owner,
            name,
        )
        raise ExternalServiceError(
            f"GitHub API mengembalikan status {status}",
            details={"status_code": status, "repository": f"{owner}/{name}"},
        )

    @staticmethod
    def _parse_repo_data(data: dict) -> GitHubRepoData:
        """Parse JSON response dari GitHub API ke GitHubRepoData."""
        is_private = data.get("private", False)
        # GitHub API mengembalikan "visibility" di versi terbaru
        visibility = data.get("visibility") or ("private" if is_private else "public")

        return GitHubRepoData(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            owner_login=data["owner"]["login"],
            html_url=data["html_url"],
            default_branch=data["default_branch"],
            visibility=visibility,
            private=is_private,
            description=data.get("description"),
        )
