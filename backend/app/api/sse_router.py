"""SSE event streaming for task progress."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.task_manager import task_manager

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def sse_events(request: Request, task_id: str):
    """Server-Sent Events endpoint for task progress."""

    q = task_manager.subscribe(task_id)
    if q is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": {"code": "TASK_NOT_FOUND", "message": "任务不存在"}},
        )

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event, data = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                    # Close connection on terminal events
                    if event in ("task_complete", "task_failed", "task_cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        finally:
            task_manager.unsubscribe(task_id, q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
