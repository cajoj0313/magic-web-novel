"""Learn mode service — add/view/deduplicate patterns."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.file_io import FileIO
from app.services.project_service import ProjectService

_MEMORY_FILE = ".webnovel/project_memory.json"


class LearnService:
    """Manage learning patterns."""

    @staticmethod
    def _memory_path(project_id: str) -> Path:
        root = ProjectService.get_project_root(project_id)
        return root / _MEMORY_FILE

    @staticmethod
    def _load(project_id: str) -> list[dict[str, Any]]:
        p = LearnService._memory_path(project_id)
        if p.exists():
            data = FileIO.read_json(p)
            return data.get("patterns", [])
        return []

    @staticmethod
    def _save(project_id: str, patterns: list[dict[str, Any]]) -> None:
        p = LearnService._memory_path(project_id)
        FileIO.write_json(p, {"patterns": patterns})

    @staticmethod
    def list_patterns(project_id: str) -> list[dict[str, Any]]:
        return LearnService._load(project_id)

    @staticmethod
    def add_pattern(
        project_id: str,
        pattern_type: str,
        description: str,
        category: str | None = None,
        importance: str | None = None,
    ) -> bool:
        patterns = LearnService._load(project_id)

        # Dedup check
        for p in patterns:
            if p["pattern_type"] == pattern_type and p["description"] == description:
                return True  # duplicated

        now = datetime.now(timezone.utc).isoformat()
        patterns.append({
            "pattern_type": pattern_type,
            "description": description,
            "category": category,
            "importance": importance,
            "learned_at": now,
        })
        LearnService._save(project_id, patterns)
        return False  # not duplicated
