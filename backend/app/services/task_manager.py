"""Task state management — in-memory + persistence, pause/resume/cancel."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.data.task_store import TaskStore


class TaskState:
    """Runtime state of a long-running task."""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        project_id: str,
        chapter_num: int | None = None,
        total_steps: int = 6,
    ) -> None:
        self.task_id = task_id
        self.type = task_type
        self.project_id = project_id
        self.chapter_num = chapter_num
        self.total_steps = total_steps
        self.status = "running"
        self.current_step = 0
        self.step_name = ""
        self.started_at = time.monotonic()
        self.step_results: dict[int, dict[str, Any]] = {}
        self._pause_flag = asyncio.Event()
        self._cancel_flag = asyncio.Event()
        self._pause_flag.set()  # Start un-paused

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_at) * 1000)

    def is_paused(self) -> bool:
        return not self._pause_flag.is_set()

    def is_cancelled(self) -> bool:
        return self._cancel_flag.is_set()

    def pause(self) -> None:
        self._pause_flag.clear()

    def resume(self) -> None:
        self._pause_flag.set()

    def cancel(self) -> None:
        self._cancel_flag.set()
        self._pause_flag.set()  # Unblock if waiting
        self.status = "cancelled"

    async def wait_while_paused(self) -> None:
        while self.is_paused() and not self.is_cancelled():
            await asyncio.sleep(0.3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "type": self.type,
            "status": self.status,
            "chapter_num": self.chapter_num,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_name": self.step_name,
            "elapsed_ms": self.elapsed_ms,
            "step_results": {str(k): v for k, v in self.step_results.items()},
        }


class TaskManager:
    """Manage all task states with SSE event broadcasting."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._sse_queues: dict[str, list[asyncio.Queue]] = {}

    def get_lock(self, project_id: str) -> asyncio.Lock:
        if project_id not in self._locks:
            self._locks[project_id] = asyncio.Lock()
        return self._locks[project_id]

    def create_task(
        self,
        task_type: str,
        project_id: str,
        chapter_num: int | None = None,
        total_steps: int = 6,
    ) -> TaskState:
        task_id = str(uuid.uuid4())
        state = TaskState(task_id, task_type, project_id, chapter_num, total_steps)
        self._tasks[task_id] = state
        self._sse_queues[task_id] = []
        return state

    def get_task(self, task_id: str) -> TaskState | None:
        return self._tasks.get(task_id)

    def pause_task(self, task_id: str) -> bool:
        state = self._tasks.get(task_id)
        if state and state.status == "running":
            state.pause()
            state.status = "paused"
            self._broadcast(task_id, "task_paused", {
                "task_id": task_id,
                "completed_steps": state.current_step,
                "current_step_name": state.step_name,
            })
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        state = self._tasks.get(task_id)
        if state and state.status == "paused":
            state.resume()
            state.status = "running"
            self._broadcast(task_id, "task_resumed", {
                "task_id": task_id,
                "resume_from_step": state.current_step + 1,
            })
            return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        state = self._tasks.get(task_id)
        if state and state.status in ("running", "paused"):
            state.cancel()
            self._broadcast(task_id, "task_cancelled", {
                "task_id": task_id,
                "completed_steps": state.current_step,
            })
            return True
        return False

    def get_status(self, task_id: str) -> dict[str, Any] | None:
        state = self._tasks.get(task_id)
        if not state:
            return None
        return {
            "task_id": state.task_id,
            "type": state.type,
            "status": state.status,
            "progress": {
                "current_step": state.current_step,
                "total_steps": state.total_steps,
                "step_name": state.step_name,
                "elapsed_ms": state.elapsed_ms,
            },
        }

    def subscribe(self, task_id: str) -> asyncio.Queue | None:
        queues = self._sse_queues.get(task_id)
        if queues is None:
            return None
        q: asyncio.Queue = asyncio.Queue()
        queues.append(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        if task_id in self._sse_queues:
            if q in self._sse_queues[task_id]:
                self._sse_queues[task_id].remove(q)

    def _broadcast(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        queues = self._sse_queues.get(task_id, [])
        for q in list(queues):
            q.put_nowait((event, data))

    def emit(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        self._broadcast(task_id, event, data)


# Singleton
task_manager = TaskManager()
