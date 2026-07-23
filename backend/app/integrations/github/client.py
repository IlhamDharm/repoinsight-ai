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


@dataclass(frozen=True)
class GitHubTreeItem:
    """Item individual dalam tree repository (file atau directory)."""

    path: str
    mode: str
    type: str  # "blob" atau "tree"
    sha: str
    size: int | None = None
    url: str | None = None


@dataclass(frozen=True)
class GitHubTreeData:
    """Struktur tree repository dari GitHub API."""

    sha: str
    url: str
    tree: list[GitHubTreeItem]
    truncated: bool = False


@dataclass(frozen=True)
class GitHubContentData:
    """Data isi file dari GitHub API (Contents API)."""

    name: str
    path: str
    sha: str
    size: int
    encoding: str
    content: str
    type: str  # "file"


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

    def _check_status(
        self,
        response: httpx.Response,
        owner: str,
        name: str,
        resource_desc: str = "Resource",
    ) -> None:
        """Validasi status code HTTP response dan raise domain exception yang sesuai jika status != 200."""
        status = response.status_code
        if status == 200:
            return

        if status == 404:
            raise GitHubNotFoundError(
                f"{resource_desc} tidak ditemukan: {owner}/{name}"
            )

        if status == 401:
            raise GitHubAuthError(
                "Autentikasi GitHub API gagal — periksa REPOINSIGHT_GITHUB_TOKEN"
            )

        if status == 403:
            rate_remaining = response.headers.get("x-ratelimit-remaining", "")
            if rate_remaining == "0":
                raise GitHubRateLimitError("GitHub API rate limit terlampaui")
            raise GitHubAuthError(
                f"Akses ditolak oleh GitHub API (403) untuk {owner}/{name}"
            )

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

    async def get_repository(self, owner: str, name: str) -> GitHubRepoData:
        """Ambil metadata repository dari GitHub API."""
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

    async def get_tree(
        self,
        owner: str,
        name: str,
        tree_sha_or_branch: str = "main",
        recursive: bool = True,
    ) -> GitHubTreeData:
        """Ambil struktur git tree repository dari GitHub API.

        Args:
            owner: Username atau org pemilik repository.
            name: Nama repository.
            tree_sha_or_branch: SHA commit, branch, atau tag (default 'main').
            recursive: Jika True, ambil tree secara rekursif.

        Returns:
            GitHubTreeData berisi list item (file dan directory).
        """
        url = f"{self._base_url}/repos/{owner}/{name}/git/trees/{tree_sha_or_branch}"
        params = {"recursive": "1"} if recursive else {}
        logger.debug("GitHub API request: GET tree %s/%s (ref: %s)", owner, name, tree_sha_or_branch)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http_client:
                response = await http_client.get(
                    url, headers=self._build_headers(), params=params
                )
        except httpx.TimeoutException as exc:
            raise GitHubTimeoutError(
                f"GitHub API request timeout untuk tree {owner}/{name}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GitHubConnectionError(
                f"Tidak dapat terhubung ke GitHub API: {exc}"
            ) from exc
        except httpx.TransportError as exc:
            raise GitHubConnectionError(
                f"Transport error saat menghubungi GitHub API: {exc}"
            ) from exc

        self._check_status(response, owner, name, resource_desc=f"Tree '{tree_sha_or_branch}'")
        data = response.json()
        tree_items = [
            GitHubTreeItem(
                path=item.get("path", ""),
                mode=item.get("mode", ""),
                type=item.get("type", ""),
                sha=item.get("sha", ""),
                size=item.get("size"),
                url=item.get("url"),
            )
            for item in data.get("tree", [])
        ]
        return GitHubTreeData(
            sha=data.get("sha", ""),
            url=data.get("url", ""),
            tree=tree_items,
            truncated=data.get("truncated", False),
        )

    async def get_file_content(
        self,
        owner: str,
        name: str,
        path: str,
        ref: str = "main",
    ) -> GitHubContentData:
        """Ambil konten file tertentu dari GitHub Contents API.

        Args:
            owner: Username atau org pemilik repository.
            name: Nama repository.
            path: Relative path file di repository.
            ref: Branch, tag, atau commit SHA (default 'main').

        Returns:
            GitHubContentData yang berisi metadata file dan encoded content (Base64).
        """
        # Bersihkan leading slash dari path agar URL konsisten
        clean_path = path.lstrip("/")
        url = f"{self._base_url}/repos/{owner}/{name}/contents/{clean_path}"
        params = {"ref": ref}
        logger.debug("GitHub API request: GET content %s/%s/%s", owner, name, clean_path)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http_client:
                response = await http_client.get(
                    url, headers=self._build_headers(), params=params
                )
        except httpx.TimeoutException as exc:
            raise GitHubTimeoutError(
                f"GitHub API request timeout untuk file {clean_path} di {owner}/{name}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GitHubConnectionError(
                f"Tidak dapat terhubung ke GitHub API: {exc}"
            ) from exc
        except httpx.TransportError as exc:
            raise GitHubConnectionError(
                f"Transport error saat menghubungi GitHub API: {exc}"
            ) from exc

        self._check_status(
            response, owner, name, resource_desc=f"File '{clean_path}'"
        )
        data = response.json()
        if isinstance(data, list):
            # Jika path mengarah ke direktori, bukannya file
            raise GitHubNotFoundError(
                f"Path '{clean_path}' adalah direktori, bukan file: {owner}/{name}"
            )

        return GitHubContentData(
            name=data.get("name", ""),
            path=data.get("path", ""),
            sha=data.get("sha", ""),
            size=data.get("size", 0),
            encoding=data.get("encoding", ""),
            content=data.get("content", ""),
            type=data.get("type", "file"),
        )

    def _handle_response(
        self,
        response: httpx.Response,
        owner: str,
        name: str,
    ) -> GitHubRepoData:
        """Proses response HTTP dan map ke domain object atau exception."""
        self._check_status(response, owner, name, resource_desc="Repository GitHub")
        return self._parse_repo_data(response.json())

    @staticmethod
    def _parse_repo_data(data: dict) -> GitHubRepoData:
        """Parse JSON response dari GitHub API ke GitHubRepoData."""
        is_private = data.get("private", False)
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

