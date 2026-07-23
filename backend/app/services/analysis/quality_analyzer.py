"""Code Quality Analyzer module with rule-based static evaluation."""
from __future__ import annotations

import os

from app.services.analysis.types import Finding, FindingSeverity
from app.services.code_scanner import NormalizedRepositoryStructure


class QualityAnalyzer:
    """Analyzer untuk mengevaluasi kualitas dasar repository berdasarkan aturan static analysis."""

    def analyze(self, snapshot: NormalizedRepositoryStructure) -> list[Finding]:
        """Menghasilkan list of Finding berdasarkan indikator kualitas."""
        findings: list[Finding] = []

        if not snapshot.files:
            return findings

        has_readme = False
        has_tests = False

        for file_meta in snapshot.files:
            path_lower = file_meta.path.lower()
            filename = os.path.basename(path_lower)

            # Check README
            if filename in ("readme.md", "readme.txt", "readme", "readme.rst"):
                has_readme = True

            # Check Test directory / test files
            if (
                "/tests/" in path_lower
                or "/test/" in path_lower
                or "/spec/" in path_lower
                or "/__tests__/" in path_lower
                or path_lower.startswith("tests/")
                or path_lower.startswith("test/")
                or filename.startswith("test_")
                or filename.endswith("_test.py")
                or filename.endswith("_test.go")
                or filename.endswith(".spec.ts")
                or filename.endswith(".spec.js")
                or filename.endswith(".test.ts")
                or filename.endswith(".test.js")
            ):
                has_tests = True

            # Rule: Large source file (> 500 lines and <= 1000 lines)
            if file_meta.lines > 500 and file_meta.lines <= 1000:
                findings.append(
                    Finding(
                        rule_id="large-source-file",
                        severity=FindingSeverity.MEDIUM.value,
                        category="quality",
                        title=f"Large file `{file_meta.path}`",
                        description=f"File `{file_meta.path}` contains {file_meta.lines} lines of code. Large files can be hard to maintain.",
                        file_path=file_meta.path,
                        recommendation="Consider breaking down large files into smaller modules or helper files.",
                    )
                )

            # Rule: Very large source file (> 1000 lines)
            elif file_meta.lines > 1000:
                findings.append(
                    Finding(
                        rule_id="very-large-source-file",
                        severity=FindingSeverity.HIGH.value,
                        category="quality",
                        title=f"Very large file `{file_meta.path}`",
                        description=f"File `{file_meta.path}` contains {file_meta.lines} lines of code, exceeding 1000 lines.",
                        file_path=file_meta.path,
                        recommendation="Refactor this file immediately into separate modules or services to reduce monolithic risk.",
                    )
                )

        # Rule: Missing README
        if not has_readme:
            findings.append(
                Finding(
                    rule_id="missing-readme",
                    severity=FindingSeverity.MEDIUM.value,
                    category="quality",
                    title="Missing README documentation",
                    description="No README file was detected in the repository.",
                    file_path=None,
                    recommendation="Add a README.md file documenting project purpose, setup, and usage.",
                )
            )

        # Rule: Missing tests
        source_files = [f for f in snapshot.files if f.language not in ("Unknown", "Markdown")]
        if len(source_files) > 0 and not has_tests:
            findings.append(
                Finding(
                    rule_id="missing-tests",
                    severity=FindingSeverity.MEDIUM.value,
                    category="quality",
                    title="Test coverage structure not detected",
                    description="No test directory or automated test files were detected in the repository.",
                    file_path=None,
                    recommendation="Add automated unit/integration tests to ensure code correctness and prevent regressions.",
                )
            )

        return findings
