"""Task management API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.error_codes import ErrorCode, error_response
from app.models.schemas import (
    OkResponse,
    TaskControlRequest,
    TaskControlResponse,
    TaskStatusRequest,
    TaskStatusResponse,
    TaskProgress,
)
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/status")
async def task_status(req: TaskStatusRequest):
    status = task_manager.get_status(req.task_id)
    if not status:
        return {"ok": False, "error": "任务不存在"}
    return TaskStatusResponse(**status)


@router.post("/pause", response_model=TaskControlResponse)
async def task_pause(req: TaskControlRequest):
    ok = task_manager.pause_task(req.task_id)
    return TaskControlResponse(ok=ok)


@router.post("/resume", response_model=TaskControlResponse)
async def task_resume(req: TaskControlRequest):
    ok = task_manager.resume_task(req.task_id)
    return TaskControlResponse(ok=ok)


@router.post("/cancel", response_model=TaskControlResponse)
async def task_cancel(req: TaskControlRequest):
    ok = task_manager.cancel_task(req.task_id)
    return TaskControlResponse(ok=ok)
