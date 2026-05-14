"""Unit tests for PlanOrchestrator — 9-step volume planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.data.file_io import FileIO


class TestFullFlow:
    async def test_full_flow_9_steps(self, tmp_path: Path) -> None:
        """All 9 steps complete without errors."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "volumes").mkdir(parents=True)
        (project_root / "大纲").mkdir()

        # Minimal master outline for step 1
        FileIO.write_markdown(project_root / "大纲" / "总纲.md", "# 总纲\n这是一个测试总纲。")
        FileIO.write_json(project_root / ".webnovel" / "state.json", {"genre": "玄幻"})

        # Volume contract for step 2
        FileIO.write_json(
            project_root / ".story-system" / "volumes" / "volume_001.json",
            {"volume_id": 1, "goal": "introduce world"},
        )

        async def dummy_caller(system, user, **kwargs):
            if "节拍表" in system:
                return "# 节拍表\n节拍1：主角出发"
            elif "时间线" in system:
                return "# 时间线\nDay 1: 出发"
            elif "逐章章纲" in system:
                return "# 章纲\n第1章：出发"
            elif "连续性" in system:
                return '{"continuity_issues": []}'
            elif "验证" in system:
                return '{"conflicts": []}'
            elif "设定管理" in system:
                return '{"new_settings": []}'
            return "dummy"

        from app.services.plan_orchestrator import PlanOrchestrator
        orchestrator = PlanOrchestrator(
            task_id="plan-task-1",
            project_id="test-proj",
            volume_id=1,
            project_root=project_root,
            caller=dummy_caller,
        )
        result = await orchestrator.execute()
        assert result["status"] == "completed"
        assert result["volume_id"] == 1


class TestLoadContext:
    async def test_load_context_loads_master_outline(self, tmp_path: Path) -> None:
        """Step 1 loads master outline and state.json into context."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        FileIO.write_markdown(project_root / "大纲" / "总纲.md", "# 总纲\n测试内容。")
        FileIO.write_json(project_root / ".webnovel" / "state.json", {"genre": "玄幻"})

        from app.services.plan_orchestrator import PlanOrchestrator
        orchestrator = PlanOrchestrator(
            task_id="ctx-task",
            project_id="test-proj",
            volume_id=1,
            project_root=project_root,
            caller=lambda system, user, **kwargs: "ok",
        )
        result = await orchestrator._step_load_context()
        assert "已加载总纲" in result["output"]
        assert orchestrator.context.get("master_outline") == "# 总纲\n测试内容。"

    async def test_load_context_no_outline(self, tmp_path: Path) -> None:
        """Handles missing master outline gracefully."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()

        from app.services.plan_orchestrator import PlanOrchestrator
        orchestrator = PlanOrchestrator(
            task_id="ctx-task-2",
            project_id="test-proj",
            volume_id=1,
            project_root=project_root,
            caller=lambda system, user, **kwargs: "ok",
        )
        result = await orchestrator._step_load_context()
        assert orchestrator.context.get("master_outline") == ""


class TestContractMissing:
    async def test_contract_missing(self, tmp_path: Path) -> None:
        """Does not error when volume contract file doesn't exist."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        from app.services.plan_orchestrator import PlanOrchestrator
        orchestrator = PlanOrchestrator(
            task_id="contract-task",
            project_id="test-proj",
            volume_id=1,
            project_root=project_root,
            caller=lambda system, user, **kwargs: "ok",
        )
        result = await orchestrator._step_refresh_contract()
        assert "不存在" in result["output"]
        assert orchestrator.context.get("volume_contract") == {}
