"""Project management API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.core.error_codes import ErrorCode, error_response
from app.models.schemas import (
    OkResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDeleteRequest,
    ProjectInfo,
    ProjectListRequest,
    ProjectListResponse,
    ProjectOverviewRequest,
    ProjectOverviewResponse,
    ProjectSwitchRequest,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/list", response_model=ProjectListResponse)
async def list_projects(_req: ProjectListRequest = ProjectListRequest()):
    projects, active_id = await ProjectService.list_projects()
    return ProjectListResponse(
        projects=[ProjectInfo(**p) for p in projects],
        active_project_id=active_id,
    )


@router.post("/create", response_model=ProjectCreateResponse)
async def create_project(req: ProjectCreateRequest):
    try:
        project_id, title = await ProjectService.create_project(
            root_path=req.root_path,
            title=Path(req.root_path).name,
            genre=req.genre,
            target_words=req.target_words,
            target_chapters=req.target_chapters,
        )
        return ProjectCreateResponse(id=project_id, title=title)
    except ValueError as e:
        return error_response(ErrorCode.PROJECT_ROOT_INVALID, str(e))


@router.post("/delete", response_model=OkResponse)
async def delete_project(req: ProjectDeleteRequest):
    await ProjectService.delete_project(req.project_id)
    return OkResponse()


@router.post("/switch", response_model=OkResponse)
async def switch_project(req: ProjectSwitchRequest):
    await ProjectService.switch_project(req.project_id)
    return OkResponse()


@router.post("/overview", response_model=ProjectOverviewResponse)
async def project_overview(req: ProjectOverviewRequest):
    try:
        overview = ProjectService.get_overview(req.project_id)
        return ProjectOverviewResponse(**overview)
    except ValueError as e:
        return error_response(ErrorCode.PROJECT_NOT_FOUND, str(e))
