"""Unit tests for FileIO data access layer."""

from __future__ import annotations

import json
from pathlib import Path

from app.data.file_io import FileIO


class TestReadUtf8WithBom:
    def test_read_utf8_with_bom(self, tmp_path: Path) -> None:
        """UTF-8 BOM CSV is read correctly with BOM stripped."""
        csv_path = tmp_path / "test.csv"
        # UTF-8 BOM + content
        content = "﻿id,name,genre\n1,Test,玄幻\n"
        csv_path.write_text(content, encoding="utf-8")
        result = FileIO.read_csv(csv_path)
        assert len(result) == 1
        assert result[0]["name"] == "Test"

    def test_read_csv_bom(self, tmp_path: Path) -> None:
        """BOM header is automatically stripped."""
        csv_path = tmp_path / "bom.csv"
        csv_path.write_text("﻿a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")
        rows = FileIO.read_csv(csv_path)
        assert len(rows) == 2
        assert rows[0]["a"] == "1"


class TestWriteJsonAtomic:
    def test_write_json_atomic(self, tmp_path: Path) -> None:
        """JSON write uses temp file + rename for atomic writes."""
        path = tmp_path / "data.json"
        data = {"key": "value", "num": 42}
        FileIO.write_json(path, data)
        assert path.exists()
        loaded = FileIO.read_json(path)
        assert loaded == data

    def test_write_json_overwrites(self, tmp_path: Path) -> None:
        """Second write replaces content atomically."""
        path = tmp_path / "data.json"
        FileIO.write_json(path, {"v": 1})
        FileIO.write_json(path, {"v": 2})
        assert FileIO.read_json(path) == {"v": 2}


class TestMarkdown:
    def test_read_write_markdown(self, tmp_path: Path) -> None:
        """Markdown read/write round-trip."""
        path = tmp_path / "test.md"
        content = "# Title\n\nSome content with 中文。\n"
        FileIO.write_markdown(path, content)
        assert FileIO.read_markdown(path) == content

    def test_write_markdown_creates_parent(self, tmp_path: Path) -> None:
        """Auto-creates parent directories for markdown files."""
        path = tmp_path / "deep" / "nested" / "file.md"
        FileIO.write_markdown(path, "content")
        assert path.exists()


class TestWriteText:
    def test_write_text_creates_parent(self, tmp_path: Path) -> None:
        """Auto-creates parent directories for text files."""
        path = tmp_path / "new_dir" / "file.txt"
        FileIO.write_text(path, "hello")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "hello"


class TestExists:
    def test_exists_true(self, tmp_path: Path) -> None:
        path = tmp_path / "exists.txt"
        path.write_text("yes")
        assert FileIO.exists(path)

    def test_exists_false(self, tmp_path: Path) -> None:
        assert not FileIO.exists(tmp_path / "nonexistent.txt")
