"""Test untuk GitHub URL parser.

Test murni (pure unit tests) — tidak butuh database atau HTTP client.
Memverifikasi semua kombinasi format URL yang valid dan invalid.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.integrations.github.parser import ParsedGitHubRepo, parse_github_url


# ─── Valid URL ─────────────────────────────────────────────────────────────────

def test_parse_standard_https_url() -> None:
    result = parse_github_url("https://github.com/owner/repo")
    assert isinstance(result, ParsedGitHubRepo)
    assert result.owner == "owner"
    assert result.name == "repo"


def test_parse_url_with_git_suffix() -> None:
    result = parse_github_url("https://github.com/owner/repo.git")
    assert result.owner == "owner"
    assert result.name == "repo"


def test_parse_url_with_trailing_slash() -> None:
    result = parse_github_url("https://github.com/owner/repo/")
    assert result.owner == "owner"
    assert result.name == "repo"


def test_parse_url_with_git_suffix_and_trailing_slash() -> None:
    result = parse_github_url("https://github.com/owner/repo.git/")
    assert result.owner == "owner"
    assert result.name == "repo"


def test_parse_url_with_http_scheme() -> None:
    """http:// (non-HTTPS) juga harus diterima sesuai spesifikasi."""
    result = parse_github_url("http://github.com/owner/repo")
    assert result.owner == "owner"
    assert result.name == "repo"


def test_parse_url_with_leading_and_trailing_whitespace() -> None:
    result = parse_github_url("  https://github.com/owner/repo  ")
    assert result.owner == "owner"
    assert result.name == "repo"


def test_parse_url_with_hyphenated_names() -> None:
    result = parse_github_url("https://github.com/my-org/my-repo")
    assert result.owner == "my-org"
    assert result.name == "my-repo"


def test_parse_url_with_underscore_and_dot_in_names() -> None:
    result = parse_github_url("https://github.com/owner_name/repo.name")
    assert result.owner == "owner_name"
    assert result.name == "repo.name"


def test_parse_url_with_numeric_names() -> None:
    result = parse_github_url("https://github.com/org123/repo456")
    assert result.owner == "org123"
    assert result.name == "repo456"


def test_result_is_frozen_dataclass() -> None:
    """ParsedGitHubRepo harus immutable."""
    result = parse_github_url("https://github.com/owner/repo")
    with pytest.raises((AttributeError, TypeError)):
        result.owner = "other"  # type: ignore[misc]


# ─── Invalid URL ───────────────────────────────────────────────────────────────

def test_empty_string_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_github_url("")


def test_whitespace_only_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_github_url("   ")


def test_non_github_url_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_github_url("https://gitlab.com/owner/repo")


def test_bitbucket_url_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_github_url("https://bitbucket.org/owner/repo")


def test_github_without_scheme_raises_validation_error() -> None:
    """github.com/owner/repo tanpa scheme tidak valid."""
    with pytest.raises(ValidationError):
        parse_github_url("github.com/owner/repo")


def test_github_url_without_repo_raises_validation_error() -> None:
    """URL hanya sampai owner tanpa nama repo tidak valid."""
    with pytest.raises(ValidationError):
        parse_github_url("https://github.com/owner")


def test_github_url_root_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_github_url("https://github.com/")


def test_github_url_with_extra_path_segments_raises_validation_error() -> None:
    """URL dengan path terlalu dalam (bukan root repo) tidak valid."""
    with pytest.raises(ValidationError):
        parse_github_url("https://github.com/owner/repo/tree/main")


def test_random_string_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_github_url("bukan-url-sama-sekali")


def test_validation_error_contains_url_in_details_for_non_github() -> None:
    url = "https://gitlab.com/owner/repo"
    exc = pytest.raises(ValidationError, parse_github_url, url)
    assert exc.value.details is not None
    assert "url" in exc.value.details
