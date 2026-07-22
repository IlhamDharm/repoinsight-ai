"""API endpoint untuk manajemen repository.

Endpoints:
    POST /api/v1/repositories — Daftarkan atau perbarui GitHub repository
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_github_client, get_request_id_dependency
from app.core.response import build_success_payload
from app.integrations.github.client import GitHubClient
from app.schemas.repository import RegisterRepositoryRequest, RepositoryResponse
from app.services.github_sync import RepositorySyncService

router = APIRouter()


@router.post("", status_code=201)
async def register_repository(
    body: RegisterRepositoryRequest,
    request: Request,
    request_id: str = Depends(get_request_id_dependency),
    session: AsyncSession = Depends(get_db_session),
    github_client: GitHubClient = Depends(get_github_client),
) -> JSONResponse:
    """Daftarkan GitHub repository atau perbarui metadata-nya jika sudah ada.

    Menerima GitHub URL, mengambil metadata dari GitHub API, lalu menyimpan
    atau memperbarui record di database.

    Args:
        body: Request body berisi URL GitHub repository.

    Returns:
        201 Created — Repository baru berhasil didaftarkan atau data diperbarui.

    Raises:
        422 — URL tidak valid atau bukan URL GitHub.
        404 — Repository tidak ditemukan di GitHub.
        429 — GitHub API rate limit terlampaui.
        401 — Token GitHub tidak valid.
        504 — GitHub API timeout.
        502 — GitHub API tidak dapat dihubungi atau mengembalikan error server.
    """
    service = RepositorySyncService(session=session, github_client=github_client)
    repository = await service.sync_repository(body.url)

    response_data = RepositoryResponse(
        id=repository.id,
        github_repo_id=repository.github_repo_id,
        name=repository.name,
        full_name=repository.full_name,
        url=repository.url,
        default_branch=repository.default_branch,
        visibility=repository.visibility,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )

    return JSONResponse(
        status_code=201,
        content=build_success_payload(
            response_data.model_dump(mode="json"),
            request_id=request_id,
        ),
    )
