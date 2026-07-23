"""Repository Structure Analyzer module."""
from __future__ import annotations

import os
from typing import Any

from app.services.analysis.types import Finding, FindingSeverity
from app.services.code_scanner import NormalizedRepositoryStructure


class StructureAnalyzer:
    """Analyzer untuk memeriksa struktur direktori, kedalaman folder, dan organisasi project."""

    def analyze(self, snapshot: NormalizedRepositoryStructure) -> list[Finding]:
        """Menganalisis struktur direktori dan menghasilkan list of Finding."""
        findings: list[Finding] = []

        if not snapshot.files:
            return findings

        directories: set[str] = set()
        root_files: list[str] = []
        max_depth = 0

        for file_meta in snapshot.files:
            path = file_meta.path.strip("/")
            parts = path.split("/")

            if len(parts) == 1:
                root_files.append(path)
            else:
                dir_path = "/".join(parts[:-1])
                directories.add(dir_path)
                depth = len(parts) - 1
                if depth > max_depth:
                    max_depth = depth

        # 1. Excessive root files rule (> 10 files directly in root)
        if len(root_files) > 10:
            findings.append(
                Finding(
                    rule_id="excessive-root-files",
                    severity=FindingSeverity.LOW.value,
                    category="structure",
                    title="Excessive files in root directory",
                    description=f"Found {len(root_files)} files in the root directory. Placing too many files in root can impair readability.",
                    file_path=None,
                    recommendation="Organize root files into subdirectories like src/, app/, docs/, or config/.",
                )
            )

        # 2. Excessive directory depth rule (depth > 5)
        if max_depth > 5:
            findings.append(
                Finding(
                    rule_id="excessive-directory-depth",
                    severity=FindingSeverity.MEDIUM.value,
                    category="structure",
                    title="Excessive directory nesting depth",
                    description=f"Maximum directory depth reached {max_depth} levels. Deeply nested paths increase cognitive complexity.",
                    file_path=None,
                    recommendation="Consider flattening deeply nested directory hierarchies.",
                )
            )

        # 3. Unorganized source structure rule (> 5 source files and > 60% of source files in root)
        source_files = [f for f in snapshot.files if f.language != "Unknown" and f.language != "Markdown"]
        if len(source_files) >= 5:
            source_root_files = [f for f in source_files if "/" not in f.path]
            ratio = len(source_root_files) / len(source_files)
            if ratio > 0.6:
                findings.append(
                    Finding(
                        rule_id="unorganized-source-structure",
                        severity=FindingSeverity.LOW.value,
                        category="structure",
                        title="Unorganized source code placement",
                        description=f"{len(source_root_files)} out of {len(source_files)} source files are located directly in the root directory.",
                        file_path=None,
                        recommendation="Move application source code into dedicated packages or directories (e.g., src/ or app/).",
                    )
                )

        return findings
