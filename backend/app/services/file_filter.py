"""Mekanisme filtering file untuk menyaring source code dan file konfigurasi yang relevan."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class FileFilterConfig:
    """Konfigurasi aturan filtering file."""

    # Ekstensi yang diproses
    allowed_extensions: set[str] = field(
        default_factory=lambda: {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".php",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".cs",
            ".sql",
            ".html",
            ".css",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".md",
        }
    )

    # Direktori yang harus diabaikan
    ignored_directories: set[str] = field(
        default_factory=lambda: {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            "coverage",
            ".idea",
            ".vscode",
            ".next",
            ".pytest_cache",
        }
    )

    # Ekstensi file yang selalu diabaikan (binary, image, video, audio, archive)
    ignored_extensions: set[str] = field(
        default_factory=lambda: {
            # Binary & Executable
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".o",
            ".obj",
            ".pyc",
            ".pyo",
            ".class",
            ".db",
            ".sqlite",
            # Gambar
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".svg",
            ".webp",
            ".bmp",
            ".tiff",
            # Video & Audio
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".mp3",
            ".wav",
            ".ogg",
            # Arsip
            ".zip",
            ".tar",
            ".gz",
            ".7z",
            ".rar",
            ".bz2",
            # Source maps
            ".map",
        }
    )

    # Nama file tertentu yang diabaikan (lockfiles, generated)
    ignored_filenames: set[str] = field(
        default_factory=lambda: {
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "Cargo.lock",
            "poetry.lock",
            "pipfile.lock",
        }
    )

    # Maksimal ukuran file dalam bytes yang diproses untuk content scanning (default: 500 KB)
    max_file_size_bytes: int = 500 * 1024


class FileFilter:
    """Evaluator untuk menentukan apakah sebuah file/directory harus diproses."""

    def __init__(self, config: FileFilterConfig | None = None) -> None:
        self.config = config or FileFilterConfig()

    def should_process(
        self,
        path: str,
        size: int | None = None,
        is_dir: bool = False,
    ) -> bool:
        """Menentukan apakah item di path harus diproses.

        Args:
            path: Relative path file di repository.
            size: Ukuran file dalam bytes (opsional).
            is_dir: True jika item merupakan direktori.

        Returns:
            True jika file relevan untuk di-scan, False jika harus diabaikan.
        """
        if not path or path == ".":
            return False

        parts = path.strip("/").split("/")

        # Check direktori terlarang di komponen path mana pun
        for part in parts:
            if part in self.config.ignored_directories:
                return False

        if is_dir:
            return False

        filename = parts[-1]
        filename_lower = filename.lower()

        # Check nama file yang diabaikan (mis. lockfiles)
        if filename_lower in self.config.ignored_filenames:
            return False

        # Check file minified (mis. jquery.min.js, style.min.css)
        if filename_lower.endswith(".min.js") or filename_lower.endswith(".min.css"):
            return False

        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        # Check ekstensi terlarang (binary, media, dll)
        if ext_lower in self.config.ignored_extensions:
            return False

        # Check ukuran file jika tersedia
        if size is not None and size > self.config.max_file_size_bytes:
            return False

        # Terima manifest file khusus (mis. requirements.txt, Dockerfile, Pipfile)
        if filename_lower in {"requirements.txt", "dockerfile", "pipfile", "makefile"}:
            return True

        # Hanya terima file dengan ekstensi yang diizinkan
        return ext_lower in self.config.allowed_extensions
