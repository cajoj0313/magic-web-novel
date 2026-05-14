"""Integration tests for chapter draft/review flow with mock LLM."""

from __future__ import annotations

from unittest.mock import patch

from app.data.file_io import FileIO
from app.services.chapter_orchestrator import ChapterOrchestrator
from app.services.task_manager import task_manager


class TestMockLLMFlow:
    async def test_draft_flow_with_mock_llm(self, tmp_path) -> None:
        """Full 6-step draft flow with mock LLM completes successfully."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel").mkdir()
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()
        FileIO.write_json(project_root / ".webnovel" / "state.json", {"genre": "玄幻"})

        # Register task
        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-proj",
            chapter_num=1,
            total_steps=6,
        )

        orchestrator = ChapterOrchestrator(
            task_id=task_state.task_id,
            project_id="test-proj",
            chapter_num=1,
            project_root=project_root,
            caller=_mock_caller,
        )
        result = await orchestrator.execute()
        assert result["status"] == "completed"
        assert result["chapter_num"] == 1

    async def test_review_flow_with_mock_llm(self, sample_project) -> None:
        """Review flow with mock LLM produces review report."""
        project_root = sample_project["project_root"]
        project_id = sample_project["project_id"]

        # Create chapter file in the 正文 directory
        content_dir = project_root / "正文"
        content_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(
            content_dir / "第0001章-测试章节.md",
            "这是第1章的正文内容。" * 50,
        )

        from app.services.review_service import ReviewService

        task_state = task_manager.create_task(
            task_type="review",
            project_id=project_id,
            chapter_num=1,
            total_steps=3,
        )

        service = ReviewService(
            task_id=task_state.task_id,
            project_id=project_id,
            chapter_num=1,
            project_root=project_root,
            caller=_mock_caller,
        )
        result = await service.execute()
        assert result["status"] == "completed"

    async def test_blocking_review_stops_flow(self, tmp_path) -> None:
        """Review with blocking issues stops the draft flow."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".webnovel" / "tmp").mkdir(parents=True)
        (project_root / ".story-system" / "chapters").mkdir(parents=True)
        (project_root / "正文").mkdir()

        # Create draft so steps 1-2 can complete
        FileIO.write_markdown(
            project_root / ".webnovel" / "tmp" / "draft_ch1.md",
            "Draft content for blocking test.",
        )

        import json

        async def blocking_caller(system: str, user: str, **kwargs) -> str:
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
            return "mock content"

        task_state = task_manager.create_task(
            task_type="draft",
            project_id="test-proj",
            chapter_num=2,
            total_steps=6,
        )

        orchestrator = ChapterOrchestrator(
            task_id=task_state.task_id,
            project_id="test-proj",
            chapter_num=2,
            project_root=project_root,
            caller=blocking_caller,
        )
        result = await orchestrator.execute()
        assert result["status"] == "blocked"
        assert len(result.get("blocking_issues", [])) > 0


async def _mock_caller(system: str, user: str, **kwargs) -> str:
    """Mock LLM caller that returns predefined responses based on prompt content."""
    if "写作任务" in system or "上下文" in system:
        import json
        return json.dumps({
            "task_book": {
                "chapter_num": 1,
                "core_event": "主角觉醒",
                "cbn": "主角 | 觉醒 | 力量",
                "cpns": ["主角 | 练习 | 新技能"],
                "cen": "主角 | 发现 | 秘密",
            },
        }, ensure_ascii=False)
    elif "润色" in system:
        return "这是润色后的正文内容。主角伫立在苍茫的山巅，感受着体内奔涌的力量。"
    elif "审查" in system:
        import json
        return json.dumps({
            "issues": [],
            "summary": "章节质量良好，无明显问题。",
        }, ensure_ascii=False)
    elif "事实" in system:
        import json
        return json.dumps({
            "fulfillment_result": {},
            "disambiguation_result": {},
            "extraction_result": {"summary": "主角觉醒了力量"},
        }, ensure_ascii=False)
    elif "草稿" in system or "作家" in system:
        return "这是起草的正文内容。主角站在山顶上，感受着体内涌动的力量。风吹过他的脸庞。他知道自己踏上了一条不归路。"
    return "mock response"
