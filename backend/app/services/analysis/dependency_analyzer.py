"""Dependency Analyzer module to inspect package manifest presence and dependencies."""
from __future__ import annotations

import json
import re
from typing import Any

from app.services.analysis.types import Finding, FindingSeverity
from app.services.code_scanner import NormalizedRepositoryStructure

KNOWN_MANIFESTS = {
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "setup.py": "Python",
    "package.json": "Node.js / JavaScript",
    "package-lock.json": "Node.js",
    "yarn.lock": "Node.js",
    "pnpm-lock.yaml": "Node.js",
    "composer.json": "PHP",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "build.gradle.kts": "Kotlin (Gradle)",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
}


class DependencyAnalyzer:
    """Analyzer untuk mendeteksi file dependensi project."""

    def analyze(self, snapshot: NormalizedRepositoryStructure) -> tuple[list[Finding], dict[str, Any]]:
        """Menganalisis file dependensi di repository.

        Returns:
            Tuple of (findings, dependency_summary_dict)
        """
        findings: list[Finding] = []
        detected_manifests: list[str] = []
        detected_dependencies_count = 0

        # Cari manifest file dari snapshot.files
        for file_meta in snapshot.files:
            filename = file_meta.path.split("/")[-1]
            if filename in KNOWN_MANIFESTS:
                if filename not in detected_manifests:
                    detected_manifests.append(filename)

                # Coba ekstrak perkiraan jumlah dependensi jika konten tersedia
                if file_meta.content:
                    if filename == "requirements.txt":
                        lines = [
                            l.strip() for l in file_meta.content.splitlines()
                            if l.strip() and not l.strip().startswith("#")
                        ]
                        detected_dependencies_count += len(lines)
                    elif filename == "package.json":
                        try:
                            data = json.loads(file_meta.content)
                            deps = data.get("dependencies", {})
                            dev_deps = data.get("devDependencies", {})
                            detected_dependencies_count += len(deps) + len(dev_deps)
                        except Exception:
                            pass
                    elif filename == "go.mod":
                        requires = re.findall(r"require\s*\((.*?)\)", file_meta.content, re.DOTALL)
                        if requires:
                            lines = [l for l in requires[0].splitlines() if l.strip()]
                            detected_dependencies_count += len(lines)

        # Jika ada source files tapi tidak ada manifest dependensi yang terdeteksi
        source_files = [f for f in snapshot.files if f.language not in ("Unknown", "Markdown")]
        if len(source_files) > 0 and not detected_manifests:
            findings.append(
                Finding(
                    rule_id="missing-dependency-manifest",
                    severity=FindingSeverity.MEDIUM.value,
                    category="dependency",
                    title="No dependency manifest detected",
                    description="No standard package manifest file (e.g., requirements.txt, package.json, go.mod) was found.",
                    file_path=None,
                    recommendation="Add a standard dependency manifest file to specify explicit project dependencies.",
                )
            )

        summary = {
            "has_dependency_manifest": len(detected_manifests) > 0,
            "manifest_files": detected_manifests,
            "estimated_dependency_count": detected_dependencies_count,
        }

        return findings, summary
