"""Pydantic request/response schemas for all API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Generic response ───────────────────────────────────────────────

class OkResponse(BaseModel):
    ok: bool = True


# ─── Project ────────────────────────────────────────────────────────

class ProjectInfo(BaseModel):
    id: str
    title: str
    genre: str
    progress: int = 0
    last_updated: str | None = None


class ProjectListRequest(BaseModel):
    pass


class ProjectListResponse(BaseModel):
    projects: list[ProjectInfo]
    active_project_id: str | None = None


class ProjectCreateRequest(BaseModel):
    root_path: str
    genre: str
    target_words: int = 0
    target_chapters: int = 0


class ProjectCreateResponse(BaseModel):
    id: str
    title: str


class ProjectOverviewRequest(BaseModel):
    project_id: str


class ProjectOverviewResponse(BaseModel):
    title: str
    genre: str
    current_chapter: int = 0
    total_chapters: int = 0
    total_words: int = 0
    review_status: str = "unknown"
    last_updated: str | None = None


class ProjectDeleteRequest(BaseModel):
    project_id: str


class ProjectDeleteResponse(BaseModel):
    ok: bool = True


class ProjectSwitchRequest(BaseModel):
    project_id: str


# ─── Chapter ────────────────────────────────────────────────────────

class ChapterInfo(BaseModel):
    chapter_num: int
    title: str | None = None
    word_count: int = 0
    status: str = "unwritten"
    review_score: float | None = None
    last_updated: str | None = None


class ChapterListRequest(BaseModel):
    project_id: str
    volume: int | None = None


class ChapterListResponse(BaseModel):
    chapters: list[ChapterInfo]


class ChapterGetRequest(BaseModel):
    project_id: str
    chapter_num: int


class ChapterGetResponse(BaseModel):
    chapter_num: int
    title: str | None = None
    content: str = ""
    word_count: int = 0
    last_updated: str | None = None


class ChapterSaveRequest(BaseModel):
    project_id: str
    chapter_num: int
    content: str


class ChapterSaveResponse(BaseModel):
    ok: bool = True
    word_count: int


class ChapterDraftRequest(BaseModel):
    project_id: str
    chapter_num: int
    mode: str = "default"


class ChapterDraftResponse(BaseModel):
    task_id: str


class ChapterDraftBatchRequest(BaseModel):
    project_id: str
    start_chapter: int
    end_chapter: int
    mode: str = "default"


class ChapterDraftBatchResponse(BaseModel):
    task_id: str


# ─── Review ─────────────────────────────────────────────────────────

class ReviewIssue(BaseModel):
    severity: str
    category: str
    location: str | None = None
    description: str
    evidence: str | None = None
    fix_hint: str | None = None
    blocking: bool = False


class ReviewStartRequest(BaseModel):
    project_id: str
    chapter_num: int


class ReviewStartResponse(BaseModel):
    task_id: str


class ReviewHistoryRequest(BaseModel):
    project_id: str
    chapter_num: int


class ReviewHistoryEntry(BaseModel):
    report_id: str
    reviewed_at: str
    issues_count: int
    blocking_count: int
    overall_score: float | None = None


class ReviewHistoryResponse(BaseModel):
    reviews: list[ReviewHistoryEntry]


class ReviewReportRequest(BaseModel):
    project_id: str
    report_id: str


class ReviewSummary(BaseModel):
    total_issues: int = 0
    blocking_issues: int = 0
    categories: dict[str, int] = {}


class ReviewReportResponse(BaseModel):
    report: dict[str, Any] = Field(
        default_factory=dict,
        description="Full review report following schema v6",
    )


# ─── Planning ───────────────────────────────────────────────────────

class PlanMasterOutlineGetRequest(BaseModel):
    project_id: str


class PlanMasterOutlineGetResponse(BaseModel):
    content: str
    last_updated: str | None = None


class PlanMasterOutlineSaveRequest(BaseModel):
    project_id: str
    content: str


class PlanMasterOutlineSaveResponse(BaseModel):
    ok: bool = True


class PlanVolumeStartRequest(BaseModel):
    project_id: str
    volume_id: int


class PlanVolumeStartResponse(BaseModel):
    task_id: str


class PlanVolumeGetRequest(BaseModel):
    project_id: str
    volume_id: int


class PlanVolumeGetResponse(BaseModel):
    beat_sheet: str | None = None
    timeline: str | None = None
    chapter_outlines: list[dict[str, Any]] = []


# ─── Query ──────────────────────────────────────────────────────────

class QueryEntityRequest(BaseModel):
    project_id: str
    entity_id: str
    at_chapter: int | None = None


class QueryEntityResponse(BaseModel):
    entity: dict[str, Any] = {}


class QueryPowerSystemRequest(BaseModel):
    project_id: str


class QueryPowerSystemResponse(BaseModel):
    content: str


class QueryForeshadowingRequest(BaseModel):
    project_id: str
    chapter: int | None = None


class QueryForeshadowingResponse(BaseModel):
    foreshadowing: list[dict[str, Any]] = []


class QueryGoldenFingerRequest(BaseModel):
    project_id: str
    chapter: int | None = None


class QueryGoldenFingerResponse(BaseModel):
    golden_finger: dict[str, Any] = {}


# ─── Settings ───────────────────────────────────────────────────────

class SettingGetRequest(BaseModel):
    project_id: str
    setting_type: str


class SettingGetResponse(BaseModel):
    content: str
    last_updated: str | None = None


class SettingSaveRequest(BaseModel):
    project_id: str
    setting_type: str
    content: str


class SettingSaveResponse(BaseModel):
    ok: bool = True


# ─── LLM Config ─────────────────────────────────────────────────────

class LLMConfigInfo(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    url: str
    api_key_masked: str = ""
    is_default: bool = False


class LLMConfigListRequest(BaseModel):
    pass


class LLMConfigListResponse(BaseModel):
    configs: list[LLMConfigInfo]


class LLMConfigAddRequest(BaseModel):
    name: str
    provider: str
    model: str
    url: str
    api_key: str


class LLMConfigAddResponse(BaseModel):
    id: str


class LLMConfigUpdateRequest(BaseModel):
    id: str
    name: str | None = None
    provider: str | None = None
    model: str | None = None
    url: str | None = None
    api_key: str | None = None


class LLMConfigDeleteRequest(BaseModel):
    id: str


class LLMConfigDeleteResponse(BaseModel):
    ok: bool = True


class LLMConfigUpdateResponse(BaseModel):
    ok: bool = True


class LLMConfigSetDefaultRequest(BaseModel):
    id: str


class LLMConfigTestRequest(BaseModel):
    id: str


class LLMConfigTestResponse(BaseModel):
    ok: bool
    latency_ms: float | None = None
    error: str | None = None
    model_info: str | None = None


# ─── Task Management ────────────────────────────────────────────────

class TaskProgress(BaseModel):
    current_step: int = 0
    total_steps: int = 0
    step_name: str = ""
    elapsed_ms: int = 0


class TaskStatusRequest(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    type: str
    status: str
    progress: TaskProgress
    result: dict[str, Any] | None = None


class TaskPauseRequest(BaseModel):
    task_id: str


class TaskPauseResponse(BaseModel):
    ok: bool = True


class TaskResumeRequest(BaseModel):
    task_id: str


class TaskResumeResponse(BaseModel):
    ok: bool = True


class TaskCancelRequest(BaseModel):
    task_id: str


class TaskCancelResponse(BaseModel):
    ok: bool = True
    message: str | None = None


class TaskControlRequest(BaseModel):
    task_id: str


class TaskControlResponse(BaseModel):
    ok: bool = True


# ─── Learn Mode ─────────────────────────────────────────────────────

class LearnPatternInfo(BaseModel):
    pattern_type: str
    description: str
    category: str | None = None
    importance: str | None = None
    learned_at: str


class LearnListRequest(BaseModel):
    project_id: str


class LearnListResponse(BaseModel):
    patterns: list[LearnPatternInfo]


class LearnAddRequest(BaseModel):
    project_id: str
    pattern_type: str
    description: str
    category: str | None = None
    importance: str | None = None


class LearnAddResponse(BaseModel):
    ok: bool = True
    duplicated: bool = False
