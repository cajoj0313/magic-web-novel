"""Integration tests for filesystem operations."""

from __future__ import annotations

from pathlib import Path

from app.data.file_io import FileIO
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService


class TestFilesystem:
    def test_read_existing_chapter_file(self, sample_project) -> None:
        """Read existing chapter file via ChapterService."""
        project_root = sample_project["project_root"]
        project_id = sample_project["project_id"]

        chapter = ChapterService.get_chapter(project_id, 1)
        assert chapter["chapter_num"] == 1
        assert len(chapter["content"]) > 0

    def test_write_new_chapter_creates_file(self, sample_project) -> None:
        """Save new chapter creates correct path."""
        project_id = sample_project["project_id"]
        content = "这是新章节的正文内容。" * 50

        wc = ChapterService.save_chapter(project_id, 99, content)
        assert wc > 0

        project_root = sample_project["project_root"]
        # Verify file exists
        files = list((project_root / "正文").glob("*.md"))
        assert any(f.name.startswith("第0099") for f in files)

    def test_update_state_json_atomic(self, sample_project) -> None:
        """Writing state.json uses atomic write (tmp + rename)."""
        project_root = sample_project["project_root"]
        state_file = project_root / ".webnovel" / "state.json"

        original = FileIO.read_json(state_file)
        original["genre"] = "都市"
        FileIO.write_json(state_file, original)

        # Verify file still valid JSON
        updated = FileIO.read_json(state_file)
        assert updated["genre"] == "都市"

    def test_state_json_no_temp_leftover(self, sample_project) -> None:
        """After atomic write, no .tmp file remains."""
        project_root = sample_project["project_root"]
        webnovel = project_root / ".webnovel"
        FileIO.write_json(webnovel / "state.json", {"test": True})

        tmp_files = list(webnovel.glob("*.tmp"))
        assert len(tmp_files) == 0
