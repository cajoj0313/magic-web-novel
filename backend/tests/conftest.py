"""Global test fixtures for backend tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.data.file_io import FileIO
from main import app


# ── FastAPI test client ─────────────────────────────────────────────────────

@pytest.fixture
def fastapi_client():
    """httpx AsyncClient mounted on the FastAPI app."""
    import httpx
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ── Sample project fixture ──────────────────────────────────────────────────

SAMPLE_STATE = {
    "project": {
        "title": "测试小说",
        "genre": "玄幻",
        "target_words": 300000,
        "target_chapters": 200,
    },
    "progress": {
        "current_chapter": 3,
        "total_chapters": 200,
        "total_words": 6000,
        "review_status": "pending",
    },
    "word_count": 6000,
    "title": "测试小说",
    "genre": "玄幻",
    "total_chapters": 200,
    "review_status": "pending",
}

SAMPLE_CONTRACT = {
    "chapter_id": "ch_0001",
    "chapter_num": 1,
    "title": "第一章标题",
    "core_event": "主角觉醒",
    "cbn": "主角 | 觉醒 | 力量",
    "cpns": ["主角 | 练习 | 新技能"],
    "cen": "主角 | 发现 | 秘密",
    "goal": "引入主角和世界观",
}


def _build_project(tmp_path: Path, num_chapters: int = 3) -> dict[str, Any]:
    """Build a test project with state.json, contract tree, and written chapters."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # .webnovel/state.json
    webnovel = project_root / ".webnovel"
    webnovel.mkdir()
    FileIO.write_json(webnovel / "state.json", SAMPLE_STATE)

    # .story-system/chapters/
    contracts_dir = project_root / ".story-system" / "chapters"
    contracts_dir.mkdir(parents=True)
    for i in range(1, num_chapters + 1):
        contract = {
            **SAMPLE_CONTRACT,
            "chapter_id": f"ch_{i:04d}",
            "chapter_num": i,
        }
        FileIO.write_json(contracts_dir / f"chapter_{i:04d}.review.json", contract)

    # .story-system/volumes/ (for plan orchestrator)
    volumes_dir = project_root / ".story-system" / "volumes"
    volumes_dir.mkdir(parents=True)

    # 正文/ files
    chapter_dir = project_root / "正文"
    chapter_dir.mkdir()
    for i in range(1, num_chapters + 1):
        content = f"这是第{i}章的正文内容。" * 100
        FileIO.write_markdown(chapter_dir / f"第{i:04d}章-第{i}章标题.md", content)

    # Setup project_registry in temp app_data_dir
    app_data_dir = tmp_path / "app_data"
    app_data_dir.mkdir()
    registry_path = app_data_dir / "project_registry.json"
    project_id = "test-project-001"
    registry = {
        "projects": [
            {
                "id": project_id,
                "title": "测试小说",
                "root_path": str(project_root),
                "genre": "玄幻",
                "target_words": 300000,
                "target_chapters": 200,
            }
        ],
        "active_project_id": project_id,
    }
    FileIO.write_json(registry_path, registry)

    # Patch ensure_app_data_dir at the consumer site (import binding)
    with patch("app.data.project_registry.ensure_app_data_dir") as mock_ensure:
        mock_ensure.return_value = app_data_dir
        with patch("app.core.config.ensure_app_data_dir") as mock_ensure2:
            mock_ensure2.return_value = app_data_dir
            yield {
                "project_id": project_id,
                "project_root": project_root,
                "app_data_dir": app_data_dir,
            }


@pytest.fixture
def sample_project(tmp_path: Path):
    """Create a test project with state.json, contract tree, 3 written chapters."""
    yield from _build_project(tmp_path, num_chapters=3)


# ── Mock LLM response ───────────────────────────────────────────────────────

MOCK_LLM_RESPONSES = {
    "context": json.dumps({
        "task_book": {
            "chapter_num": 1,
            "title": "第一章标题",
            "core_event": "主角觉醒",
            "cbn": "主角 | 觉醒 | 力量",
            "cpns": ["主角 | 练习 | 新技能"],
            "cen": "主角 | 发现 | 秘密",
            "goal": "引入主角和世界观",
        },
    }, ensure_ascii=False),
    "draft": "这是起草的正文内容。主角站在山顶上，感受着体内涌动的力量。风吹过他的脸庞，带来了远方的气息。他知道自己踏上了一条不归路。",
    "review": json.dumps({
        "issues": [],
        "summary": "章节质量良好，无明显问题。",
    }, ensure_ascii=False),
    "polish": "这是润色后的正文内容。主角伫立在苍茫的山巅，感受着体内奔涌的力量。凛冽的风拂过他的面颊，带来了远方未知的气息。他明白，自己已踏上了一条无法回头的路。",
    "data": json.dumps({
        "commit": {
            "chapter_num": 1,
            "entities": [{"name": "主角", "type": "character"}],
            "relationships": [],
            "foreshadowing": [],
        },
    }, ensure_ascii=False),
    "beat_sheet": "# 第1卷节拍表\n\n## 节拍1\n情节：主角初入修真界...",
    "timeline": "# 第1卷时间线\n\n## 第一天\n主角抵达修真学院...",
    "chapter_outlines": "# 第1卷详细大纲\n\n## 第1章\n核心事件：主角觉醒...",
    "continuity": '{"continuity_issues": []}',
    "conflicts": '{"conflicts": []}',
    "new_settings": '{"new_settings": []}',
}


@pytest.fixture
def mock_llm_response() -> dict[str, str]:
    """Mock LLM responses keyed by scenario name."""
    return dict(MOCK_LLM_RESPONSES)


@pytest.fixture
def mock_anthropic_client(mock_llm_response: dict[str, str]):
    """Mock LLM caller (Protocol-compatible) that returns predefined responses."""
    async def fake_call(system: str, user: str, max_tokens: int = 8192, temperature: float = 0.7, **kwargs) -> str:
        sys_lower = system.lower()
        if "你是中文网文作家" in system:
            return mock_llm_response["draft"]
        elif "写作任务" in system:
            return mock_llm_response["context"]
        elif "审查" in system:
            return mock_llm_response["review"]
        elif "润色" in system:
            return mock_llm_response["polish"]
        elif "设定管理" in system:
            return mock_llm_response["data"]
        elif "节拍表" in system:
            return mock_llm_response["beat_sheet"]
        elif "时间线" in system:
            return mock_llm_response["timeline"]
        elif "逐章章纲" in system:
            return mock_llm_response["chapter_outlines"]
        elif "连续性" in system:
            return mock_llm_response["continuity"]
        elif "验证" in system:
            return mock_llm_response["conflicts"]
        else:
            return mock_llm_response["draft"]

    return fake_call


@pytest.fixture
def mock_llm_caller_failing():
    """Mock caller that raises an exception on every call."""
    async def failer(*args, **kwargs):
        raise RuntimeError("LLM API unavailable")

    return failer


@pytest.fixture
def mock_llm_caller_retry():
    """Mock caller that fails twice then succeeds."""
    call_count = 0

    async def flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError(f"Rate limited (attempt {call_count})")
        return "Success after retries"

    return flaky
