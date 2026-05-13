"""Task state persistence — workflow_state.json per project.

Uses atomic write (temp file + rename) to prevent corruption on crash.

State file path: ``{store_dir}/workflow_state.json`` — a single file
containing all task states keyed by task_id:

.. code-block:: json

   {
     "task-001": { "status": "running", "step": 2, "data": {...} },
     "task-002": { "status": "paused", "step": 3, "data": {...} }
   }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.data.file_io import FileIO

logger = get_logger(__name__)

_STATE_FILE = "workflow_state.json"
_WEBNOVEL_DIR = ".webnovel"


class TaskStore:
    """Read/write task workflow states."""

    def __init__(self, store_dir: Path | None = None) -> None:
        self._store_dir = store_dir or Path.cwd()

    def _state_path(self) -> Path:
        return self._store_dir / _WEBNOVEL_DIR / _STATE_FILE

    def _read_all(self) -> dict[str, Any]:
        p = self._state_path()
        if p.exists():
            return FileIO.read_json(p)
        return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        FileIO.write_json(p, data)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def save_state(self, task_id: str, state: dict[str, Any]) -> None:
        """Atomically persist a task's state into the shared file."""
        data = self._read_all()
        data[task_id] = state
        self._write_all(data)
        logger.debug("Saved state for task: %s", task_id)

    async def load_state(self, task_id: str) -> dict[str, Any] | None:
        """Load a task's state. Returns None if not found."""
        data = self._read_all()
        state = data.get(task_id)
        if state is not None:
            logger.debug("Loaded state for task: %s", task_id)
        return state

    async def delete_state(self, task_id: str) -> bool:
        """Delete a task's state file entry. Returns False if not found."""
        data = self._read_all()
        if task_id not in data:
            return False
        del data[task_id]
        self._write_all(data)
        logger.debug("Deleted state for task: %s", task_id)
        return True

    async def list_states(self) -> list[str]:
        """List all task IDs that have saved state."""
        data = self._read_all()
        task_ids = list(data.keys())
        logger.debug("Found %d task states", len(task_ids))
        return task_ids

    # ------------------------------------------------------------------
    # Convenience aliases used by orchestrators and tests
    # ------------------------------------------------------------------

    def save(self, data: dict[str, Any]) -> None:
        """Save a task state dict. Writes data directly to the state file."""
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        FileIO.write_json(p, data)
        logger.debug("Saved task state to %s", p)

    def load(self) -> dict[str, Any] | None:
        """Load the active task state. Returns None if not found."""
        data = self._read_all()
        state = data.get("active_task")
        if state is not None:
            return {"active_task": state}
        return None

    def clear(self) -> None:
        """Clear all task states by deleting the workflow state file."""
        p = self._state_path()
        if p.exists():
            p.unlink()
            logger.debug("Cleared workflow state file")
