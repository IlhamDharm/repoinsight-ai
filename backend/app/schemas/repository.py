"""Pydantic schemas untuk Repository API."""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, field_validator


class RegisterRepositoryRequest(BaseModel):
    """Request body untuk mendaftarkan GitHub repository."""

    url: str

    @field_validator("url")
    @classmethod
    def url_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("URL tidak boleh kosong")
        return stripped

    @field_validator("url")
    @classmethod
    def url_must_be_github(cls, v: str) -> str:
        stripped = v.strip()
        if not re.match(r"^https?://github\.com/", stripped, re.IGNORECASE):
            raise ValueError(
                "URL harus berformat https://github.com/owner/repo"
            )
        if len(stripped) > 2048:
            raise ValueError("URL terlalu panjang (maksimal 2048 karakter)")
        return stripped


class RepositoryResponse(BaseModel):
    """Response body untuk data repository yang berhasil didaftarkan/diperbarui."""

    id: int
    github_repo_id: int
    name: str
    full_name: str
    url: str
    default_branch: str
    visibility: str
    created_at: datetime
    updated_at: datetime


class RepositoryListItem(BaseModel):
    """Schema untuk item dalam daftar repository."""

    id: int
    github_repo_id: int
    name: str
    full_name: str
    url: str
    default_branch: str
    visibility: str
    created_at: datetime
    updated_at: datetime


class ScannedFileResponse(BaseModel):
    """Schema untuk metadata file yang telah di-scan."""

    path: str
    language: str
    size: int
    lines: int


class RepositoryScanResponse(BaseModel):
    """Response body untuk normalized repository scan result."""

    repository: str
    branch: str
    total_files: int
    total_source_files: int
    total_lines: int
    languages: dict[str, int]
    files: list[ScannedFileResponse]

