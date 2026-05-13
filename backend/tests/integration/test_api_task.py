"""Integration tests for task management API."""

from __future__ import annotations

from app.services.task_manager import task_manager


class TestTaskAPI:
    async def test_tasks_status_not_found(self, fastapi_client) -> None:
        """Status for nonexistent task returns error."""
        resp = await fastapi_client.post("/api/tasks/status", json={"task_id": "nonexistent"})
        data = resp.json()
        assert data.get("ok") is False

    async def test_tasks_pause_resume(self, fastapi_client) -> None:
        """Pause and resume a task that doesn't exist returns False."""
        # Pause on nonexistent task
        resp = await fastapi_client.post("/api/tasks/pause", json={"task_id": "no-task"})
        data = resp.json()
        assert data["ok"] is False

        # Resume on nonexistent task
        resp = await fastapi_client.post("/api/tasks/resume", json={"task_id": "no-task"})
        data = resp.json()
        assert data["ok"] is False

    async def test_tasks_cancel(self, fastapi_client) -> None:
        """Cancel a task."""
        resp = await fastapi_client.post("/api/tasks/cancel", json={"task_id": "no-task"})
        data = resp.json()
        assert data["ok"] is False

    async def test_tasks_status_after_create(self, fastapi_client) -> None:
        """Create a task via task_manager, then check status via API."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-proj",
            chapter_num=1,
            total_steps=6,
        )
        resp = await fastapi_client.post("/api/tasks/status", json={"task_id": task_state.task_id})
        data = resp.json()
        assert data["task_id"] == task_state.task_id
        assert data["status"] == "running"
