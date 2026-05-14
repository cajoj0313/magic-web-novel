"""Project management service — CRUD, overview, preflight."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.core.error_codes import ErrorCode
from app.data.file_io import FileIO
from app.data.project_registry import ProjectInfo, ProjectRegistryStore

_registry = ProjectRegistryStore()


class ProjectService:
    """Manage novel projects."""

    @staticmethod
    async def list_projects() -> tuple[list[dict[str, Any]], str | None]:
        projects = await _registry.list_projects()
        active_id = await _registry.get_active_project_id()
        result = []
        for p in projects:
            root = p.root_path
            # Try to read word_count from state.json
            state_path = Path(root) / ".webnovel" / "state.json"
            progress = 0
            if state_path.exists():
                try:
                    state = FileIO.read_json(state_path)
                    progress = state.get("word_count", 0)
                except Exception:
                    pass
            result.append({
                "id": p.id,
                "title": p.name,
                "genre": p.genre or "unknown",
                "progress": progress,
                "last_updated": p.updated_at or None,
            })
        return result, active_id

    @staticmethod
    async def create_project(
        root_path: str,
        title: str,
        genre: str,
        target_words: int = 0,
        target_chapters: int = 0,
    ) -> tuple[str, str]:
        # Validate root path
        p = Path(root_path)
        if not p.exists():
            raise ValueError(f"项目根目录不存在: {root_path}")
        # Check for state.json (project validation)
        state_path = p / ".webnovel" / "state.json"
        if not state_path.exists():
            raise ValueError(f"项目缺少 .webnovel/state.json: {root_path}")

        project = ProjectInfo(
            id="",  # Will be assigned by store
            name=title or p.name,
            root_path=str(p.resolve()),
            genre=genre,
            target_words=target_words,
            total_chapters=target_chapters,
        )
        created = await _registry.create_project(project)
        return created.id, created.name

    @staticmethod
    async def delete_project(project_id: str) -> bool:
        return await _registry.delete_project(project_id)

    @staticmethod
    async def switch_project(project_id: str) -> bool:
        project = await _registry.get_project(project_id)
        if not project:
            raise ValueError(f"项目 {project_id} 不存在")
        await _registry.set_active_project(project_id)
        return True

    @staticmethod
    async def get_project(project_id: str) -> ProjectInfo | None:
        return await _registry.get_project(project_id)

    @staticmethod
    def get_project_root(project_id: str) -> Path:
        project = _registry.get_project_sync(project_id)
        if not project:
            raise ValueError(f"项目 {project_id} 不存在")
        return Path(project.root_path)

    @staticmethod
    def get_overview(project_id: str) -> dict[str, Any]:
        root = ProjectService.get_project_root(project_id)
        state_path = root / ".webnovel" / "state.json"

        state: dict = {}
        if state_path.exists():
            state = FileIO.read_json(state_path)

        # Count chapters
        chapter_dir = root / "正文"
        chapters = []
        if chapter_dir.exists():
            chapters = [f for f in chapter_dir.iterdir() if f.suffix == ".md"]

        total_words = state.get("word_count", 0)
        target_chapters = state.get("total_chapters", 0)

        return {
            "title": state.get("title", ""),
            "genre": state.get("genre", "unknown"),
            "current_chapter": len(chapters),
            "total_chapters": target_chapters or len(chapters),
            "total_words": total_words,
            "review_status": state.get("review_status", "unknown"),
            "last_updated": state.get("last_updated"),
        }
