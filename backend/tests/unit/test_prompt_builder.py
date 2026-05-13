"""Unit tests for PromptBuilder."""

from __future__ import annotations

import json
from pathlib import Path

from app.data.file_io import FileIO
from app.services.prompt_builder import PromptBuilder, ANTI_AI_RULES, CORE_CONSTRAINTS


class TestBuildContextPrompt:
    def test_build_context_prompt_loads_contract(self) -> None:
        """System prompt contains chapter info and core constraints."""
        contract = {
            "chapter": {
                "chapter_directive": {"goal": "introduce protagonist"},
                "must_cover_nodes": [{"cbn": "主角|觉醒|力量"}],
                "forbidden_zones": ["不要揭示最终Boss"],
            },
            "dynamic_context": {"recent_events": "主角刚离开新手村"},
        }
        sys_prompt, user_prompt = PromptBuilder.build_context_prompt(
            chapter_num=5,
            contract_tree=contract,
            prev_chapter_summary="第4章主角打败了新手Boss",
            project_setting={"genre": "玄幻"},
        )
        assert "第 5 章" in sys_prompt
        assert CORE_CONSTRAINTS in sys_prompt
        assert "introduce protagonist" in user_prompt
        assert "上一章摘要" in user_prompt
        assert "主角刚离开新手村" in user_prompt

    def test_context_prompt_minimal_contract(self) -> None:
        """Works with empty contract tree."""
        sys_prompt, user_prompt = PromptBuilder.build_context_prompt(
            chapter_num=1,
            contract_tree={},
        )
        assert "第 1 章" in sys_prompt
        assert "硬性约束" in user_prompt


class TestBuildDraftPrompt:
    def test_build_draft_prompt_anti_ai_rules(self) -> None:
        """Draft prompt injects all 8 Anti-AI rules."""
        task_book = {
            "task_book": {
                "chapter_num": 3,
                "core_event": "主角突破",
                "cbn": "主角|突破|境界",
            }
        }
        sys_prompt, user_prompt = PromptBuilder.build_draft_prompt(task_book, genre="玄幻")
        assert ANTI_AI_RULES in sys_prompt
        assert CORE_CONSTRAINTS in sys_prompt
        assert "玄幻" in user_prompt
        assert "写作任务书" in user_prompt


class TestBuildReviewPrompt:
    def test_build_review_prompt_schema_v6(self) -> None:
        """Review prompt includes v6 schema JSON format requirements."""
        sys_prompt, user_prompt = PromptBuilder.build_review_prompt(
            chapter_content="这是正文内容",
            chapter_num=5,
            contract_tree={"chapter": {"chapter_directive": {}}},
            setting_context="力量体系：炼气→筑基→金丹",
        )
        assert "schema v6" in sys_prompt
        assert "severity" in sys_prompt
        assert "blocking" in sys_prompt
        assert "overall_score" in sys_prompt  # mentions no overall_score
        assert "第 5 章正文" in user_prompt
        assert "力量体系" in user_prompt


class TestBuildPolishPrompt:
    def test_build_polish_prompt_with_review_report(self) -> None:
        """Polish prompt includes non-blocking issues from review."""
        issues = [
            {"severity": "medium", "description": "某段落副词过多", "fix_hint": "用具体动作替代副词", "blocking": False},
            {"severity": "critical", "description": "设定冲突", "blocking": True},
        ]
        sys_prompt, user_prompt = PromptBuilder.build_polish_prompt(
            draft_content="草稿正文",
            review_issues=issues,
            genre="玄幻",
        )
        assert ANTI_AI_RULES in sys_prompt
        assert "修复" in user_prompt
        assert "副词过多" in user_prompt
        # Blocking issue should NOT be in the fix list
        assert "设定冲突" not in user_prompt


class TestBuildDataPrompt:
    def test_build_data_prompt_commit_schema(self) -> None:
        """Data prompt requires output matching commit JSON schema."""
        sys_prompt, user_prompt = PromptBuilder.build_data_prompt(
            chapter_content="正文内容",
            chapter_num=1,
            contract_tree={"chapter": {"chapter_directive": {}}},
            review_results={"issues": []},
        )
        assert "fulfillment_result" in sys_prompt
        assert "disambiguation_result" in sys_prompt
        assert "extraction_result" in sys_prompt
        assert "正文" in user_prompt


class TestLoadContractTree:
    def test_load_contract_tree_existing(self, tmp_path: Path) -> None:
        """Loads contract from .story-system/chapters/chapter_NNNN.review.json."""
        tree_dir = tmp_path / ".story-system" / "chapters"
        tree_dir.mkdir(parents=True)
        contract = {"chapter_num": 1}
        FileIO.write_json(tree_dir / "chapter_0005.review.json", contract)
        result = PromptBuilder.load_contract_tree(tmp_path, 5)
        assert result == {"chapter_num": 1}

    def test_load_contract_tree_missing(self, tmp_path: Path) -> None:
        """Returns None when contract file doesn't exist."""
        result = PromptBuilder.load_contract_tree(tmp_path, 99)
        assert result is None

    def test_load_contract_tree_no_story_system(self, tmp_path: Path) -> None:
        """Returns None when .story-system directory doesn't exist."""
        result = PromptBuilder.load_contract_tree(tmp_path, 1)
        assert result is None


class TestLoadPrevSummary:
    def test_load_prev_summary_existing(self, tmp_path: Path) -> None:
        """Loads summary from .webnovel/summaries/chNNNN.md."""
        summary_dir = tmp_path / ".webnovel" / "summaries"
        summary_dir.mkdir(parents=True)
        FileIO.write_markdown(summary_dir / "ch0004.md", "Chapter 4 summary")
        result = PromptBuilder.load_prev_summary(tmp_path, 5)
        assert result == "Chapter 4 summary"

    def test_load_prev_summary_missing(self, tmp_path: Path) -> None:
        """Returns None when summary doesn't exist."""
        result = PromptBuilder.load_prev_summary(tmp_path, 1)
        assert result is None


class TestLoadProjectSetting:
    def test_load_project_setting_existing(self, tmp_path: Path) -> None:
        """Loads state.json as setting."""
        webnovel = tmp_path / ".webnovel"
        webnovel.mkdir()
        FileIO.write_json(webnovel / "state.json", {"genre": "玄幻", "word_count": 5000})
        result = PromptBuilder.load_project_setting(tmp_path)
        assert result["genre"] == "玄幻"

    def test_load_project_setting_missing(self, tmp_path: Path) -> None:
        """Returns empty dict when state.json doesn't exist."""
        result = PromptBuilder.load_project_setting(tmp_path)
        assert result == {}
