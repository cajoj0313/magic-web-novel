"""Learn mode API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import (
    LearnAddRequest,
    LearnAddResponse,
    LearnListRequest,
    LearnListResponse,
    LearnPatternInfo,
)
from app.services.learn_service import LearnService

router = APIRouter(prefix="/api/learn", tags=["learn"])


@router.post("/list", response_model=LearnListResponse)
async def list_patterns(req: LearnListRequest):
    patterns = LearnService.list_patterns(req.project_id)
    return LearnListResponse(
        patterns=[LearnPatternInfo(**p) for p in patterns],
    )


@router.post("/add", response_model=LearnAddResponse)
async def add_pattern(req: LearnAddRequest):
    duplicated = LearnService.add_pattern(
        req.project_id,
        pattern_type=req.pattern_type,
        description=req.description,
        category=req.category,
        importance=req.importance,
    )
    return LearnAddResponse(ok=True, duplicated=duplicated)
