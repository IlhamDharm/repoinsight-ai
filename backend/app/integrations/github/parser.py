"""GitHub URL parser utility.

Mengekstrak owner dan repository name dari GitHub URL.
Mendukung format:
- https://github.com/owner/repo
- https://github.com/owner/repo.git
- https://github.com/owner/repo/
- http://github.com/owner/repo
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.exceptions import ValidationError

# Regex: wajib https?://github.com/, lalu owner/repo, lalu opsional .git dan/atau trailing slash
_GITHUB_REPO_PATTERN = re.compile(
    r"^https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedGitHubRepo:
    """Hasil parsing GitHub repository URL."""

    owner: str
    name: str


def parse_github_url(url: str) -> ParsedGitHubRepo:
    """Parse GitHub repository URL dan ekstrak owner dan nama repository.

    Args:
        url: URL GitHub repository.

    Returns:
        ParsedGitHubRepo berisi owner dan name.

    Raises:
        ValidationError: Jika URL kosong, bukan URL GitHub, atau format tidak valid.
    """
    if not url or not url.strip():
        raise ValidationError("GitHub URL tidak boleh kosong")

    url = url.strip()

    if "github.com" not in url.lower():
        raise ValidationError(
            f"URL bukan URL GitHub yang valid: {url}",
            details={"url": url, "reason": "URL harus mengandung github.com"},
        )

    match = _GITHUB_REPO_PATTERN.match(url)
    if not match:
        raise ValidationError(
            f"Format URL GitHub tidak valid: {url}",
            details={
                "url": url,
                "reason": "Format yang didukung: https://github.com/owner/repo",
            },
        )

    owner = match.group(1)
    name = match.group(2)
    return ParsedGitHubRepo(owner=owner, name=name)
