"""Planning API routes."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from app.core.error_codes import ErrorCode, error_response
from app.data.file_io import FileIO
from app.models.schemas import (
    OkResponse,
    PlanMasterOutlineGetRequest,
    PlanMasterOutlineGetResponse,
    PlanMasterOutlineSaveRequest,
    PlanVolumeGetRequest,
    PlanVolumeGetResponse,
    PlanVolumeStartRequest,
    PlanVolumeStartResponse,
)
from app.services.project_service import ProjectService
from app.services.plan_orchestrator import PlanOrchestrator
from app.services.llm_service import LLMService, _decrypt_api_key
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/plan", tags=["plan"])


@router.post("/master-outline/get")
async def master_outline_get(req: PlanMasterOutlineGetRequest):
    try:
        root = ProjectService.get_project_root(req.project_id)
        path = root / "大纲" / "总纲.md"
        if path.exists():
            content = FileIO.read_markdown(path)
            from datetime import datetime, timezone
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            return PlanMasterOutlineGetResponse(content=content, last_updated=mtime)
        return PlanMasterOutlineGetResponse(content="", last_updated=None)
    except ValueError:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")


@router.post("/master-outline/save", response_model=OkResponse)
async def master_outline_save(req: PlanMasterOutlineSaveRequest):
    try:
        root = ProjectService.get_project_root(req.project_id)
        path = root / "大纲" / "总纲.md"
        FileIO.write_markdown(path, req.content)
        return OkResponse()
    except ValueError:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")


@router.post("/volume/start")
async def volume_start(req: PlanVolumeStartRequest):
    # Check for concurrent task
    lock = task_manager.get_lock(req.project_id)
    if lock.locked():
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "该项目已有正在执行的任务，请等待完成后再试",
        )

    try:
        project_root = ProjectService.get_project_root(req.project_id)
    except ValueError as e:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, str(e))

    llm_config = LLMService.get_default_config()
    if not llm_config:
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "未配置 LLM 模型，请先在模型配置页面添加并设为默认",
        )

    api_key = _decrypt_api_key(llm_config["api_key_encrypted"])

    from app.services.chapter_orchestrator import _make_caller
    caller = _make_caller(
        provider=llm_config["provider"],
        api_key=api_key,
        base_url=llm_config["url"],
        model=llm_config["model"],
    )

    task_state = task_manager.create_task(
        task_type="plan",
        project_id=req.project_id,
        total_steps=9,
    )

    orchestrator = PlanOrchestrator(
        task_id=task_state.task_id,
        project_id=req.project_id,
        volume_id=req.volume_id,
        project_root=project_root,
        caller=caller,
    )

    async def run_with_lock():
        async with lock:
            try:
                await orchestrator.execute()
            except Exception as e:
                from app.core.logger import get_logger
                get_logger(__name__).error("Plan task failed: %s", e)

    task_ref = asyncio.create_task(run_with_lock())

    return PlanVolumeStartResponse(task_id=task_state.task_id)


@router.post("/volume/get", response_model=PlanVolumeGetResponse)
async def volume_get(req: PlanVolumeGetRequest):
    try:
        root = ProjectService.get_project_root(req.project_id)
        # Try to find existing volume files
        volume_dir = root / "大纲"
        beat_sheet = ""
        timeline = ""
        chapter_outlines: list[dict[str, Any]] = []
        if volume_dir.exists():
            for f in volume_dir.iterdir():
                if f.name.startswith(f"第{req.volume_id}卷"):
                    content = FileIO.read_markdown(f)
                    if "节拍" in f.name or "beat" in f.name.lower():
                        beat_sheet = content
                    elif "时间线" in f.name or "timeline" in f.name.lower():
                        timeline = content
                    elif "详细大纲" in f.name:
                        chapter_outlines = _parse_chapter_outlines(content)
        return PlanVolumeGetResponse(beat_sheet=beat_sheet, timeline=timeline, chapter_outlines=chapter_outlines)
    except ValueError:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")


def _parse_chapter_outlines(content: str) -> list[dict[str, Any]]:
    """Parse chapter outlines from a detailed volume outline markdown file.

    Looks for patterns like `### 第N章` or `- 第N章` headings.
    """
    import re
    outlines: list[dict[str, Any]] = []
    # Match patterns like "### 第5章-标题" or "- 第5章"
    pattern = re.compile(r"#+\s*第\s*(\d+)\s*章\s*[-–—]?\s*(.*)")
    for match in pattern.finditer(content):
        chapter_num = int(match.group(1))
        title = match.group(2).strip()
        outlines.append({"chapter_num": chapter_num, "title": title})
    return outlines
