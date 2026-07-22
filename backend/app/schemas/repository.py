"""Pydantic schemas untuk Repository API."""
from __future__ import annotations

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
