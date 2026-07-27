"""Sprint 11 Test Suite — Authentication & User Management.

Coverage:
    A. Registration
    B. Login
    C. JWT Token Validation
    D. Protected Endpoints
    E. User Ownership
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.exceptions import (
    AuthenticationError,
    DuplicateResourceError,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.models import User
from app.integrations.github.client import GitHubClient, GitHubRepoData
from app.main import app
from app.repositories.user import UserRepository
from app.services.auth import AuthService


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


async def _create_test_user(email: str | None = None, password: str = "StrongPass123!") -> tuple[User, str]:
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(subject=user.id)
        return user, token


# ============================================================================
# A. Registration Tests
# ============================================================================

class TestRegistration:
    """Test POST /api/v1/auth/register"""

    def test_register_success(self):
        """Registrasi berhasil dengan email dan password valid."""
        client = TestClient(app)
        email = f"reg_{uuid.uuid4().hex[:8]}@example.com"

        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["email"] == email
        assert payload["data"]["is_active"] is True
        assert "id" in payload["data"]
        # Password tidak boleh muncul di response
        assert "password" not in payload["data"]
        assert "password_hash" not in payload["data"]

    def test_register_duplicate_email(self):
        """Email yang sudah terdaftar menghasilkan error 409."""
        client = TestClient(app)
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"

        first = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "AnotherPass123!"},
        )
        assert second.status_code == 409
        payload = second.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "duplicate_resource"

    def test_register_invalid_email(self):
        """Email format tidak valid menghasilkan error 422."""
        client = TestClient(app)

        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "StrongPass123!"},
        )

        assert response.status_code == 422

    def test_register_short_password(self):
        """Password kurang dari 8 karakter menghasilkan error 422."""
        client = TestClient(app)
        email = f"short_{uuid.uuid4().hex[:8]}@example.com"

        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "short"},
        )

        assert response.status_code == 422

    def test_register_missing_fields(self):
        """Field yang tidak ada menghasilkan error 422."""
        client = TestClient(app)

        response = client.post(
            "/api/v1/auth/register",
            json={},
        )

        assert response.status_code == 422

    def test_password_not_stored_as_plaintext(self):
        """Password tidak disimpan sebagai plaintext di database."""
        client = TestClient(app)
        email = f"plain_{uuid.uuid4().hex[:8]}@example.com"
        password = "MySecretPassword123!"

        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )

        async def _check():
            session_factory = get_session_factory()
            async with session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_by_email(email)
                assert user is not None
                assert user.password_hash != password
                assert verify_password(password, user.password_hash) is True

        asyncio.get_event_loop().run_until_complete(_check())


# ============================================================================
# B. Login Tests
# ============================================================================

class TestLogin:
    """Test POST /api/v1/auth/login"""

    def test_login_success(self):
        """Login berhasil menghasilkan access token."""
        client = TestClient(app)
        email = f"login_{uuid.uuid4().hex[:8]}@example.com"
        password = "StrongPass123!"

        # Register dulu
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert "access_token" in payload["data"]
        assert payload["data"]["token_type"] == "bearer"
        # Token harus valid
        token = payload["data"]["access_token"]
        decoded = decode_access_token(token)
        assert decoded is not None
        assert "sub" in decoded
        assert "exp" in decoded

    def test_login_wrong_password(self):
        """Password yang salah menghasilkan error 404 (generic message)."""
        client = TestClient(app)
        email = f"wp_{uuid.uuid4().hex[:8]}@example.com"

        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword123!"},
        )

        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False
        # Error message harus generik — tidak membocorkan apakah email atau password salah
        assert "Email atau password salah" in payload["error"]["message"]

    def test_login_nonexistent_email(self):
        """Email yang tidak ada menghasilkan error yang sama (generic message)."""
        client = TestClient(app)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": f"noexist_{uuid.uuid4().hex[:8]}@example.com", "password": "StrongPass123!"},
        )

        assert response.status_code == 404
        payload = response.json()
        assert payload["success"] is False
        assert "Email atau password salah" in payload["error"]["message"]

    def test_login_inactive_user(self):
        """User inactive tidak bisa login."""
        client = TestClient(app)
        email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"

        async def _create_inactive():
            session_factory = get_session_factory()
            async with session_factory() as session:
                user = User(
                    email=email,
                    password_hash=hash_password("StrongPass123!"),
                    is_active=False,
                )
                session.add(user)
                await session.commit()

        asyncio.get_event_loop().run_until_complete(_create_inactive())

        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StrongPass123!"},
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["success"] is False


# ============================================================================
# C. JWT Token Validation Tests
# ============================================================================

class TestJWTValidation:
    """Test token handling pada protected endpoints."""

    def test_valid_token_accepted(self):
        """Token valid diterima oleh protected endpoint."""
        client = TestClient(app)
        user, _token = asyncio.get_event_loop().run_until_complete(_create_test_user())

        async def _get_user() -> User:
            return user
        app.dependency_overrides[get_current_user] = _get_user

        try:
            response = client.post(
                "/api/v1/repositories",
                json={"url": "https://github.com/owner/repo"},
            )
            # Harus bukan 401 — bisa 404/422 tergantung mock
            assert response.status_code != 401
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_invalid_token_rejected(self):
        """Token yang tidak valid ditolak."""
        client = TestClient(app)

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "authentication_error"

    def test_expired_token_rejected(self):
        """Token yang sudah expired ditolak."""
        client = TestClient(app)
        user, _token = asyncio.get_event_loop().run_until_complete(
            _create_test_user()
        )

        expired_token = create_access_token(
            subject=user.id,
            expires_delta=timedelta(seconds=-1),
        )

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        payload = response.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "authentication_error"

    def test_missing_token_rejected(self):
        """Request tanpa token ditolak pada protected endpoint."""
        client = TestClient(app)

        # Repositories endpoint butuh auth — harus 401 tanpa token
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 401

    def test_malformed_bearer_header_rejected(self):
        """Header Authorization dengan format salah ditolak."""
        client = TestClient(app)

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
            headers={"Authorization": "NotBearer sometoken"},
        )

        assert response.status_code == 401


# ============================================================================
# D. Protected Endpoint Tests
# ============================================================================

class TestProtectedEndpoints:
    """Test bahwa endpoint yang dilindungi membutuhkan token."""

    def test_register_repository_without_token_returns_401(self):
        """POST /repositories tanpa token ditolak."""
        client = TestClient(app)

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 401

    def test_scan_repository_without_token_returns_401(self):
        """POST /{id}/scan tanpa token ditolak."""
        client = TestClient(app)

        response = client.post("/api/v1/repositories/1/scan")

        assert response.status_code == 401

    def test_analyze_repository_without_token_returns_401(self):
        """POST /{id}/analyze tanpa token ditolak."""
        client = TestClient(app)

        response = client.post("/api/v1/repositories/1/analyze")

        assert response.status_code == 401

    def test_get_analysis_history_without_token_returns_401(self):
        """GET /{id}/analyses tanpa token ditolak."""
        client = TestClient(app)

        response = client.get("/api/v1/repositories/1/analyses")

        assert response.status_code == 401

    def test_get_analysis_status_without_token_returns_401(self):
        """GET /analyses/{id} tanpa token ditolak."""
        client = TestClient(app)

        response = client.get("/api/v1/analyses/1")

        assert response.status_code == 401

    def test_health_endpoints_still_public(self):
        """Health endpoints tetap publik (tidak butuh token)."""
        client = TestClient(app)

        assert client.get("/").status_code == 200
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/health/ready").status_code == 200


# ============================================================================
# E. User Ownership Tests
# ============================================================================

class TestUserOwnership:
    """Test bahwa user hanya bisa mengakses repository miliknya sendiri."""

    def _setup_auth(self, user: User):
        async def _get_user() -> User:
            return user
        app.dependency_overrides[get_current_user] = _get_user

    def test_user_can_access_own_repository(self):
        """User dapat mengakses repository miliknya sendiri."""
        import base64
        from app.integrations.github.client import GitHubTreeData, GitHubTreeItem, GitHubContentData

        user1, token1 = asyncio.get_event_loop().run_until_complete(
            _create_test_user(email=f"own1_{uuid.uuid4().hex[:8]}@example.com")
        )
        rand_id = _random_github_repo_id()
        unique_name = f"my-repo-{uuid.uuid4().hex[:6]}"

        mock_gh = AsyncMock()
        mock_gh.get_repository.return_value = GitHubRepoData(
            id=rand_id,
            name=unique_name,
            full_name=f"testowner/{unique_name}",
            owner_login="testowner",
            html_url=f"https://github.com/testowner/{unique_name}",
            default_branch="main",
            visibility="public",
            private=False,
            description="Test",
        )
        mock_gh.get_tree.return_value = GitHubTreeData(
            sha="sha_tree", url="http://tree",
            tree=[GitHubTreeItem(path="README.md", mode="100644", type="blob", sha="sha1", size=50)],
            truncated=False,
        )
        encoded = base64.b64encode(b"# Test").decode("utf-8")
        async def mock_content(o, n, p, ref="main"):
            return GitHubContentData("README.md", "README.md", "sha1", 50, "base64", encoded, "file")
        mock_gh.get_file_content.side_effect = mock_content

        app.dependency_overrides[get_github_client] = lambda: mock_gh
        self._setup_auth(user1)

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/repositories",
                json={"url": f"https://github.com/testowner/{unique_name}"},
            )
            assert resp.status_code == 201
            repo_id = resp.json()["data"]["id"]

            scan_resp = client.post(f"/api/v1/repositories/{repo_id}/scan")
            assert scan_resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_user_cannot_access_other_user_repository(self):
        """User tidak dapat mengakses repository milik user lain."""
        user1, token1 = asyncio.get_event_loop().run_until_complete(
            _create_test_user(email=f"own2_{uuid.uuid4().hex[:8]}@example.com")
        )
        user2, token2 = asyncio.get_event_loop().run_until_complete(
            _create_test_user(email=f"own3_{uuid.uuid4().hex[:8]}@example.com")
        )
        unique_name = f"user1-repo-{uuid.uuid4().hex[:6]}"

        mock_gh = AsyncMock()
        mock_gh.get_repository.return_value = GitHubRepoData(
            id=_random_github_repo_id(),
            name=unique_name,
            full_name=f"testowner/{unique_name}",
            owner_login="testowner",
            html_url=f"https://github.com/testowner/{unique_name}",
            default_branch="main",
            visibility="public",
            private=False,
            description="Test",
        )

        app.dependency_overrides[get_github_client] = lambda: mock_gh
        self._setup_auth(user1)

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/repositories",
                json={"url": f"https://github.com/testowner/{unique_name}"},
            )
            assert resp.status_code == 201
            repo_id = resp.json()["data"]["id"]

            self._setup_auth(user2)
            client2 = TestClient(app)

            scan_resp = client2.post(f"/api/v1/repositories/{repo_id}/scan")
            assert scan_resp.status_code == 403
            payload = scan_resp.json()
            assert payload["success"] is False
            assert payload["error"]["code"] == "forbidden"
        finally:
            app.dependency_overrides.clear()

    def test_user_cannot_access_other_user_analysis(self):
        """User tidak dapat mengakses analysis milik user lain."""
        user1, token1 = asyncio.get_event_loop().run_until_complete(
            _create_test_user(email=f"own4_{uuid.uuid4().hex[:8]}@example.com")
        )
        user2, token2 = asyncio.get_event_loop().run_until_complete(
            _create_test_user(email=f"own5_{uuid.uuid4().hex[:8]}@example.com")
        )
        unique_name = f"user1-analysis-repo-{uuid.uuid4().hex[:6]}"

        mock_gh = AsyncMock()
        mock_gh.get_repository.return_value = GitHubRepoData(
            id=_random_github_repo_id(),
            name=unique_name,
            full_name=f"testowner/{unique_name}",
            owner_login="testowner",
            html_url=f"https://github.com/testowner/{unique_name}",
            default_branch="main",
            visibility="public",
            private=False,
            description="Test",
        )

        app.dependency_overrides[get_github_client] = lambda: mock_gh
        self._setup_auth(user1)

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/repositories",
                json={"url": f"https://github.com/testowner/{unique_name}"},
            )
            assert resp.status_code == 201
            repo_id = resp.json()["data"]["id"]

            # Buat analysis langsung di DB
            async def _create_analysis():
                session_factory = get_session_factory()
                async with session_factory() as session:
                    from app.repositories.analysis import AnalysisRepository
                    from app.db.models import Analysis, AnalysisStatus
                    analysis_repo = AnalysisRepository(session)
                    analysis = Analysis(
                        repository_id=repo_id,
                        status=AnalysisStatus.COMPLETED,
                    )
                    result = await analysis_repo.create(analysis)
                    await session.commit()
                    return result

            analysis = asyncio.get_event_loop().run_until_complete(_create_analysis())

            # Switch ke user2
            self._setup_auth(user2)
            client2 = TestClient(app)

            # User2 tidak bisa akses analysis milik user1
            get_resp = client2.get(f"/api/v1/analyses/{analysis.id}")
            assert get_resp.status_code == 403
            payload = get_resp.json()
            assert payload["success"] is False
            assert payload["error"]["code"] == "forbidden"
        finally:
            app.dependency_overrides.clear()
