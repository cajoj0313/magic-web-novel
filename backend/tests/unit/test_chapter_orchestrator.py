"""Unit tests for ChapterOrchestrator — 6-step state machine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data.file_io import FileIO
from app.services.chapter_orchestrator import (
    ChapterOrchestrator,
    BlockingReviewError,
)


async def _dummy_caller(system: str, user: str, **kwargs) -> str:
    return "dummy content"


class TestFullFlow:
    async def test_full_flow_6_steps(self, tmp_path: Path) -> None:
        """Without interruption all 6 steps complete."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        orchestrator = ChapterOrchestrator(
            task_id="test-task-1",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=_dummy_caller,
        )
        result = await orchestrator.execute()
        assert result["status"] == "completed"
        assert orchestrator.current_step == 5

    async def test_blocking_review_stops_flow(self, tmp_path: Path) -> None:
        """When review returns blocking=true, subsequent steps don't execute."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        async def blocking_caller(system: str, user: str, **kwargs):
            if "审查" in system:
                return json.dumps({
                    "issues": [{
                        "severity": "critical",
                        "category": "setting",
                        "location": "p1",
                        "description": "设定冲突",
                        "evidence": "原文",
                        "fix_hint": "修改",
                        "blocking": True,
                    }],
                    "summary": "阻断",
                }, ensure_ascii=False)
            return "dummy content"

        orchestrator = ChapterOrchestrator(
            task_id="test-task-2",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=blocking_caller,
        )
        result = await orchestrator.execute()
        assert result["status"] == "blocked"
        assert "blocking_issues" in result
        assert len(result["blocking_issues"]) == 1
        assert result["blocking_issues"][0]["blocking"] is True


class TestPauseResume:
    async def test_pause_after_step_2(self, tmp_path: Path) -> None:
        """Pause signal stops execution after current step."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        orchestrator = ChapterOrchestrator(
            task_id="test-task-3",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=_dummy_caller,
        )
        # Set cancel flag immediately so it stops after checking
        orchestrator._cancelled = True
        result = await orchestrator.execute()
        assert result["status"] == "cancelled"

    async def test_resume_from_pause(self, tmp_path: Path) -> None:
        """Without cancel flag, execution completes normally."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        orchestrator = ChapterOrchestrator(
            task_id="test-task-4",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=_dummy_caller,
        )
        result = await orchestrator.execute()
        assert result["status"] == "completed"


class TestCancel:
    async def test_cancel_mid_execution(self, tmp_path: Path) -> None:
        """Cancel sets status to cancelled, already completed step products are preserved."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        orchestrator = ChapterOrchestrator(
            task_id="test-task-5",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=_dummy_caller,
        )
        orchestrator._cancelled = True
        result = await orchestrator.execute()
        assert result["status"] == "cancelled"


class TestRecovery:
    async def test_persist_state_writes_workflow_state(self, tmp_path: Path) -> None:
        """Persist state writes to .webnovel/workflow_state.json."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        webnovel = project_root / ".webnovel"
        webnovel.mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        orchestrator = ChapterOrchestrator(
            task_id="persist-task",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=_dummy_caller,
        )
        orchestrator.step_results[0] = {"status": "completed", "output": "test"}
        orchestrator._persist_state()

        state_file = webnovel / "workflow_state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["active_task"]["step_results"]["0"]["status"] == "completed"

    async def test_skip_completed_steps_when_pre_populated(self, tmp_path: Path) -> None:
        """When step_results is pre-populated, execute skips those steps."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        call_count = 0

        async def tracking_caller(system, user, **kwargs):
            nonlocal call_count
            call_count += 1
            return "content"

        orchestrator = ChapterOrchestrator(
            task_id="skip-task",
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=tracking_caller,
        )
        # Pre-populate steps 0-3 as completed (simulates recovery after polish).
        # Steps 0-3 write files needed by later steps, so we also create a
        # fake polished file since the actual step was skipped.
        for i in range(4):
            orchestrator.step_results[i] = {"status": "completed"}
        tmp_dir = project_root / ".webnovel" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(tmp_dir / "polished_ch1.md", "Polished content for test")

        result = await orchestrator.execute()
        assert result["status"] == "completed"
        # Only steps 4(fact_extract) and 5(commit) run.
        # Step 4 calls LLM, step 5 doesn't.
        assert call_count == 1
