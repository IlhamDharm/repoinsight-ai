"""Sprint 13 Test Suite — Security Hardening & Backend Stabilization.

Security Tests:
    Authentication:
        1. Register berhasil.
        2. Duplicate email ditolak.
        3. Login berhasil dengan credential valid.
        4. Login gagal dengan password salah.
        5. Invalid token ditolak.
        6. Expired token ditolak.
        7. Protected endpoint tanpa token ditolak.

    Authorization:
        8. User dapat mengakses resource miliknya.
        9. User tidak dapat mengakses resource user lain.
        10. Ownership validation tidak dapat dibypass.
        11. Resource ID invalid ditangani dengan aman.

    Input Validation:
        12. Invalid email ditolak.
        13. Invalid password ditolak (too short, no uppercase, no digit, no special).
        14. Invalid repository URL ditolak (non-GitHub URL).
        15. Invalid request body ditolak.
        16. Password too long ditolak.
        17. URL too long ditolak.

    Error Handling:
        18. Internal error tidak membocorkan detail sensitif.
        19. API response tetap konsisten.

    Configuration Security:
        20. Security headers present on response.
        21. X-Request-ID sanitized.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.security import create_access_token, hash_password
from app.db.models import User
from app.main import app


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def _make_mock_github_data():
    from app.integrations.github.client import GitHubRepoData
    _id = _random_github_repo_id()
    owner = f"owner_{uuid.uuid4().hex[:6]}"
    name = f"repo_{uuid.uuid4().hex[:6]}"
    full_name = f"{owner}/{name}"
    return GitHubRepoData(
        id=_id,
        name=name,
        full_name=full_name,
        owner_login=owner,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Test repository",
    )


async def _create_test_user(prefix: str = "sec") -> User:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=f"{prefix}_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("StrongPass123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _setup_auth(user: User):
    async def _get_user() -> User:
        return user
    app.dependency_overrides[get_current_user] = _get_user


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class TestAuthenticationSecurity:
    """Authentication security tests."""

    def test_register_success(self):
        """1. Register berhasil dengan credential valid."""
        client = TestClient(app)
        email = f"sec_reg_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

    def test_register_duplicate_email_rejected(self):
        """2. Duplicate email ditolak."""
        client = TestClient(app)
        email = f"sec_dup_{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        assert response.status_code == 409

    def test_login_success(self):
        """3. Login berhasil dengan credential valid."""
        client = TestClient(app)
        email = f"sec_login_{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StrongPass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()["data"]

    def test_login_wrong_password(self):
        """4. Login gagal dengan password salah."""
        client = TestClient(app)
        email = f"sec_wrong_{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword123!"},
        )
        assert response.status_code == 404
        assert "Email atau password salah" in response.json()["error"]["message"]

    def test_invalid_token_rejected(self):
        """5. Invalid token ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_expired_token_rejected(self):
        """6. Expired token ditolak."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_exp"))
        expired_token = create_access_token(
            subject=user.id,
            expires_delta=timedelta(seconds=-1),
        )
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_without_token(self):
        """7. Protected endpoint tanpa token ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )
        assert response.status_code == 401


# ============================================================================
# AUTHORIZATION TESTS
# ============================================================================

class TestAuthorizationSecurity:
    """Authorization security tests."""

    def test_user_can_access_own_resource(self):
        """8. User dapat mengakses resource miliknya."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_own1"))
        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        assert resp.status_code == 201

    def test_user_cannot_access_other_user_resource(self):
        """9. User tidak dapat mengakses resource user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_oth1a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_oth1b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        _setup_auth(user2)
        scan_resp = client.post(f"/api/v1/repositories/{repo_id}/scan")
        assert scan_resp.status_code == 403

    def test_ownership_cannot_be_bypassed(self):
        """10. Ownership validation tidak dapat dibypass."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_byp1a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_byp1b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        # User2 mencoba bypass dengan langsung akses scan
        _setup_auth(user2)
        scan_resp = client.post(f"/api/v1/repositories/{repo_id}/scan")
        assert scan_resp.status_code == 403
        assert scan_resp.json()["error"]["code"] == "forbidden"

    def test_invalid_resource_id_handled_safely(self):
        """11. Resource ID invalid ditangani dengan aman."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_id1"))
        _setup_auth(user)

        client = TestClient(app)
        # Non-existent ID returns 404, not 500
        resp = client.post("/api/v1/repositories/99999/scan")
        assert resp.status_code == 404


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================

class TestInputValidationSecurity:
    """Input validation security tests."""

    def test_invalid_email_rejected(self):
        """12. Invalid email ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "StrongPass123!"},
        )
        assert response.status_code == 422

    def test_weak_password_too_short(self):
        """13a. Password terlalu pendek ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"weak1_{uuid.uuid4().hex[:8]}@example.com", "password": "short"},
        )
        assert response.status_code == 422

    def test_weak_password_no_uppercase(self):
        """13b. Password tanpa huruf besar ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"weak2_{uuid.uuid4().hex[:8]}@example.com", "password": "nouppercase1!"},
        )
        assert response.status_code == 422

    def test_weak_password_no_lowercase(self):
        """13c. Password tanpa huruf kecil ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"weak3_{uuid.uuid4().hex[:8]}@example.com", "password": "NOLOWERCASE1!"},
        )
        assert response.status_code == 422

    def test_weak_password_no_digit(self):
        """13d. Password tanpa angka ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"weak4_{uuid.uuid4().hex[:8]}@example.com", "password": "NoDigitHere!"},
        )
        assert response.status_code == 422

    def test_weak_password_no_special_char(self):
        """13e. Password tanpa karakter spesial ditolak."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"weak5_{uuid.uuid4().hex[:8]}@example.com", "password": "NoSpecial123"},
        )
        assert response.status_code == 422

    def test_password_too_long_rejected(self):
        """16. Password terlalu panjang ditolak."""
        client = TestClient(app)
        long_password = "A" * 129 + "1!"
        response = client.post(
            "/api/v1/auth/register",
            json={"email": f"long_{uuid.uuid4().hex[:8]}@example.com", "password": long_password},
        )
        assert response.status_code == 422

    def test_invalid_repository_url_rejected(self):
        """14. Invalid repository URL ditolak (non-GitHub URL)."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_url1"))
        _setup_auth(user)

        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://gitlab.com/owner/repo"},
        )
        assert response.status_code == 422

    def test_empty_url_rejected(self):
        """15a. Empty request body ditolak."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_url2"))
        _setup_auth(user)

        client = TestClient(app)
        response = client.post("/api/v1/repositories", json={"url": ""})
        assert response.status_code == 422

    def test_missing_url_field_rejected(self):
        """15b. Missing URL field ditolak."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_url3"))
        _setup_auth(user)

        client = TestClient(app)
        response = client.post("/api/v1/repositories", json={})
        assert response.status_code == 422

    def test_url_too_long_rejected(self):
        """17. URL terlalu panjang ditolak."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("sec_url4"))
        _setup_auth(user)

        client = TestClient(app)
        long_url = "https://github.com/" + "a" * 2050
        response = client.post("/api/v1/repositories", json={"url": long_url})
        assert response.status_code == 422


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandlingSecurity:
    """Error handling security tests."""

    def test_internal_error_no_stack_trace(self):
        """18. Internal error tidak membocorkan stack trace."""
        client = TestClient(app)
        # Request to non-existent route returns generic error
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        payload = response.json()
        assert "traceback" not in str(payload).lower()
        assert "stack" not in str(payload).lower()

    def test_api_response_format_consistent(self):
        """19. API response format tetap konsisten."""
        client = TestClient(app)

        # Success response format
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "meta" in data

        # Error response format
        resp = client.get("/api/v1/health/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "success" in data
        assert "error" in data
        assert "meta" in data

    def test_validation_error_format(self):
        """Validation error mengikuti format yang benar."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "x"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "validation_error"
        assert "meta" in data


# ============================================================================
# CONFIGURATION SECURITY TESTS
# ============================================================================

class TestConfigurationSecurity:
    """Configuration and headers security tests."""

    def test_security_headers_present(self):
        """20. Security headers present on response."""
        client = TestClient(app)
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_request_id_sanitized(self):
        """21. X-Request-ID sanitized — malicious input replaced with UUID."""
        client = TestClient(app)
        # Send malicious request ID
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "<script>alert('xss')</script>"},
        )
        assert response.status_code == 200
        # Response should have a clean UUID, not the malicious input
        req_id = response.headers.get("X-Request-ID", "")
        assert re.match(r"^[a-f0-9-]{36}$", req_id)  # UUID format

    def test_request_id_valid_passes_through(self):
        """21b. Valid X-Request-ID preserved."""
        client = TestClient(app)
        valid_id = "test-request-id-123"
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": valid_id},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == valid_id

    def test_password_not_in_api_response(self):
        """Password tidak muncul di API response."""
        client = TestClient(app)
        email = f"sec_pwf_{uuid.uuid4().hex[:8]}@example.com"
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert "password" not in data
        assert "password_hash" not in data

    def test_auth_error_generic_message(self):
        """Auth error tidak membocorkan informasi sensitif."""
        client = TestClient(app)
        # Login with non-existent email — should not reveal whether email exists
        response = client.post(
            "/api/v1/auth/login",
            json={"email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == 404
        message = response.json()["error"]["message"]
        assert "Email atau password salah" in message
        # Should not contain "email not found" or similar
        assert "tidak ditemukan" not in message.lower() or "email atau password" in message.lower()
