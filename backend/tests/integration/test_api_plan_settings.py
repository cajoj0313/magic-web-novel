"""Integration tests for plan and settings API endpoints."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.data.file_io import FileIO


class TestPlanAPI:
    async def test_master_outline_get_empty(self, fastapi_client, sample_project) -> None:
        """Get master outline returns empty when file doesn't exist."""
        resp = await fastapi_client.post("/api/plan/master-outline/get", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert data["content"] == ""
        assert data["last_updated"] is None

    async def test_master_outline_get_existing(self, fastapi_client, sample_project) -> None:
        """Get master outline returns file content."""
        root = sample_project["project_root"]
        outline_dir = root / "大纲"
        outline_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(outline_dir / "总纲.md", "# 总纲\n\n这是一个测试总纲。")

        resp = await fastapi_client.post("/api/plan/master-outline/get", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert "总纲" in data["content"]
        assert data["last_updated"] is not None

    async def test_master_outline_save(self, fastapi_client, sample_project) -> None:
        """Save master outline writes file."""
        root = sample_project["project_root"]
        resp = await fastapi_client.post("/api/plan/master-outline/save", json={
            "project_id": sample_project["project_id"],
            "content": "# 新总纲\n\n更新内容。",
        })
        assert resp.json()["ok"] is True
        assert (root / "大纲" / "总纲.md").exists()

    async def test_master_outline_get_not_found(self, fastapi_client) -> None:
        """Get master outline for nonexistent project returns error."""
        resp = await fastapi_client.post("/api/plan/master-outline/get", json={
            "project_id": "nonexistent-id",
        })
        data = resp.json()
        assert "error_code" in data

    async def test_volume_get_empty(self, fastapi_client, sample_project) -> None:
        """Get volume returns empty strings when no volume files exist."""
        resp = await fastapi_client.post("/api/plan/volume/get", json={
            "project_id": sample_project["project_id"],
            "volume_id": 1,
        })
        data = resp.json()
        assert data["beat_sheet"] == ""
        assert data["timeline"] == ""

    async def test_volume_get_with_files(self, fastapi_client, sample_project) -> None:
        """Get volume returns content from matching volume files."""
        root = sample_project["project_root"]
        outline_dir = root / "大纲"
        outline_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(outline_dir / "第1卷节拍表.md", "# 节拍表")
        FileIO.write_markdown(outline_dir / "第1卷时间线.md", "# 时间线")

        resp = await fastapi_client.post("/api/plan/volume/get", json={
            "project_id": sample_project["project_id"],
            "volume_id": 1,
        })
        data = resp.json()
        assert "节拍表" in data["beat_sheet"]
        assert "时间线" in data["timeline"]

    async def test_volume_start_no_llm_config(self, fastapi_client, sample_project) -> None:
        """Volume start returns error when no default LLM config."""
        resp = await fastapi_client.post("/api/plan/volume/start", json={
            "project_id": sample_project["project_id"],
            "volume_id": 1,
        })
        data = resp.json()
        assert "error_code" in data

    async def test_volume_start_with_llm_config(self, fastapi_client, sample_project) -> None:
        """Volume start creates task and returns task_id."""
        # Set up LLM config
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.app_secret_key = ""
            mock_settings.app_data_dir = str(sample_project["project_root"])
            with patch("app.core.config.ensure_app_data_dir") as mock_ensure:
                mock_ensure.return_value = sample_project["project_root"]
                from app.services.llm_service import LLMService
                LLMService.add_config(
                    name="Test",
                    provider="anthropic",
                    model="claude-test",
                    url="http://test",
                    api_key="sk-test",
                )

                resp = await fastapi_client.post("/api/plan/volume/start", json={
                    "project_id": sample_project["project_id"],
                    "volume_id": 1,
                })
                data = resp.json()
                assert "task_id" in data


class TestSettingAPI:
    async def test_setting_get_empty(self, fastapi_client, sample_project) -> None:
        """Get setting returns empty when file doesn't exist."""
        resp = await fastapi_client.post("/api/settings/get", json={
            "project_id": sample_project["project_id"],
            "setting_type": "world",
        })
        data = resp.json()
        assert data["content"] == ""
        assert data["last_updated"] is None

    async def test_setting_get_existing(self, fastapi_client, sample_project) -> None:
        """Get setting returns file content."""
        root = sample_project["project_root"]
        setting_dir = root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(setting_dir / "世界观.md", "# 世界观\n\n测试世界。")

        resp = await fastapi_client.post("/api/settings/get", json={
            "project_id": sample_project["project_id"],
            "setting_type": "world",
        })
        data = resp.json()
        assert "世界观" in data["content"]
        assert data["last_updated"] is not None

    async def test_setting_save(self, fastapi_client, sample_project) -> None:
        """Save setting writes file."""
        root = sample_project["project_root"]
        resp = await fastapi_client.post("/api/settings/save", json={
            "project_id": sample_project["project_id"],
            "setting_type": "world",
            "content": "# 新世界\n\n新的世界观内容。",
        })
        assert resp.json()["ok"] is True
        assert (root / "设定集" / "世界观.md").exists()

    async def test_setting_get_custom_type(self, fastapi_client, sample_project) -> None:
        """Get setting with custom type falls back to 设定集/{type}.md."""
        root = sample_project["project_root"]
        setting_dir = root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(setting_dir / "custom-setting.md", "# 自定义设定")

        resp = await fastapi_client.post("/api/settings/get", json={
            "project_id": sample_project["project_id"],
            "setting_type": "custom-setting",
        })
        data = resp.json()
        assert "自定义设定" in data["content"]

    async def test_setting_save_custom_type(self, fastapi_client, sample_project) -> None:
        """Save setting with custom type creates fallback path."""
        root = sample_project["project_root"]
        resp = await fastapi_client.post("/api/settings/save", json={
            "project_id": sample_project["project_id"],
            "setting_type": "custom-type",
            "content": "# 自定义类型",
        })
        assert resp.json()["ok"] is True
        assert (root / "设定集" / "custom-type.md").exists()


class TestQueryAPI:
    async def test_query_power_system_missing(self, fastapi_client, sample_project) -> None:
        """Query power system returns fallback when file missing."""
        resp = await fastapi_client.post("/api/query/power-system", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert "尚未创建" in data["content"]

    async def test_query_power_system_existing(self, fastapi_client, sample_project) -> None:
        """Query power system returns file content."""
        root = sample_project["project_root"]
        setting_dir = root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(setting_dir / "力量体系.md", "# 力量体系\n\n练气、筑基、金丹。")

        resp = await fastapi_client.post("/api/query/power-system", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert "练气" in data["content"]

    async def test_query_golden_finger_missing(self, fastapi_client, sample_project) -> None:
        """Query golden finger returns fallback."""
        resp = await fastapi_client.post("/api/query/golden-finger", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert "尚未创建" in data["golden_finger"]["content"]

    async def test_query_golden_finger_existing(self, fastapi_client, sample_project) -> None:
        """Query golden finger returns file content."""
        root = sample_project["project_root"]
        setting_dir = root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)
        FileIO.write_markdown(setting_dir / "金手指.md", "# 金手指\n\n系统提示音。")

        resp = await fastapi_client.post("/api/query/golden-finger", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert "系统" in data["golden_finger"]["content"]

    async def test_query_foreshadowing_empty(self, fastapi_client, sample_project) -> None:
        """Query foreshadowing returns empty list when no data."""
        resp = await fastapi_client.post("/api/query/foreshadowing", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert data["foreshadowing"] == []

    async def test_query_entity_not_found(self, fastapi_client, sample_project) -> None:
        """Query entity returns unknown fallback."""
        resp = await fastapi_client.post("/api/query/entity", json={
            "project_id": sample_project["project_id"],
            "entity_id": "nonexistent-entity",
        })
        data = resp.json()
        assert data["entity"]["name"] == "nonexistent-entity"
        assert data["entity"]["type"] == "unknown"


class TestLearnAPI:
    async def test_learn_list_empty(self, fastapi_client, sample_project) -> None:
        """Learn list returns empty when no patterns."""
        resp = await fastapi_client.post("/api/learn/list", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert data["patterns"] == []

    async def test_learn_add_and_list(self, fastapi_client, sample_project) -> None:
        """Learn add then list returns pattern."""
        resp = await fastapi_client.post("/api/learn/add", json={
            "project_id": sample_project["project_id"],
            "pattern_type": "writing-style",
            "description": "使用短句制造紧张感",
            "category": "节奏",
            "importance": "high",
        })
        data = resp.json()
        assert data["ok"] is True
        assert data["duplicated"] is False

        resp = await fastapi_client.post("/api/learn/list", json={
            "project_id": sample_project["project_id"],
        })
        data = resp.json()
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["pattern_type"] == "writing-style"

    async def test_learn_add_duplicate(self, fastapi_client, sample_project) -> None:
        """Learn add duplicate returns duplicated=true."""
        await fastapi_client.post("/api/learn/add", json={
            "project_id": sample_project["project_id"],
            "pattern_type": "test",
            "description": "test pattern",
        })
        resp = await fastapi_client.post("/api/learn/add", json={
            "project_id": sample_project["project_id"],
            "pattern_type": "test",
            "description": "test pattern",
        })
        data = resp.json()
        assert data["duplicated"] is True


class TestReviewAPIExtended:
    async def test_review_start_no_llm_config(self, fastapi_client, sample_project) -> None:
        """Review start returns error when no default LLM config."""
        resp = await fastapi_client.post("/api/review/start", json={
            "project_id": sample_project["project_id"],
            "chapter_num": 1,
        })
        data = resp.json()
        assert "error_code" in data

    async def test_review_report_not_found(self, fastapi_client, sample_project) -> None:
        """Review report returns error for nonexistent report."""
        resp = await fastapi_client.post("/api/review/report", json={
            "project_id": sample_project["project_id"],
            "report_id": "nonexistent",
        })
        data = resp.json()
        assert "error_code" in data
