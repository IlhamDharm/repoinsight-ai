"""API endpoint untuk authentication.

Endpoints:
    POST /api/v1/auth/register — Daftarkan user baru
    POST /api/v1/auth/login   — Login dan dapatkan access token
    GET  /api/v1/auth/me       — Dapatkan data user yang sedang login
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user, get_request_id_dependency
from app.core.response import build_success_payload
from app.db.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Daftarkan user baru.

    Request body:
        email: Email unik.
        password: Password minimal 8 karakter.

    Returns:
        201 — User berhasil didaftarkan (tanpa password).
    """
    service = AuthService(session)
    user = await service.register(email=body.email, password=body.password)

    return JSONResponse(
        status_code=201,
        content=build_success_payload(
            {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
            },
            request_id=request_id,
        ),
    )


@router.post("/login", status_code=200)
async def login(
    body: LoginRequest,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Login dan dapatkan access token.

    Request body:
        email: Email terdaftar.
        password: Password yang benar.

    Returns:
        200 — Access token.
    """
    service = AuthService(session)
    token = await service.authenticate(email=body.email, password=body.password)

    token_data = TokenResponse(access_token=token, token_type="bearer")

    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            token_data.model_dump(),
            request_id=request_id,
        ),
    )


@router.get("/me", status_code=200)
async def get_me(
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Dapatkan data user yang sedang login.

    Returns:
        200 — Data user (tanpa password).
    """
    return JSONResponse(
        status_code=200,
        content=build_success_payload(
            {
                "id": current_user.id,
                "email": current_user.email,
                "is_active": current_user.is_active,
            },
            request_id=request_id,
        ),
    )
