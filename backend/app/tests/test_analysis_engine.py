"""Comprehensive test suite for Sprint 8 AI Analysis Engine."""
from __future__ import annotations

import base64
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_github_client
from app.integrations.github.client import (
    GitHubClient,
    GitHubContentData,
    GitHubRepoData,
    GitHubTreeData,
    GitHubTreeItem,
)
from app.main import app
from app.services.analysis import (
    ComplexityAnalyzer,
    DependencyAnalyzer,
    Finding,
    FindingSeverity,
    LanguageAnalyzer,
    QualityAnalyzer,
    RecommendationEngine,
    ScoringEngine,
    StructureAnalyzer,
)
from app.services.code_scanner import NormalizedRepositoryStructure, ScannedFileMetadata


def _random_github_repo_id() -> int:
    return (uuid.uuid4().int >> 98) & 0x7FFFFFFF


# ============================================================================
# A. Language Analyzer Tests
# ============================================================================

def test_language_analyzer_single_language():
    analyzer = LanguageAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=2,
        total_source_files=2,
        total_lines=100,
        languages={"Python": 2},
        files=[
            ScannedFileMetadata(path="app/main.py", language="Python", size=500, lines=60),
            ScannedFileMetadata(path="app/utils.py", language="Python", size=400, lines=40),
        ],
    )
    summary = analyzer.analyze(snapshot)
    assert summary.dominant_language == "Python"
    assert summary.total_files == 2
    assert summary.total_source_files == 2
    assert summary.total_lines == 100
    assert "Python" in summary.languages
    assert summary.languages["Python"]["percentage"] == 100.0


def test_language_analyzer_multiple_languages():
    analyzer = LanguageAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=3,
        total_source_files=3,
        total_lines=100,
        languages={"Python": 2, "JavaScript": 1},
        files=[
            ScannedFileMetadata(path="app/main.py", language="Python", size=500, lines=70),
            ScannedFileMetadata(path="app/utils.py", language="Python", size=400, lines=10),
            ScannedFileMetadata(path="web/app.js", language="JavaScript", size=300, lines=20),
        ],
    )
    summary = analyzer.analyze(snapshot)
    assert summary.dominant_language == "Python"
    assert summary.languages["Python"]["lines"] == 80
    assert summary.languages["Python"]["percentage"] == 80.0
    assert summary.languages["JavaScript"]["lines"] == 20
    assert summary.languages["JavaScript"]["percentage"] == 20.0


def test_language_analyzer_empty_data():
    analyzer = LanguageAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/empty",
        branch="main",
        total_files=0,
        total_source_files=0,
        total_lines=0,
        languages={},
        files=[],
    )
    summary = analyzer.analyze(snapshot)
    assert summary.dominant_language is None
    assert summary.total_files == 0
    assert summary.total_lines == 0
    assert summary.languages == {}


# ============================================================================
# B. Structure Analyzer Tests
# ============================================================================

def test_structure_analyzer_normal():
    analyzer = StructureAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=3,
        total_source_files=3,
        total_lines=50,
        files=[
            ScannedFileMetadata(path="README.md", language="Markdown", size=100, lines=5),
            ScannedFileMetadata(path="src/main.py", language="Python", size=200, lines=20),
            ScannedFileMetadata(path="src/utils.py", language="Python", size=250, lines=25),
        ],
    )
    findings = analyzer.analyze(snapshot)
    assert len(findings) == 0


def test_structure_analyzer_many_root_files():
    analyzer = StructureAnalyzer()
    files = [
        ScannedFileMetadata(path=f"file_{i}.py", language="Python", size=100, lines=10)
        for i in range(12)
    ]
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=12,
        total_source_files=12,
        total_lines=120,
        files=files,
    )
    findings = analyzer.analyze(snapshot)
    rule_ids = [f.rule_id for f in findings]
    assert "excessive-root-files" in rule_ids


def test_structure_analyzer_deep_directory_structure():
    analyzer = StructureAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=1,
        total_source_files=1,
        total_lines=10,
        files=[
            ScannedFileMetadata(path="a/b/c/d/e/f/g/deep.py", language="Python", size=100, lines=10),
        ],
    )
    findings = analyzer.analyze(snapshot)
    rule_ids = [f.rule_id for f in findings]
    assert "excessive-directory-depth" in rule_ids


# ============================================================================
# C. Complexity Analyzer Tests
# ============================================================================

def test_complexity_analyzer_supported_language():
    analyzer = ComplexityAnalyzer()
    py_code = """
def func1():
    pass

def func2():
    pass

class MyClass:
    def method1(self):
        pass
"""
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=1,
        total_source_files=1,
        total_lines=12,
        files=[
            ScannedFileMetadata(path="main.py", language="Python", size=150, lines=12, content=py_code),
        ],
    )
    findings, metrics = analyzer.analyze(snapshot)
    assert len(metrics) == 1
    assert metrics[0].status == "analyzed"
    assert metrics[0].functions_count == 3
    assert metrics[0].classes_count == 1


def test_complexity_analyzer_unsupported_language_and_syntax_error():
    analyzer = ComplexityAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=2,
        total_source_files=2,
        total_lines=20,
        files=[
            ScannedFileMetadata(path="index.js", language="JavaScript", size=100, lines=10, content="console.log('hi');"),
            ScannedFileMetadata(path="bad.py", language="Python", size=100, lines=10, content="def invalid syntax (("),
        ],
    )
    findings, metrics = analyzer.analyze(snapshot)
    assert len(metrics) == 2
    assert metrics[0].status == "unsupported"
    assert metrics[1].status == "unsupported"


def test_complexity_analyzer_large_complex_file():
    analyzer = ComplexityAnalyzer()
    # Construct 16 functions in 1 file
    funcs = "\n".join([f"def func_{i}():\n    pass" for i in range(16)])
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=1,
        total_source_files=1,
        total_lines=32,
        files=[
            ScannedFileMetadata(path="huge.py", language="Python", size=500, lines=32, content=funcs),
        ],
    )
    findings, metrics = analyzer.analyze(snapshot)
    rule_ids = [f.rule_id for f in findings]
    assert "high-function-count" in rule_ids


# ============================================================================
# D. Dependency Analyzer Tests
# ============================================================================

def test_dependency_analyzer_python_requirements():
    analyzer = DependencyAnalyzer()
    req_content = "fastapi==0.100.0\nsqlalchemy>=2.0.0\n# comment\npytest\n"
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=2,
        total_source_files=2,
        total_lines=30,
        files=[
            ScannedFileMetadata(path="app/main.py", language="Python", size=100, lines=10),
            ScannedFileMetadata(path="requirements.txt", language="Text", size=100, lines=4, content=req_content),
        ],
    )
    findings, summary = analyzer.analyze(snapshot)
    assert summary["has_dependency_manifest"] is True
    assert "requirements.txt" in summary["manifest_files"]
    assert summary["estimated_dependency_count"] == 3
    assert len(findings) == 0


def test_dependency_analyzer_no_manifest():
    analyzer = DependencyAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=1,
        total_source_files=1,
        total_lines=10,
        files=[
            ScannedFileMetadata(path="app/main.py", language="Python", size=100, lines=10),
        ],
    )
    findings, summary = analyzer.analyze(snapshot)
    assert summary["has_dependency_manifest"] is False
    assert len(findings) == 1
    assert findings[0].rule_id == "missing-dependency-manifest"


# ============================================================================
# E. Quality Analyzer Tests
# ============================================================================

def test_quality_analyzer_good_repository():
    analyzer = QualityAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=3,
        total_source_files=2,
        total_lines=40,
        files=[
            ScannedFileMetadata(path="README.md", language="Markdown", size=100, lines=10),
            ScannedFileMetadata(path="src/app.py", language="Python", size=200, lines=20),
            ScannedFileMetadata(path="tests/test_app.py", language="Python", size=150, lines=10),
        ],
    )
    findings = analyzer.analyze(snapshot)
    assert len(findings) == 0


def test_quality_analyzer_missing_readme_and_tests_and_large_file():
    analyzer = QualityAnalyzer()
    snapshot = NormalizedRepositoryStructure(
        repository="owner/repo",
        branch="main",
        total_files=1,
        total_source_files=1,
        total_lines=600,
        files=[
            ScannedFileMetadata(path="monolith.py", language="Python", size=15000, lines=600),
        ],
    )
    findings = analyzer.analyze(snapshot)
    rule_ids = [f.rule_id for f in findings]
    assert "missing-readme" in rule_ids
    assert "missing-tests" in rule_ids
    assert "large-source-file" in rule_ids


# ============================================================================
# F. Scoring Engine Tests
# ============================================================================

def test_scoring_engine_perfect_score():
    engine = ScoringEngine()
    scores = engine.calculate_scores([])
    assert scores.code_quality == 100
    assert scores.architecture == 100
    assert scores.maintainability == 100


def test_scoring_engine_penalties_and_clamps():
    engine = ScoringEngine()
    findings = [
        Finding(rule_id="missing-readme", severity="medium", category="quality", title="No README", description="", recommendation=""),
        Finding(rule_id="missing-tests", severity="medium", category="quality", title="No tests", description="", recommendation=""),
        Finding(rule_id="missing-dependency-manifest", severity="medium", category="dependency", title="No manifest", description="", recommendation=""),
        Finding(rule_id="excessive-root-files", severity="low", category="structure", title="Root files", description="", recommendation=""),
    ]
    scores = engine.calculate_scores(findings)
    # Quality base 100 - 10 (readme) - 15 (tests) = 75
    assert scores.code_quality == 75
    # Arch base 100 - 10 (manifest) - 10 (root files) = 80
    assert scores.architecture == 80
    # Maint base 100 - 10 (readme) - 15 (tests) - 10 (manifest) - 5 (root files) = 60
    assert scores.maintainability == 60


# ============================================================================
# G. Recommendation Engine Tests
# ============================================================================

def test_recommendation_engine_generates_recommendations():
    engine = RecommendationEngine()
    findings = [
        Finding(rule_id="missing-readme", severity="medium", category="quality", title="No README", description="", recommendation="Add README.md file."),
        Finding(rule_id="large-source-file", severity="medium", category="quality", title="Large file", description="", file_path="big.py", recommendation="Split file into modules."),
    ]
    recs = engine.generate_recommendations(findings)
    assert len(recs) == 2
    assert "Add README.md file." in recs[0]
    assert "Split file into modules." in recs[1]
    assert "big.py" in recs[1]


# ============================================================================
# H & I. Analysis API Endpoint Integration Tests
# ============================================================================

def test_analyze_repository_endpoint_success():
    client = TestClient(app)

    repo_id = _random_github_repo_id()
    owner = f"owner_{uuid.uuid4().hex[:6]}"
    repo_name = f"repo_{uuid.uuid4().hex[:6]}"
    full_name = f"{owner}/{repo_name}"

    # 1. Register repository via API
    mock_github = AsyncMock(spec=GitHubClient)
    mock_github.get_repository.return_value = GitHubRepoData(
        id=repo_id,
        name=repo_name,
        full_name=full_name,
        owner_login=owner,
        html_url=f"https://github.com/{full_name}",
        default_branch="main",
        visibility="public",
        private=False,
        description="Test repo for analysis",
    )

    app.dependency_overrides[get_github_client] = lambda: mock_github

    reg_resp = client.post("/api/v1/repositories", json={"url": f"https://github.com/{full_name}"})
    assert reg_resp.status_code == 201
    db_id = reg_resp.json()["data"]["id"]

    # 2. Setup mock tree & files for analysis
    mock_github.get_tree.return_value = GitHubTreeData(
        sha="sha_tree",
        url="http://tree",
        tree=[
            GitHubTreeItem(path="README.md", mode="100644", type="blob", sha="sha1", size=50),
            GitHubTreeItem(path="app/main.py", mode="100644", type="blob", sha="sha2", size=150),
            GitHubTreeItem(path="tests/test_main.py", mode="100644", type="blob", sha="sha3", size=100),
            GitHubTreeItem(path="requirements.txt", mode="100644", type="blob", sha="sha4", size=30),
        ],
        truncated=False,
    )

    encoded_readme = base64.b64encode(b"# Title\nSample README").decode("utf-8")
    encoded_py = base64.b64encode(b"import os\n\ndef run():\n    print('ok')\n").decode("utf-8")
    encoded_test = base64.b64encode(b"def test_run():\n    assert True\n").decode("utf-8")
    encoded_req = base64.b64encode(b"fastapi\npytest\n").decode("utf-8")

    async def mock_get_content(o, n, p, ref="main"):
        if p == "README.md":
            return GitHubContentData("README.md", "README.md", "sha1", 50, "base64", encoded_readme, "file")
        elif p == "app/main.py":
            return GitHubContentData("main.py", "app/main.py", "sha2", 150, "base64", encoded_py, "file")
        elif p == "tests/test_main.py":
            return GitHubContentData("test_main.py", "tests/test_main.py", "sha3", 100, "base64", encoded_test, "file")
        elif p == "requirements.txt":
            return GitHubContentData("requirements.txt", "requirements.txt", "sha4", 30, "base64", encoded_req, "file")
        return GitHubContentData(p, p, "sha_unknown", 10, "base64", "", "file")

    mock_github.get_file_content.side_effect = mock_get_content

    # 3. Trigger analyze endpoint
    analyze_resp = client.post(f"/api/v1/repositories/{db_id}/analyze")
    app.dependency_overrides.clear()

    assert analyze_resp.status_code == 200
    json_body = analyze_resp.json()
    assert json_body["success"] is True
    data = json_body["data"]
    assert data["repository_id"] == db_id
    assert data["status"] == "COMPLETED"
    assert "scores" in data
    assert data["scores"]["code_quality"] == 100
    assert data["scores"]["architecture"] == 100
    assert data["scores"]["maintainability"] == 100
    assert "summary" in data
    assert data["summary"]["dominant_language"] == "Python"
    assert "findings" in data
    assert "recommendations" in data


def test_analyze_repository_endpoint_not_found():
    client = TestClient(app)
    mock_github = AsyncMock(spec=GitHubClient)
    app.dependency_overrides[get_github_client] = lambda: mock_github

    resp = client.post("/api/v1/repositories/999999/analyze")
    app.dependency_overrides.clear()

    assert resp.status_code == 404
    json_body = resp.json()
    assert json_body["success"] is False
    assert json_body["error"]["code"] == "not_found"
