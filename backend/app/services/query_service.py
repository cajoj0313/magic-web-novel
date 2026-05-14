"""Query service — multi-source aggregation (contract tree + index.db + settings)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.data.file_io import FileIO
from app.services.project_service import ProjectService


class QueryService:
    """Query entities, power systems, foreshadowing, golden finger."""

    @staticmethod
    def _get_db_path(project_id: str) -> Path:
        root = ProjectService.get_project_root(project_id)
        return root / ".webnovel" / "index.db"

    @staticmethod
    def query_entity(project_id: str, entity_id: str, at_chapter: int | None = None) -> dict[str, Any]:
        db_path = QueryService._get_db_path(project_id)
        if not db_path.exists():
            return {"name": entity_id, "type": "unknown", "state": "", "relationships": []}
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
                row = cursor.fetchone()
                if row:
                    entity = dict(row)
                    cursor2 = conn.execute(
                        "SELECT * FROM relationships WHERE entity_id = ? OR related_entity_id = ?",
                        (entity_id, entity_id),
                    )
                    relationships = [dict(r) for r in cursor2.fetchall()]
                    return {
                        "name": entity.get("name", ""),
                        "type": entity.get("type", ""),
                        "state": entity.get("state", ""),
                        "relationships": relationships,
                    }
                return {"name": entity_id, "type": "unknown", "state": "", "relationships": []}
        except Exception:
            return {"name": entity_id, "type": "unknown", "state": "", "relationships": []}

    @staticmethod
    def query_power_system(project_id: str) -> str:
        root = ProjectService.get_project_root(project_id)
        path = root / "设定集" / "力量体系.md"
        if path.exists():
            return FileIO.read_markdown(path)
        return "力量体系设定尚未创建"

    @staticmethod
    def query_foreshadowing(project_id: str, chapter: int | None = None) -> list[dict[str, Any]]:
        db_path = QueryService._get_db_path(project_id)
        if not db_path.exists():
            return []
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM entities WHERE type = 'foreshadowing' ORDER BY name",
                )
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    @staticmethod
    def query_golden_finger(project_id: str, chapter: int | None = None) -> dict[str, Any]:
        root = ProjectService.get_project_root(project_id)
        path = root / "设定集" / "金手指.md"
        if path.exists():
            content = FileIO.read_markdown(path)
            return {"content": content}
        return {"content": "金手指设定尚未创建"}
