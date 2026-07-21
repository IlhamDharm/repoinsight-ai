from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_standard_payload() -> None:
    response = client.get("/")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["service"] == "RepoInsight AI API"
    assert payload["meta"]["request_id"]


def test_health_live_endpoint_returns_standard_payload() -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["service"] == "RepoInsight AI API"
    assert payload["data"]["environment"] == "development"


def test_unknown_route_returns_standard_error_payload() -> None:
    response = client.get("/not-found")
    assert response.status_code == 404

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"
    assert payload["meta"]["request_id"]


def test_request_id_header_is_returned() -> None:
    response = client.get("/", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"
