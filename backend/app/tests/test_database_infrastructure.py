import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import get_db_session
from app.main import app


def test_database_health_endpoint_returns_success() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/db")
        assert response.status_code == 200

        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["status"] == "ok"
        assert payload["data"]["database"] == "postgresql"


@pytest.mark.asyncio
async def test_async_database_session_can_execute_query() -> None:
    async for session in get_db_session():
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
        await session.close()
