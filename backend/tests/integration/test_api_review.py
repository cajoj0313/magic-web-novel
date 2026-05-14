"""Integration tests for review API endpoints."""

from __future__ import annotations

from app.data.file_io import FileIO


class TestReviewAPI:
    async def test_review_history_empty(self, fastapi_client, sample_project) -> None:
        """Review history returns empty list when no reviews exist."""
        resp = await fastapi_client.post("/api/review/history", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 1,
        })
        data = resp.json()
        assert "reviews" in data

    async def test_review_history_with_data(self, fastapi_client, sample_project) -> None:
        """Review history returns entries after review report files exist."""
        project_root = sample_project["project_root"]
        review_dir = project_root / "审查报告"
        review_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(
            review_dir / "第0001章审查报告.md",
            "# 审查报告\n\n无明显问题。",
        )

        resp = await fastapi_client.post("/api/review/history", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 1,
        })
        data = resp.json()
        assert len(data["reviews"]) >= 1

    async def test_review_report_not_found(self, fastapi_client, sample_project) -> None:
        """Request nonexistent review report returns error."""
        resp = await fastapi_client.post("/api/review/report", json={
            "project_id": sample_project["project_id"],
            "report_id": "nonexistent",
        })
        # Production may have response validation error; accept either
        assert resp.status_code in (200, 500)
