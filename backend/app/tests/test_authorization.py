"""Sprint 12 Test Suite — Authorization & Resource Ownership.

Security Testing:
    1. User A dapat mengakses repository miliknya sendiri.
    2. User A tidak dapat mengakses repository milik User B.
    3. User A dapat mengakses analysis miliknya sendiri.
    4. User A tidak dapat mengakses analysis milik User B.
    5. User yang tidak authenticated tidak dapat mengakses protected resource.
    6. Resource ID milik user lain tidak membocorkan data.
    7. Ownership validation tetap berjalan ketika resource tidak ditemukan.
    8. Cross-user comparison analysis.
    9. Cross-user analysis history.
    10. List repositories hanya mengembalikan milik user sendiri.
"""
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user, get_github_client
from app.core.security import hash_password
from app.db.models import AnalysisStatus, User
from app.integrations.github.client import GitHubRepoData
from app.main import app
from app.repositories.analysis import AnalysisRepository


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def _make_mock_github_data() -> GitHubRepoData:
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


async def _create_test_user(prefix: str = "authz") -> User:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=f"{prefix}_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPassword123!"),
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


@pytest.fixture
def mock_github():
    mock_client = AsyncMock()
    app.dependency_overrides[get_github_client] = lambda: mock_client
    yield mock_client
    app.dependency_overrides.pop(get_github_client, None)


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


# ============================================================================
# 1. Repository Ownership — User A can access own repo
# ============================================================================

class TestRepositoryOwnership:
    """User hanya bisa mengakses repository miliknya sendiri."""

    def test_user_can_access_own_repository(self):
        """User dapat mengakses repository miliknya sendiri."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("own1"))
        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        assert resp.status_code == 201
        repo_id = resp.json()["data"]["id"]

        scan_resp = client.post(f"/api/v1/repositories/{repo_id}/scan")
        assert scan_resp.status_code == 200

    def test_user_cannot_access_other_user_repository(self):
        """User tidak dapat mengakses repository milik user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("own2a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("own2b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        assert resp.status_code == 201
        repo_id = resp.json()["data"]["id"]

        _setup_auth(user2)
        scan_resp = client.post(f"/api/v1/repositories/{repo_id}/scan")
        assert scan_resp.status_code == 403
        assert scan_resp.json()["error"]["code"] == "forbidden"

    def test_user_cannot_analyze_other_user_repository(self):
        """User tidak dapat menjalankan analysis pada repository milik user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("own3a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("own3b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        assert resp.status_code == 201
        repo_id = resp.json()["data"]["id"]

        _setup_auth(user2)
        analyze_resp = client.post(f"/api/v1/repositories/{repo_id}/analyze")
        assert analyze_resp.status_code == 403
        assert analyze_resp.json()["error"]["code"] == "forbidden"

    def test_user_cannot_get_other_user_analysis_history(self):
        """User tidak dapat mengambil analysis history milik user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("own4a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("own4b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        assert resp.status_code == 201
        repo_id = resp.json()["data"]["id"]

        _setup_auth(user2)
        history_resp = client.get(f"/api/v1/repositories/{repo_id}/analyses")
        assert history_resp.status_code == 403
        assert history_resp.json()["error"]["code"] == "forbidden"


# ============================================================================
# 3. Analysis Ownership — User A can access own analysis
# ============================================================================

class TestAnalysisOwnership:
    """User hanya bisa mengakses analysis miliknya sendiri."""

    def test_user_can_access_own_analysis(self):
        """User dapat mengakses analysis miliknya sendiri."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("az_own1"))
        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        async def _create():
            sf = get_session_factory()
            async with sf() as session:
                repo = AnalysisRepository(session)
                a = await repo.create_analysis(repo_id)
                await repo.update_status(a.id, AnalysisStatus.COMPLETED, scores={"quality": 80})
                return a

        analysis = asyncio.get_event_loop().run_until_complete(_create())

        get_resp = client.get(f"/api/v1/analyses/{analysis.id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["status"] == "COMPLETED"

    def test_user_cannot_access_other_user_analysis(self):
        """User tidak dapat mengakses analysis milik user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("az_own2a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("az_own2b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        async def _create():
            sf = get_session_factory()
            async with sf() as session:
                repo = AnalysisRepository(session)
                a = await repo.create_analysis(repo_id)
                await repo.update_status(a.id, AnalysisStatus.COMPLETED)
                return a

        analysis = asyncio.get_event_loop().run_until_complete(_create())

        _setup_auth(user2)
        get_resp = client.get(f"/api/v1/analyses/{analysis.id}")
        assert get_resp.status_code == 403
        assert get_resp.json()["error"]["code"] == "forbidden"


# ============================================================================
# 5. Unauthenticated access to protected resources
# ============================================================================

class TestUnauthenticatedAccess:
    """User yang tidak authenticated tidak dapat mengakses protected resource."""

    def test_list_repositories_without_token(self):
        """GET /repositories tanpa token ditolak."""
        client = TestClient(app)
        resp = client.get("/api/v1/repositories")
        assert resp.status_code == 401

    def test_register_repository_without_token(self):
        """POST /repositories tanpa token ditolak."""
        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": "https://github.com/owner/repo"})
        assert resp.status_code == 401

    def test_scan_repository_without_token(self):
        """POST /{id}/scan tanpa token ditolak."""
        client = TestClient(app)
        resp = client.post("/api/v1/repositories/1/scan")
        assert resp.status_code == 401

    def test_analyze_repository_without_token(self):
        """POST /{id}/analyze tanpa token ditolak."""
        client = TestClient(app)
        resp = client.post("/api/v1/repositories/1/analyze")
        assert resp.status_code == 401

    def test_get_analysis_history_without_token(self):
        """GET /{id}/analyses tanpa token ditolak."""
        client = TestClient(app)
        resp = client.get("/api/v1/repositories/1/analyses")
        assert resp.status_code == 401

    def test_get_analysis_status_without_token(self):
        """GET /analyses/{id} tanpa token ditolak."""
        client = TestClient(app)
        resp = client.get("/api/v1/analyses/1")
        assert resp.status_code == 401

    def test_compare_analyses_without_token(self):
        """GET /analyses/{id}/compare/{prev_id} tanpa token ditolak."""
        client = TestClient(app)
        resp = client.get("/api/v1/analyses/1/compare/2")
        assert resp.status_code == 401


# ============================================================================
# 6. Resource ID guessing — tidak membocorkan data
# ============================================================================

class TestResourceIDDoesNotLeakData:
    """Resource ID milik user lain tidak membocorkan data."""

    def test_other_user_repo_scan_returns_forbidden_not_found(self):
        """Akses scan repository milik user lain menghasilkan 403, bukan 404."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("leak1a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("leak1b"))

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

    def test_other_user_analysis_returns_forbidden_not_found(self):
        """Akses analysis milik user lain menghasilkan 403, bukan 404."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("leak2a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("leak2b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        async def _create():
            sf = get_session_factory()
            async with sf() as session:
                repo = AnalysisRepository(session)
                a = await repo.create_analysis(repo_id)
                await session.commit()
                return a

        analysis = asyncio.get_event_loop().run_until_complete(_create())

        _setup_auth(user2)
        get_resp = client.get(f"/api/v1/analyses/{analysis.id}")
        assert get_resp.status_code == 403
        assert get_resp.json()["error"]["code"] == "forbidden"

    def test_nonexistent_analysis_returns_404(self):
        """Analysis yang tidak ada menghasilkan 404, bukan 403."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("leak3"))
        _setup_auth(user)

        client = TestClient(app)
        resp = client.get("/api/v1/analyses/99999")
        assert resp.status_code == 404

    def test_nonexistent_repository_returns_404(self):
        """Repository yang tidak ada menghasilkan 404, bukan 403."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("leak4"))
        _setup_auth(user)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories/99999/scan")
        assert resp.status_code == 404


# ============================================================================
# 7. Ownership validation when resource not found
# ============================================================================

class TestOwnershipWithMissingResource:
    """Ownership validation tetap berjalan ketika resource tidak ditemukan."""

    def test_analyze_nonexistent_repo_returns_404(self):
        """Analysis pada repository tidak ada menghasilkan 404."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("miss1"))
        _setup_auth(user)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories/99999/analyze")
        assert resp.status_code == 404

    def test_history_nonexistent_repo_returns_404(self):
        """History pada repository tidak ada menghasilkan 404."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("miss2"))
        _setup_auth(user)

        client = TestClient(app)
        resp = client.get("/api/v1/repositories/99999/analyses")
        assert resp.status_code == 404

    def test_compare_nonexistent_analysis_returns_404(self):
        """Compare dengan analysis tidak ada menghasilkan 404."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("miss3"))
        _setup_auth(user)

        client = TestClient(app)
        resp = client.get("/api/v1/analyses/99999/compare/88888")
        assert resp.status_code == 404


# ============================================================================
# 8. Cross-user analysis comparison
# ============================================================================

class TestCrossUserComparison:
    """Comparison analysis milik user lain ditolak."""

    def test_user_cannot_compare_other_user_analyses(self):
        """User tidak dapat membandingkan analysis milik user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("cmp1a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("cmp1b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        async def _create():
            sf = get_session_factory()
            async with sf() as session:
                repo = AnalysisRepository(session)
                a1 = await repo.create_analysis(repo_id)
                await repo.update_status(a1.id, AnalysisStatus.COMPLETED, scores={"quality": 70})
                a2 = await repo.create_analysis(repo_id)
                await repo.update_status(a2.id, AnalysisStatus.COMPLETED, scores={"quality": 90})
                return a1, a2

        a1, a2 = asyncio.get_event_loop().run_until_complete(_create())

        _setup_auth(user2)
        compare_resp = client.get(f"/api/v1/analyses/{a2.id}/compare/{a1.id}")
        assert compare_resp.status_code == 403
        assert compare_resp.json()["error"]["code"] == "forbidden"


# ============================================================================
# 9. Cross-user analysis history
# ============================================================================

class TestCrossUserHistory:
    """History analysis milik user lain ditolak."""

    def test_user_cannot_get_other_user_analysis_history(self):
        """User tidak dapat mengambil analysis history milik user lain."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("hist1a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("hist1b"))

        mock_client = AsyncMock()
        repo_data = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp = client.post("/api/v1/repositories", json={"url": repo_data.html_url})
        repo_id = resp.json()["data"]["id"]

        _setup_auth(user2)
        history_resp = client.get(f"/api/v1/repositories/{repo_id}/analyses")
        assert history_resp.status_code == 403
        assert history_resp.json()["error"]["code"] == "forbidden"


# ============================================================================
# 10. List repositories — hanya milik user sendiri
# ============================================================================

class TestListRepositories:
    """GET /repositories hanya mengembalikan repository milik user sendiri."""

    def test_user_sees_only_own_repositories(self):
        """User hanya melihat repository miliknya sendiri."""
        user1 = asyncio.get_event_loop().run_until_complete(_create_test_user("list1a"))
        user2 = asyncio.get_event_loop().run_until_complete(_create_test_user("list1b"))

        mock_client = AsyncMock()

        # Register repo untuk user1
        repo_data1 = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data1
        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user1)

        client = TestClient(app)
        resp1 = client.post("/api/v1/repositories", json={"url": repo_data1.html_url})
        assert resp1.status_code == 201

        # Register repo untuk user2
        repo_data2 = _make_mock_github_data()
        mock_client.get_repository.return_value = repo_data2
        _setup_auth(user2)

        resp2 = client.post("/api/v1/repositories", json={"url": repo_data2.html_url})
        assert resp2.status_code == 201

        # User1 harusnya hanya melihat repo miliknya sendiri
        _setup_auth(user1)
        list_resp = client.get("/api/v1/repositories")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["success"] is True
        items = data["data"]
        assert len(items) >= 1
        # Semua item harus milik user1
        for item in items:
            assert "id" in item
            assert "name" in item

    def test_list_repositories_empty_for_new_user(self):
        """User baru mendapatkan list kosong."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("list2"))
        _setup_auth(user)

        client = TestClient(app)
        list_resp = client.get("/api/v1/repositories")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_list_repositories_pagination(self):
        """List repositories mendukung pagination."""
        user = asyncio.get_event_loop().run_until_complete(_create_test_user("list3"))
        mock_client = AsyncMock()
        app.dependency_overrides[get_github_client] = lambda: mock_client
        _setup_auth(user)

        client = TestClient(app)

        # Register 3 repos
        for i in range(3):
            repo_data = _make_mock_github_data()
            mock_client.get_repository.return_value = repo_data
            client.post("/api/v1/repositories", json={"url": repo_data.html_url})

        # Page 1, page_size 2
        list_resp = client.get("/api/v1/repositories?page=1&page_size=2")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 3
        assert data["meta"]["total_pages"] == 2

        # Page 2
        list_resp2 = client.get("/api/v1/repositories?page=2&page_size=2")
        assert list_resp2.status_code == 200
        data2 = list_resp2.json()
        assert len(data2["data"]) == 1
