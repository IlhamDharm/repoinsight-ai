"""Pydantic schemas untuk Authentication API."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """Request body untuk registrasi user baru."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password harus minimal 8 karakter")
        return v


class LoginRequest(BaseModel):
    """Request body untuk login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response body untuk access token."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response body untuk data user (tanpa password)."""

    id: int
    email: str
    is_active: bool
    created_at: str
