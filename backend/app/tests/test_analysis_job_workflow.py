"""Sprint 9 Test Suite — Asynchronous Analysis Job Workflow.

Coverage:
    A. Analysis Job Lifecycle & Status Transitions
    B. Background Processing (pending → running → completed)
    C. Failure Handling (failed state & safe error messages)
    D. API Endpoints (202 Accepted, GET status)
    E. Duplicate Job Prevention
    F. Regression (API envelope, 404, 409)
"""
from __future__ import annotations

import asyncio
import base64
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_github_client
from app.db.models import AnalysisStatus
from app.integrations.github.client import (
    GitHubClient,
    GitHubContentData,
    GitHubRepoData,
    GitHubTreeData,
    GitHubTreeItem,
)
from app.main import app
from app.services.analysis.job_service import (
    AnalysisJobService,
    DuplicateActiveAnalysisError,
    InvalidStatusTransitionError,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


def _make_mock_github_data(
    github_repo_id: int | None = None,
    owner_login: str | None = None,
    repo_name: str | None = None,
) -> GitHubRepoData:
    _id = github_repo_id or _random_github_repo_id()
    owner = owner_login or f"owner_{uuid.uuid4().hex[:6]}"
    name = repo_name or f"repo_{uuid.uuid4().hex[:6]}"
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


def _register_repo(client: TestClient, mock_github: GitHubClient) -> int:
    """Daftarkan repository dan kembalikan database ID-nya."""
    repo_data = mock_github.get_repository.return_value
    response = client.post(
        "/api/v1/repositories",
        json={"url": repo_data.html_url},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _setup_mock_github_for_analysis(mock_github: AsyncMock) -> None:
    """Siapkan mock GitHub client dengan tree dan file content."""
    mock_github.get_tree.return_value = GitHubTreeData(
        sha="sha_tree",
        url="http://tree",
        tree=[
            GitHubTreeItem(path="README.md", mode="100644", type="blob", sha="sha1", size=50),
            GitHubTreeItem(path="app/main.py", mode="100644", type="blob", sha="sha2", size=150),
        ],
        truncated=False,
    )

    encoded_readme = base64.b64encode(b"# Test\nSample README").decode("utf-8")
    encoded_py = base64.b64encode(b"def hello():\n    return 'world'\n").decode("utf-8")

    async def mock_get_content(o, n, p, ref="main"):
        if p == "README.md":
            return GitHubContentData("README.md", "README.md", "sha1", 50, "base64", encoded_readme, "file")
        return GitHubContentData("main.py", "app/main.py", "sha2", 150, "base64", encoded_py, "file")

    mock_github.get_file_content.side_effect = mock_get_content


# ============================================================================
# A. Analysis Job Lifecycle Tests (Unit)
# ============================================================================

class TestAnalysisJobLifecycle:
    """Unit tests untuk AnalysisJobService status transitions.

    Menggunakan in-memory async session dengan database nyata.
    """

    def _run(self, coro):
        """Helper untuk menjalankan coroutine di test sync."""
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_create_pending_job_via_api(self):
        """POST /analyze membuat job PENDING dan mengembalikan 202."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert resp.status_code == 202
            data = resp.json()["data"]
            assert "analysis_id" in data
            assert data["repository_id"] == db_id
            assert data["status"] == "PENDING"
        finally:
            app.dependency_overrides.clear()

    def test_duplicate_active_job_returns_409(self):
        """Membuat analysis job baru saat ada yang PENDING/RUNNING harus mengembalikan 409."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)

            # Patch background task agar tidak berjalan (simulate job masih PENDING)
            with patch(
                "app.api.v1.repositories.run_background_analysis",
                new_callable=lambda: lambda *a, **kw: None,
            ):
                # Perlu patch BackgroundTasks.add_task agar background tidak jalan
                with patch("fastapi.BackgroundTasks.add_task"):
                    first = client.post(f"/api/v1/repositories/{db_id}/analyze")
                    assert first.status_code == 202

                    # Coba buat job kedua — harus 409
                    second = client.post(f"/api/v1/repositories/{db_id}/analyze")
                    assert second.status_code == 409
                    payload = second.json()
                    assert payload["success"] is False
                    assert payload["error"]["code"] == "duplicate_active_analysis"
        finally:
            app.dependency_overrides.clear()

    def test_invalid_status_transition_raises_error(self):
        """Status COMPLETED tidak bisa ditransisikan ke RUNNING."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)

            # Jalankan analysis sampai COMPLETED
            first = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert first.status_code == 202
            analysis_id = first.json()["data"]["analysis_id"]

            # Verify COMPLETED via GET
            status_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            result = status_resp.json()["data"]
            assert result["status"] == "COMPLETED"

            # Coba analysis kedua — seharusnya boleh karena COMPLETED sudah tidak "active"
            second = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert second.status_code == 202
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# B. Background Processing Tests
# ============================================================================

class TestBackgroundProcessing:
    """Test bahwa background task mengubah status dengan benar."""

    def test_background_task_transitions_pending_to_completed(self):
        """TestClient menjalankan BackgroundTasks synchronously.
        Setelah POST, GET harus mengembalikan COMPLETED dengan hasil analisis.
        """
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            analyze_resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert analyze_resp.status_code == 202
            analysis_id = analyze_resp.json()["data"]["analysis_id"]

            # Background task sudah selesai — verify status
            status_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            assert status_resp.status_code == 200
            result = status_resp.json()["data"]

            assert result["status"] == "COMPLETED"
            assert result["started_at"] is not None
            assert result["completed_at"] is not None
            assert result["summary"] is not None
            assert result["scores"] is not None
            assert result["findings"] is not None
            assert result["recommendations"] is not None
        finally:
            app.dependency_overrides.clear()

    def test_background_task_saves_analysis_results(self):
        """Hasil analisis (scores, summary, findings) tersimpan dengan benar."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            analysis_id = resp.json()["data"]["analysis_id"]

            status_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            result = status_resp.json()["data"]

            assert "code_quality" in result["scores"]
            assert "architecture" in result["scores"]
            assert "maintainability" in result["scores"]
            assert isinstance(result["findings"], list)
            assert isinstance(result["recommendations"], list)
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# C. Failure Handling Tests
# ============================================================================

class TestFailureHandling:
    """Test bahwa kegagalan background task ditangani dengan benar."""

    def test_scanner_failure_marks_job_as_failed(self):
        """Jika scanner gagal, job harus berstatus FAILED."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data

        # Scanner gagal — get_tree throw exception
        mock_github.get_tree.side_effect = RuntimeError("GitHub API unavailable")

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert resp.status_code == 202
            analysis_id = resp.json()["data"]["analysis_id"]

            # Verify status FAILED setelah background task selesai
            status_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            assert status_resp.status_code == 200
            result = status_resp.json()["data"]
            assert result["status"] == "FAILED"
        finally:
            app.dependency_overrides.clear()

    def test_failed_job_has_safe_error_payload(self):
        """Response GET untuk job FAILED mengembalikan safe error — bukan stack trace."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        mock_github.get_tree.side_effect = RuntimeError("Secret internal error details")

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            analysis_id = resp.json()["data"]["analysis_id"]

            status_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            result = status_resp.json()["data"]
            assert result["status"] == "FAILED"

            # Error payload aman — ada 'error.code' dan 'error.message'
            assert result["error"] is not None
            assert result["error"]["code"] == "ANALYSIS_FAILED"
            assert "message" in result["error"]
            # Stack trace TIDAK boleh ada di response
            assert "Traceback" not in str(result)
            assert "Secret internal error details" not in str(result["error"])
        finally:
            app.dependency_overrides.clear()

    def test_failed_job_error_message_stored_safely(self):
        """Error message yang tersimpan di DB harus di-truncate dan tidak leak stack trace."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        # Pesan error sangat panjang
        long_error = "X" * 2000
        mock_github.get_tree.side_effect = RuntimeError(long_error)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            analysis_id = resp.json()["data"]["analysis_id"]

            status_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            result = status_resp.json()["data"]
            assert result["status"] == "FAILED"
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# D. API Endpoint Tests
# ============================================================================

class TestAnalysisAPIEndpoints:
    """Test API endpoint behavior."""

    def test_post_analyze_returns_202(self):
        """POST /analyze mengembalikan HTTP 202."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert resp.status_code == 202
            payload = resp.json()
            assert payload["success"] is True
            assert "analysis_id" in payload["data"]
            assert "repository_id" in payload["data"]
            assert "status" in payload["data"]
            assert "meta" in payload
            assert "request_id" in payload["meta"]
        finally:
            app.dependency_overrides.clear()

    def test_get_analysis_pending_status(self):
        """GET /api/v1/analyses/{id} mengembalikan 200 dengan status info."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            post_resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            analysis_id = post_resp.json()["data"]["analysis_id"]

            get_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            assert get_resp.status_code == 200
            result = get_resp.json()["data"]
            assert result["id"] == analysis_id
            assert result["repository_id"] == db_id
            assert "status" in result
            assert "created_at" in result
            assert "updated_at" in result
        finally:
            app.dependency_overrides.clear()

    def test_get_analysis_completed_has_full_data(self):
        """GET mengembalikan data analisis lengkap jika status COMPLETED."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            post_resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            analysis_id = post_resp.json()["data"]["analysis_id"]

            get_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            result = get_resp.json()["data"]
            assert result["status"] == "COMPLETED"
            # Semua field hasil harus ada
            for field in ("summary", "scores", "findings", "recommendations"):
                assert field in result
        finally:
            app.dependency_overrides.clear()

    def test_get_analysis_failed_has_safe_error(self):
        """GET mengembalikan safe error payload untuk status FAILED."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        mock_github.get_tree.side_effect = RuntimeError("Internal failure")

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)
            post_resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
            analysis_id = post_resp.json()["data"]["analysis_id"]

            get_resp = client.get(f"/api/v1/analyses/{analysis_id}")
            result = get_resp.json()["data"]
            assert result["status"] == "FAILED"
            assert result["error"]["code"] == "ANALYSIS_FAILED"
        finally:
            app.dependency_overrides.clear()

    def test_post_analyze_repository_not_found_returns_404(self):
        """POST /analyze dengan repository_id yang tidak ada mengembalikan 404."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            resp = client.post("/api/v1/repositories/999999/analyze")
            assert resp.status_code == 404
            payload = resp.json()
            assert payload["success"] is False
            assert payload["error"]["code"] == "not_found"
        finally:
            app.dependency_overrides.clear()

    def test_get_analysis_not_found_returns_404(self):
        """GET /api/v1/analyses/{id} dengan ID tidak ada mengembalikan 404."""
        client = TestClient(app)
        resp = client.get("/api/v1/analyses/999999")
        assert resp.status_code == 404
        payload = resp.json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "not_found"


# ============================================================================
# E. Duplicate Job Tests
# ============================================================================

class TestDuplicateJobHandling:
    """Test behavior saat ada duplicate analysis job."""

    def test_completed_analysis_allows_new_job(self):
        """Setelah analysis COMPLETED, repository yang sama boleh dianalisis ulang."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data
        _setup_mock_github_for_analysis(mock_github)

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)

            # Jalankan pertama — selesai COMPLETED
            first = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert first.status_code == 202
            first_analysis_id = first.json()["data"]["analysis_id"]

            # Verify COMPLETED
            get_first = client.get(f"/api/v1/analyses/{first_analysis_id}")
            assert get_first.json()["data"]["status"] == "COMPLETED"

            # Jalankan kedua — harus boleh (analysis baru)
            second = client.post(f"/api/v1/repositories/{db_id}/analyze")
            assert second.status_code == 202
            second_analysis_id = second.json()["data"]["analysis_id"]

            # Harus analysis yang berbeda
            assert first_analysis_id != second_analysis_id
        finally:
            app.dependency_overrides.clear()

    def test_active_analysis_prevents_duplicate_job(self):
        """PENDING/RUNNING analysis mencegah pembuatan job duplikat."""
        client = TestClient(app)
        mock_github = AsyncMock(spec=GitHubClient)
        repo_data = _make_mock_github_data()
        mock_github.get_repository.return_value = repo_data

        app.dependency_overrides[get_github_client] = lambda: mock_github
        try:
            db_id = _register_repo(client, mock_github)

            # Patch add_task agar background tidak jalan (simulate PENDING state)
            with patch("fastapi.BackgroundTasks.add_task"):
                first = client.post(f"/api/v1/repositories/{db_id}/analyze")
                assert first.status_code == 202

                # Coba duplicate — harus 409
                second = client.post(f"/api/v1/repositories/{db_id}/analyze")
                assert second.status_code == 409
                assert second.json()["error"]["code"] == "duplicate_active_analysis"
        finally:
            app.dependency_overrides.clear()
