"""Unit tests for TaskStore persistence."""

from __future__ import annotations

from pathlib import Path

from app.data.task_store import TaskStore


class TestSaveAndLoad:
    def test_save_and_load(self, tmp_path: Path) -> None:
        """Saved state can be loaded correctly."""
        webnovel = tmp_path / ".webnovel"
        webnovel.mkdir()
        store = TaskStore(tmp_path)
        state = {"active_task": {"task_id": "abc", "status": "running", "current_step": 2}}
        store.save(state)
        loaded = store.load()
        assert loaded is not None
        assert loaded["active_task"]["task_id"] == "abc"
        assert loaded["active_task"]["current_step"] == 2

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Returns None when workflow_state.json doesn't exist."""
        store = TaskStore(tmp_path)
        assert store.load() is None


class TestClear:
    def test_clear(self, tmp_path: Path) -> None:
        """Clear deletes the workflow_state.json file."""
        webnovel = tmp_path / ".webnovel"
        webnovel.mkdir()
        store = TaskStore(tmp_path)
        store.save({"active_task": {"task_id": "x"}})
        assert (webnovel / "workflow_state.json").exists()
        store.clear()
        assert not (webnovel / "workflow_state.json").exists()
        assert store.load() is None
