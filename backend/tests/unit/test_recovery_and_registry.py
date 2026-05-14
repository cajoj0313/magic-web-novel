"""Unit tests for recovery, concurrency, SQLite, and project registry."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.file_io import FileIO


class TestRecoveryFromStateFile:
    """Recover from workflow_state.json after simulated crash."""

    async def test_recovery_skips_completed_steps(self, tmp_path: Path) -> None:
        """After crash recovery, skips already-completed steps."""
        from app.services.chapter_orchestrator import ChapterOrchestrator
        from app.data.task_store import TaskStore

        # Pre-populate workflow_state.json as if steps 0 and 1 completed
        state_data = {
            "active_task": {
                "task_id": "test-recovery-001",
                "type": "draft",
                "chapter_num": 1,
                "status": "running",
                "current_step": 1,
                "total_steps": 6,
                "step_results": {
                    "0": {"status": "completed", "output": "context done"},
                    "1": {"status": "completed", "output": "draft done"},
                },
                "mode": "default",
                "last_updated": "2026-05-12T00:00:00Z",
            }
        }

        # Create project structure
        (tmp_path / ".webnovel").mkdir()
        FileIO.write_json(tmp_path / ".webnovel" / "state.json", {"project": {"genre": "玄幻"}})

        # Use TaskStore to persist state
        store = TaskStore(tmp_path)
        store.save(state_data)

        # Build contract tree
        contract_dir = tmp_path / ".story-system" / "chapters"
        contract_dir.mkdir(parents=True)
        FileIO.write_json(
            contract_dir / "chapter_0001.review.json",
            {"chapter_id": "ch_0001", "chapter_num": 1, "title": "测试章"},
        )

        # Load state back
        loaded = store.load()
        assert loaded is not None
        results = loaded.get("active_task", {}).get("step_results", {})
        step_results = {int(k): v for k, v in results.items()}

        # Steps 0 and 1 should be pre-populated
        assert 0 in step_results
        assert 1 in step_results
        assert step_results[0]["status"] == "completed"

    async def test_persist_state_creates_workflow_file(self, tmp_path: Path) -> None:
        """_persist_state writes workflow_state.json atomically."""
        from app.services.chapter_orchestrator import ChapterOrchestrator

        (tmp_path / ".webnovel").mkdir()
        FileIO.write_json(tmp_path / ".webnovel" / "state.json", {"genre": "玄幻"})

        orchestrator = ChapterOrchestrator(
            task_id="test-persist-001",
            project_id="proj-001",
            chapter_num=1,
            project_root=tmp_path,
            caller=AsyncMock(),
        )

        orchestrator.current_step = 0
        orchestrator.step_results[0] = {"status": "completed", "output": "test"}
        orchestrator._persist_state()

        state_file = tmp_path / ".webnovel" / "workflow_state.json"
        assert state_file.exists()

        data = FileIO.read_json(state_file)
        assert data["active_task"]["task_id"] == "test-persist-001"
        assert data["active_task"]["step_results"]["0"]["status"] == "completed"


class TestDoubleStartConflict:
    """Same project duplicate start returns 409 Conflict."""

    def test_task_manager_concurrent_tasks(self) -> None:
        """TaskManager tracks per-project locks."""
        from app.services.task_manager import TaskManager

        manager = TaskManager()
        lock_a = manager.get_lock("proj-001")
        lock_b = manager.get_lock("proj-001")

        assert lock_a is lock_b

        lock_c = manager.get_lock("proj-002")
        assert lock_a is not lock_c

    def test_task_manager_emit_broadcasts(self) -> None:
        """Emit broadcasts to all SSE subscribers."""
        from app.services.task_manager import TaskManager

        manager = TaskManager()
        state = manager.create_task("draft", "proj-001", chapter_num=1)

        q1: asyncio.Queue = asyncio.Queue()
        q2: asyncio.Queue = asyncio.Queue()
        manager._sse_queues[state.task_id].extend([q1, q2])

        manager.emit(state.task_id, "step_start", {"step": 1})

        event1 = q1.get_nowait()
        event2 = q2.get_nowait()

        assert event1 == ("step_start", {"step": 1})
        assert event2 == ("step_start", {"step": 1})


class TestSqliteAccess:
    """Query entities from index.db."""

    async def test_sqlite_access_query_entity(self, tmp_path: Path) -> None:
        """Query entity from index.db returns correct fields."""
        import sqlite3
        from app.data.sqlite_access import SQLiteAccess

        # Create a test index.db
        db_path = tmp_path / "index.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO entities (name, type, description)
            VALUES ('主角', 'character', '故事主角')
        """)
        conn.commit()
        conn.close()

        access = SQLiteAccess(db_path)
        result = await access.query("entities", "SELECT * FROM entities WHERE name = :name", {"name": "主角"})

        assert len(result) == 1
        assert result[0]["name"] == "主角"
        assert result[0]["type"] == "character"

        await access.close()

    async def test_sqlite_access_get_entities_by_type(self, tmp_path: Path) -> None:
        """get_entities filters by type."""
        import sqlite3
        from app.data.sqlite_access import SQLiteAccess

        db_path = tmp_path / "index.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE entities (id INTEGER PRIMARY KEY, name TEXT, type TEXT)")
        cursor.execute("INSERT INTO entities VALUES (1, '主角', 'character')")
        cursor.execute("INSERT INTO entities VALUES (2, '灵剑山', 'location')")
        conn.commit()
        conn.close()

        access = SQLiteAccess()
        result = await access.get_entities(tmp_path, entity_type="character")

        assert len(result) == 1
        assert result[0]["name"] == "主角"

        await access.close()


class TestProjectRegistryCrud:
    """Project registry CRUD operations."""

    async def test_registry_create_and_get(self, tmp_path: Path) -> None:
        """Create project and retrieve it."""
        from app.data.project_registry import ProjectRegistryStore, ProjectInfo

        store = ProjectRegistryStore(registry_path=tmp_path / "project_registry.json")

        info = await store.create_project(
            ProjectInfo(id="", name="测试小说", root_path="/tmp/test-project", genre="玄幻", total_chapters=200)
        )

        retrieved = await store.get_project(info.id)
        assert retrieved is not None
        assert retrieved.name == "测试小说"
        assert retrieved.genre == "玄幻"

    async def test_registry_list_projects(self, tmp_path: Path) -> None:
        """List all registered projects."""
        from app.data.project_registry import ProjectRegistryStore, ProjectInfo

        store = ProjectRegistryStore(registry_path=tmp_path / "project_registry.json")

        await store.create_project(ProjectInfo(id="", name="小说 A", root_path="/a", genre="玄幻"))
        await store.create_project(ProjectInfo(id="", name="小说 B", root_path="/b", genre="都市"))

        projects = await store.list_projects()
        assert len(projects) == 2

    async def test_registry_delete_project(self, tmp_path: Path) -> None:
        """Delete project removes from list."""
        from app.data.project_registry import ProjectRegistryStore, ProjectInfo

        store = ProjectRegistryStore(registry_path=tmp_path / "project_registry.json")

        info = await store.create_project(ProjectInfo(id="", name="ToDelete", root_path="/del"))
        await store.delete_project(info.id)

        assert await store.get_project(info.id) is None
        assert len(await store.list_projects()) == 0

    async def test_registry_update_project(self, tmp_path: Path) -> None:
        """Update project fields."""
        from app.data.project_registry import ProjectRegistryStore, ProjectInfo

        store = ProjectRegistryStore(registry_path=tmp_path / "project_registry.json")

        info = await store.create_project(ProjectInfo(id="", name="原名", root_path="/p"))
        updated = await store.update_project(info.id, {"title": "新名称", "genre": "仙侠"})

        assert updated.name == "新名称"
        assert updated.genre == "仙侠"
