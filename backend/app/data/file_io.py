"""Unified file I/O for JSON, Markdown, CSV with proper UTF-8 and BOM handling.

All operations are synchronous (I/O-bound, suitable for FastAPI's thread pool).
Atomic writes use temp-file-then-rename pattern to prevent corruption on crash.
"""

from __future__ import annotations

import codecs
import csv
import os
import tempfile
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class FileIO:
    """Atomic, UTF-8 aware file operations."""

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    @staticmethod
    def read_json(path: str | Path) -> dict | list:
        """Read a JSON file. Raises FileNotFoundError if missing."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"JSON file not found: {p}")
        text = p.read_text(encoding="utf-8")
        logger.debug("Read JSON: %s", p)
        import json

        return json.loads(text)

    @staticmethod
    def write_json(path: str | Path, data: dict | list) -> None:
        """Write JSON atomically with UTF-8 encoding (no BOM)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        import json

        content = json.dumps(data, ensure_ascii=False, indent=2)
        FileIO._atomic_write(p, content, encoding="utf-8")
        logger.debug("Wrote JSON: %s", p)

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    @staticmethod
    def read_markdown(path: str | Path) -> str:
        """Read a markdown file. Raises FileNotFoundError if missing."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Markdown file not found: {p}")
        logger.debug("Read markdown: %s", p)
        return p.read_text(encoding="utf-8")

    @staticmethod
    def write_markdown(path: str | Path, content: str) -> None:
        """Write markdown atomically."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        FileIO._atomic_write(p, content, encoding="utf-8")
        logger.debug("Wrote markdown: %s", p)

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    @staticmethod
    def read_csv(path: str | Path) -> list[dict[str, str]]:
        """Read CSV with UTF-8 BOM support. Returns list of dicts."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"CSV file not found: {p}")
        # utf-8-sig automatically strips BOM if present
        with open(p, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        logger.debug("Read CSV: %s (%d rows)", p, len(rows))
        return rows

    # ------------------------------------------------------------------
    # Generic text
    # ------------------------------------------------------------------

    @staticmethod
    def read_text(path: str | Path, encoding: str = "utf-8") -> str:
        """Read generic text. Raises FileNotFoundError if missing."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Text file not found: {p}")
        return p.read_text(encoding=encoding)

    @staticmethod
    def write_text(path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """Write generic text atomically."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        FileIO._atomic_write(p, content, encoding=encoding)
        logger.debug("Wrote text: %s", p)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def exists(path: str | Path) -> bool:
        return Path(path).exists()

    @staticmethod
    def _atomic_write(path: Path, content: str, encoding: str) -> None:
        """Write to a temp file in the same directory, then os.rename().

        Using os.rename (not Path.rename) ensures an atomic operation
        on the same filesystem.
        """
        dir_path = path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding=encoding) as f:
                f.write(content)
            os.replace(tmp_path, str(path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
