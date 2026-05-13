"""Query API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import (
    QueryEntityRequest,
    QueryEntityResponse,
    QueryForeshadowingRequest,
    QueryForeshadowingResponse,
    QueryGoldenFingerRequest,
    QueryGoldenFingerResponse,
    QueryPowerSystemRequest,
    QueryPowerSystemResponse,
)
from app.services.query_service import QueryService

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("/entity", response_model=QueryEntityResponse)
async def query_entity(req: QueryEntityRequest):
    entity = QueryService.query_entity(req.project_id, req.entity_id, req.at_chapter)
    return QueryEntityResponse(entity=entity)


@router.post("/power-system", response_model=QueryPowerSystemResponse)
async def query_power_system(req: QueryPowerSystemRequest):
    content = QueryService.query_power_system(req.project_id)
    return QueryPowerSystemResponse(content=content)


@router.post("/foreshadowing", response_model=QueryForeshadowingResponse)
async def query_foreshadowing(req: QueryForeshadowingRequest):
    results = QueryService.query_foreshadowing(req.project_id, req.chapter)
    return QueryForeshadowingResponse(foreshadowing=results)


@router.post("/golden-finger", response_model=QueryGoldenFingerResponse)
async def query_golden_finger(req: QueryGoldenFingerRequest):
    result = QueryService.query_golden_finger(req.project_id, req.chapter)
    return QueryGoldenFingerResponse(golden_finger=result)
