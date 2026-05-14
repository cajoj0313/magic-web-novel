"""LLM configuration API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.error_codes import ErrorCode, error_response
from app.models.schemas import (
    LLMConfigAddRequest,
    LLMConfigAddResponse,
    LLMConfigDeleteRequest,
    LLMConfigInfo,
    LLMConfigListRequest,
    LLMConfigListResponse,
    LLMConfigSetDefaultRequest,
    LLMConfigTestRequest,
    LLMConfigTestResponse,
    LLMConfigUpdateRequest,
    OkResponse,
)
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/llm-configs", tags=["llm-configs"])


@router.post("/list", response_model=LLMConfigListResponse)
async def list_configs(_req: LLMConfigListRequest = LLMConfigListRequest()):
    configs = LLMService.list_configs()
    return LLMConfigListResponse(
        configs=[LLMConfigInfo(**c) for c in configs],
    )


@router.post("/add", response_model=LLMConfigAddResponse)
async def add_config(req: LLMConfigAddRequest):
    config_id = LLMService.add_config(
        name=req.name,
        provider=req.provider,
        model=req.model,
        url=req.url,
        api_key=req.api_key,
    )
    return LLMConfigAddResponse(id=config_id)


@router.post("/update", response_model=OkResponse)
async def update_config(req: LLMConfigUpdateRequest):
    ok = LLMService.update_config(
        config_id=req.id,
        name=req.name,
        provider=req.provider,
        model=req.model,
        url=req.url,
        api_key=req.api_key,
    )
    if not ok:
        return error_response(ErrorCode.LLM_CONFIG_NOT_FOUND, "配置不存在")
    return OkResponse()


@router.post("/delete", response_model=OkResponse)
async def delete_config(req: LLMConfigDeleteRequest):
    LLMService.delete_config(req.id)
    return OkResponse()


@router.post("/set-default", response_model=OkResponse)
async def set_default(req: LLMConfigSetDefaultRequest):
    ok = LLMService.set_default(req.id)
    if not ok:
        return error_response(ErrorCode.LLM_CONFIG_NOT_FOUND, "配置不存在")
    return OkResponse()


@router.post("/test", response_model=LLMConfigTestResponse)
async def test_connection(req: LLMConfigTestRequest):
    result = await LLMService.test_connection(req.id)
    return LLMConfigTestResponse(**result)
