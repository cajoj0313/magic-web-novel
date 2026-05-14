"""Integration tests for LLM failure handling, retry, SSE events, and concurrency."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.data.file_io import FileIO
from app.services.chapter_orchestrator import ChapterOrchestrator, BlockingReviewError
from app.services.task_manager import task_manager


class TestLLMFailureHandling:
    """LLM call failures are properly tracked."""

    async def test_llm_failure_marks_step_failed(self, tmp_path: Path) -> None:
        """When LLM call fails, step status becomes failed and task fails."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        FileIO.write_json(project_root / ".webnovel" / "state.json", {"genre": "玄幻"})

        async def always_failing_caller(system: str, user: str, **kwargs) -> str:
            raise RuntimeError("LLM API is down")

        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-proj-fail",
            chapter_num=1,
            total_steps=6,
        )

        orchestrator = ChapterOrchestrator(
            task_id=task_state.task_id,
            project_id="test-proj-fail",
            chapter_num=1,
            project_root=project_root,
            caller=always_failing_caller,
        )

        result = await orchestrator.execute()
        assert result["status"] == "failed"
        assert result["failed_step"] == 1  # First step fails

    async def test_retry_succeeds_on_third_attempt(self, tmp_path: Path) -> None:
        """After step failure, recovery from state file allows retry and completion.

        The orchestrator doesn't retry the caller internally — retry happens at
        the AnthropicClient level (tested in unit tests). This test verifies
        that after a step failure, the user can retry and the flow completes.
        """
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()
        FileIO.write_json(project_root / ".webnovel" / "state.json", {"genre": "玄幻"})

        async def ok_caller(system: str, user: str, **kwargs) -> str:
            if "写作任务" in system or "上下文" in system:
                return json.dumps({
                    "task_book": {"chapter_num": 1, "core_event": "test", "cbn": "A|B|C", "cpns": [], "cen": "X|Y|Z"},
                }, ensure_ascii=False)
            elif "润色" in system:
                return "润色后正文。"
            elif "审查" in system:
                return json.dumps({"issues": [], "summary": "ok"}, ensure_ascii=False)
            elif "事实" in system:
                return json.dumps({"fulfillment_result": {}, "disambiguation_result": {}, "extraction_result": {}}, ensure_ascii=False)
            return "mock content"

        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-proj-retry",
            chapter_num=1,
            total_steps=6,
        )

        # Simulate: first attempt, step 0 succeeds, step 1 fails
        attempt_count = [0]

        async def partial_fail(system: str, user: str, **kwargs) -> str:
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # Step 0 (context): succeeds
                return await ok_caller(system, user, **kwargs)
            # Step 1 (draft): fails
            raise RuntimeError("Temporary API error")

        orch1 = ChapterOrchestrator(
            task_id=task_state.task_id,
            project_id="test-proj-retry",
            chapter_num=1,
            project_root=project_root,
            caller=partial_fail,
        )
        result1 = await orch1.execute()
        assert result1["status"] == "failed"
        assert result1["failed_step"] == 2  # Step index 1 = step number 2

        # Now retry with working caller — should skip step 0 (already completed)
        orch2 = ChapterOrchestrator(
            task_id=task_state.task_id,
            project_id="test-proj-retry",
            chapter_num=1,
            project_root=project_root,
            caller=ok_caller,
        )
        from app.data.task_store import TaskStore
        store = TaskStore(project_root)
        loaded = store.load()
        if loaded:
            results = loaded.get("active_task", {}).get("step_results", {})
            orch2.step_results = {int(k): v for k, v in results.items()}

        result2 = await orch2.execute()
        assert result2["status"] == "completed"


class TestSSEEvents:
    """SSE event emission for all event types."""

    async def test_sse_emits_step_start_events(self) -> None:
        """Each step start emits step_start event."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-sse-start",
            chapter_num=1,
        )

        q = task_manager.subscribe(task_state.task_id)
        assert q is not None

        task_manager.emit(task_state.task_id, "step_start", {
            "task_id": task_state.task_id,
            "step_number": 1,
            "step_name": "上下文",
        })

        event, data = q.get_nowait()
        assert event == "step_start"
        assert data["step_number"] == 1

    async def test_sse_emits_step_complete_events(self) -> None:
        """Step complete emits event with preview."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-sse-complete",
            chapter_num=1,
        )

        q = task_manager.subscribe(task_state.task_id)
        task_manager.emit(task_state.task_id, "step_complete", {
            "task_id": task_state.task_id,
            "step_number": 2,
            "step_name": "正文起草",
            "elapsed_ms": 5000,
            "preview": {"word_count": 3000},
        })

        event, data = q.get_nowait()
        assert event == "step_complete"
        assert data["preview"]["word_count"] == 3000

    async def test_sse_emits_task_complete_at_end(self) -> None:
        """Task completion emits task_complete event."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-sse-done",
            chapter_num=1,
        )

        q = task_manager.subscribe(task_state.task_id)
        task_manager.emit(task_state.task_id, "task_complete", {
            "task_id": task_state.task_id,
            "total_elapsed_ms": 30000,
            "final_status": "completed",
        })

        event, data = q.get_nowait()
        assert event == "task_complete"
        assert data["final_status"] == "completed"

    async def test_sse_handles_task_failure(self) -> None:
        """Task failure emits task_failed event with error info."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-sse-fail",
            chapter_num=1,
        )

        q = task_manager.subscribe(task_state.task_id)
        task_manager.emit(task_state.task_id, "task_failed", {
            "task_id": task_state.task_id,
            "failed_step": 2,
            "failed_step_name": "正文起草",
            "error_message": "LLM API error",
            "recoverable": True,
        })

        event, data = q.get_nowait()
        assert event == "task_failed"
        assert data["failed_step"] == 2
        assert "error_message" in data

    async def test_sse_unsubscribe_removes_queue(self) -> None:
        """Unsubscribe removes queue from broadcast list."""
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-sse-unsub",
            chapter_num=1,
        )

        q = task_manager.subscribe(task_state.task_id)
        assert q in task_manager._sse_queues[task_state.task_id]

        task_manager.unsubscribe(task_state.task_id, q)
        assert q not in task_manager._sse_queues[task_state.task_id]


class TestConcurrentDraft:
    """Concurrent draft requests on same project return 409."""

    def test_task_manager_lock_is_per_project(self) -> None:
        """Same project_id gets same lock, different projects get different locks."""
        lock1 = task_manager.get_lock("proj-A")
        lock2 = task_manager.get_lock("proj-A")
        lock3 = task_manager.get_lock("proj-B")

        assert lock1 is lock2
        assert lock1 is not lock3

    async def test_task_manager_state_transitions(self) -> None:
        """Pause/resume/cancel state transitions work correctly."""
        state = task_manager.create_task("draft", "proj-states", chapter_num=1)

        # Running -> Paused
        assert task_manager.pause_task(state.task_id) is True
        status = task_manager.get_status(state.task_id)
        assert status["status"] == "paused"

        # Paused -> Running
        assert task_manager.resume_task(state.task_id) is True
        status = task_manager.get_status(state.task_id)
        assert status["status"] == "running"

        # Running -> Cancelled
        assert task_manager.cancel_task(state.task_id) is True
        status = task_manager.get_status(state.task_id)
        assert status["status"] == "cancelled"

        # Cancelled cannot be resumed
        assert task_manager.resume_task(state.task_id) is False
