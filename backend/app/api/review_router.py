"""Review API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.core.error_codes import ErrorCode, error_response
from app.models.schemas import (
    ReviewHistoryRequest,
    ReviewHistoryResponse,
    ReviewReportRequest,
    ReviewReportResponse,
    ReviewStartRequest,
    ReviewStartResponse,
)
from app.services.project_service import ProjectService
from app.services.review_service import ReviewService
from app.services.llm_service import LLMService, _decrypt_api_key
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/start")
async def review_start(req: ReviewStartRequest):
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
        task_type="review",
        project_id=req.project_id,
        chapter_num=req.chapter_num,
        total_steps=3,
    )

    service = ReviewService(
        task_id=task_state.task_id,
        project_id=req.project_id,
        chapter_num=req.chapter_num,
        project_root=project_root,
        caller=caller,
    )

    async def run_with_lock():
        async with lock:
            try:
                await service.execute()
            except Exception as e:
                from app.core.logger import get_logger
                get_logger(__name__).error("Review task failed: %s", e)

    task_ref = asyncio.create_task(run_with_lock())

    return ReviewStartResponse(task_id=task_state.task_id)


@router.post("/history", response_model=ReviewHistoryResponse)
async def review_history(req: ReviewHistoryRequest):
    try:
        project_root = ProjectService.get_project_root(req.project_id)
    except ValueError:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")

    reviews = ReviewService.list_review_history(project_root, req.chapter_num)
    return ReviewHistoryResponse(reviews=reviews)


@router.post("/report")
async def review_report(req: ReviewReportRequest):
    try:
        project_root = ProjectService.get_project_root(req.project_id)
    except ValueError:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")

    report = ReviewService.get_report(project_root, req.report_id)
    if not report:
        return error_response(ErrorCode.FILE_NOT_FOUND, f"审查报告 {req.report_id} 不存在")
    return ReviewReportResponse(report=report)
