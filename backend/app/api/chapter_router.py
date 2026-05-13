"""Chapter management API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.core.error_codes import ErrorCode, error_response
from app.models.schemas import (
    ChapterDraftRequest,
    ChapterDraftResponse,
    ChapterGetRequest,
    ChapterGetResponse,
    ChapterInfo,
    ChapterListRequest,
    ChapterListResponse,
    ChapterSaveRequest,
    ChapterSaveResponse,
)
from app.services.chapter_orchestrator import ChapterOrchestrator, _make_caller
from app.services.chapter_service import ChapterService
from app.services.llm_service import LLMService, _decrypt_api_key
from app.services.project_service import ProjectService
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.post("/list", response_model=ChapterListResponse)
async def list_chapters(req: ChapterListRequest):
    chapters = await ChapterService.list_chapters(req.project_id, volume=req.volume)
    return ChapterListResponse(
        chapters=[ChapterInfo(**c) for c in chapters],
    )


@router.post("/get", response_model=ChapterGetResponse)
async def get_chapter(req: ChapterGetRequest):
    try:
        chapter = ChapterService.get_chapter(req.project_id, req.chapter_num)
        return ChapterGetResponse(**chapter)
    except ValueError:
        return error_response(ErrorCode.CHAPTER_NOT_FOUND, f"第{req.chapter_num}章不存在")


@router.post("/save", response_model=ChapterSaveResponse)
async def save_chapter(req: ChapterSaveRequest):
    wc = ChapterService.save_chapter(req.project_id, req.chapter_num, req.content)
    return ChapterSaveResponse(ok=True, word_count=wc)


@router.post("/draft")
async def draft_chapter(req: ChapterDraftRequest):
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
    caller = _make_caller(
        provider=llm_config["provider"],
        api_key=api_key,
        base_url=llm_config["url"],
        model=llm_config["model"],
    )

    task_state = task_manager.create_task(
        task_type="draft",
        project_id=req.project_id,
        chapter_num=req.chapter_num,
        total_steps=6,
    )

    orchestrator = ChapterOrchestrator(
        task_id=task_state.task_id,
        project_id=req.project_id,
        chapter_num=req.chapter_num,
        project_root=project_root,
        caller=caller,
        mode=req.mode,
    )

    async def run_with_lock():
        async with lock:
            try:
                await orchestrator.execute()
            except Exception as e:
                from app.core.logger import get_logger
                get_logger(__name__).error("Draft task failed: %s", e)

    task_ref = asyncio.create_task(run_with_lock())

    return ChapterDraftResponse(task_id=task_state.task_id)
