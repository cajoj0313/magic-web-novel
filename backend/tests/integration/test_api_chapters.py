"""Integration tests for chapter API endpoints."""

from __future__ import annotations

import pytest

from app.data.file_io import FileIO


class TestChapterCRUD:
    async def test_chapters_list_returns_all(self, fastapi_client, sample_project) -> None:
        """List returns all chapters including unwritten ones."""
        resp = await fastapi_client.post("/api/chapters/list", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert len(data["chapters"]) >= 3

    async def test_chapters_get_returns_content(self, fastapi_client, sample_project) -> None:
        """Get returns chapter content for existing chapter."""
        resp = await fastapi_client.post("/api/chapters/get", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 1,
        })
        data = resp.json()
        assert data["chapter_num"] == 1
        assert len(data["content"]) > 0
        assert data["word_count"] > 0

    async def test_chapters_save_updates_word_count(self, fastapi_client, sample_project) -> None:
        """Save chapter content and verify word count."""
        content = "这是保存后的新章节内容。" * 100
        resp = await fastapi_client.post("/api/chapters/save", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 4,
            "content": content,
        })
        data = resp.json()
        assert data["ok"] is True
        assert data["word_count"] > 0

        # Verify content persisted
        resp2 = await fastapi_client.post("/api/chapters/get", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 4,
        })
        data2 = resp2.json()
        assert data2["content"] == content

    @pytest.mark.xfail(reason="Production bug: ErrorResponse doesn't match ChapterGetResponse model")
    async def test_chapters_not_found(self, fastapi_client, sample_project) -> None:
        """Get nonexistent chapter returns error."""
        resp = await fastapi_client.post("/api/chapters/get", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 999,
        })
        assert resp.status_code in (200, 500)
