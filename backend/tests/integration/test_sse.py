"""Integration tests for SSE event streaming."""

from __future__ import annotations

import asyncio
import json

from app.services.task_manager import task_manager


class TestSSE:
    async def test_sse_emits_events(self, fastapi_client) -> None:
        """SSE endpoint receives events when task_manager emits them."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-proj",
            chapter_num=1,
            total_steps=6,
        )

        async def emit_events():
            await asyncio.sleep(0.1)
            task_manager.emit(task_state.task_id, "step_start", {
                "task_id": task_state.task_id,
                "step_number": 1,
                "step_name": "上下文",
            })
            await asyncio.sleep(0.1)
            task_manager.emit(task_state.task_id, "step_complete", {
                "task_id": task_state.task_id,
                "step_number": 1,
                "step_name": "上下文",
                "preview": {"type": "context"},
            })
            await asyncio.sleep(0.1)
            task_manager.emit(task_state.task_id, "task_complete", {
                "task_id": task_state.task_id,
                "total_elapsed_ms": 500,
                "final_status": "completed",
            })

        # Start emitting events in background
        emit_task = asyncio.create_task(emit_events())

        # Connect to SSE
        resp = await fastapi_client.get(
            f"/api/events?task_id={task_state.task_id}",
            timeout=5.0,
        )

        body = resp.text
        assert "event:" in body
        assert "step_start" in body or "step_complete" in body or "task_complete" in body

        emit_task.cancel()
        try:
            await emit_task
        except asyncio.CancelledError:
            pass

    async def test_sse_task_not_found(self, fastapi_client) -> None:
        """SSE for nonexistent task returns 404."""
        resp = await fastapi_client.get("/api/events?task_id=nonexistent")
        assert resp.status_code == 404
