"""Setting management API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import (
    SettingGetRequest,
    SettingGetResponse,
    SettingSaveRequest,
    SettingSaveResponse,
)
from app.services.setting_service import SettingService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.post("/get", response_model=SettingGetResponse)
async def get_setting(req: SettingGetRequest):
    content, last_updated = SettingService.get_setting(req.project_id, req.setting_type)
    return SettingGetResponse(content=content, last_updated=last_updated)


@router.post("/save", response_model=SettingSaveResponse)
async def save_setting(req: SettingSaveRequest):
    SettingService.save_setting(req.project_id, req.setting_type, req.content)
    return SettingSaveResponse()
