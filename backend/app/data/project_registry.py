"""Project registry store — manages ~/.webnovel-app/project_registry.json."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import ensure_app_data_dir
from app.core.logger import get_logger
from app.data.file_io import FileIO

logger = get_logger(__name__)

_REGISTRY_FILE = "project_registry.json"


@dataclass(frozen=True)
class ProjectInfo:
    """Immutable project metadata."""

    id: str
    name: str
    root_path: str
    genre: str = ""
    created_at: str = ""
    updated_at: str = ""
    total_chapters: int = 0
    written_chapters: int = 0
    target_words: int = 0


class ProjectRegistryStore:
    """CRUD for the project registry file.

    The registry JSON structure (list-based, matching actual file format):

    .. code-block:: json

       {
         "projects": [
           {
             "id": "...", "title": "...", "root_path": "...", "genre": "...",
             "target_words": 0, "target_chapters": 0,
             "created_at": "...", "last_opened": "..."
           }
         ],
         "active_project_id": "..."
       }
    """

    def __init__(self, registry_path: Path | None = None) -> None:
        self._explicit_path = registry_path

    @property
    def _registry_path(self) -> Path:
        """Lazily resolve registry path so patches to ensure_app_data_dir take effect."""
        if self._explicit_path is not None:
            return self._explicit_path
        return ensure_app_data_dir() / _REGISTRY_FILE

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _read_registry(self) -> dict[str, Any]:
        if self._registry_path.exists():
            return FileIO.read_json(self._registry_path)
        return {"projects": []}

    def _write_registry(self, data: dict[str, Any]) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        FileIO.write_json(self._registry_path, data)

    @staticmethod
    def _to_info(d: dict[str, Any]) -> ProjectInfo:
        """Convert a raw registry dict to ProjectInfo. Handles both 'title' and 'name' keys."""
        return ProjectInfo(
            id=d["id"],
            name=d.get("title") or d.get("name", ""),
            root_path=d["root_path"],
            genre=d.get("genre", ""),
            created_at=d.get("created_at", ""),
            updated_at=d.get("last_opened") or d.get("updated_at", ""),
            total_chapters=d.get("total_chapters", 0),
            written_chapters=d.get("written_chapters", 0),
            target_words=d.get("target_words", 0),
        )

    @staticmethod
    def _from_info(info: ProjectInfo) -> dict[str, Any]:
        """Convert ProjectInfo to raw registry dict."""
        return {
            "id": info.id,
            "title": info.name,
            "root_path": info.root_path,
            "genre": info.genre,
            "target_words": info.target_words,
            "target_chapters": info.total_chapters,
            "created_at": info.created_at,
            "last_opened": info.updated_at,
        }

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_projects(self) -> list[ProjectInfo]:
        """List all registered projects."""
        data = self._read_registry()
        projects = [self._to_info(v) for v in data.get("projects", [])]
        logger.debug("Listed %d registered projects", len(projects))
        return projects

    async def get_project(self, project_id: str) -> ProjectInfo | None:
        """Get a project by ID."""
        data = self._read_registry()
        for p in data.get("projects", []):
            if p["id"] == project_id:
                return self._to_info(p)
        return None

    def get_project_sync(self, project_id: str) -> ProjectInfo | None:
        """Synchronous version of get_project."""
        data = self._read_registry()
        for p in data.get("projects", []):
            if p["id"] == project_id:
                return self._to_info(p)
        return None

    async def create_project(self, project: ProjectInfo) -> ProjectInfo:
        """Register a new project. Assigns an ID and timestamps if empty."""
        data = self._read_registry()

        now = datetime.now(timezone.utc).isoformat()
        final = ProjectInfo(
            id=project.id or str(uuid.uuid4()),
            name=project.name,
            root_path=project.root_path,
            genre=project.genre,
            created_at=project.created_at or now,
            updated_at=project.updated_at or now,
            total_chapters=project.total_chapters,
            written_chapters=project.written_chapters,
        )

        data.setdefault("projects", []).append(self._from_info(final))
        self._write_registry(data)
        logger.info("Created project: %s (%s)", final.name, final.id)
        return final

    async def update_project(
        self,
        project_id: str,
        updates: dict[str, Any],
    ) -> ProjectInfo:
        """Update a project's fields. Raises KeyError if not found."""
        data = self._read_registry()
        projects = data.get("projects", [])
        idx = None
        for i, p in enumerate(projects):
            if p["id"] == project_id:
                idx = i
                break
        if idx is None:
            raise KeyError(f"Project not found: {project_id}")

        existing = projects[idx]
        # Apply updates (only known fields)
        allowed = {"id", "title", "name", "root_path", "genre", "target_words", "target_chapters", "created_at", "last_opened", "updated_at", "total_chapters", "written_chapters"}
        for k, v in updates.items():
            if k in allowed:
                existing[k] = v
        existing["last_opened"] = datetime.now(timezone.utc).isoformat()
        projects[idx] = existing
        self._write_registry(data)
        logger.info("Updated project: %s", project_id)
        return self._to_info(existing)

    async def delete_project(self, project_id: str) -> bool:
        """Remove a project from the registry (does not delete files)."""
        data = self._read_registry()
        projects = data.get("projects", [])
        before = len(projects)
        data["projects"] = [p for p in projects if p["id"] != project_id]
        if len(data["projects"]) < before:
            self._write_registry(data)
            logger.info("Deleted project from registry: %s", project_id)
            return True
        return False

    async def set_active_project(self, project_id: str) -> bool:
        """Set the active project. Returns False if project not found."""
        data = self._read_registry()
        for p in data.get("projects", []):
            if p["id"] == project_id:
                data["active_project_id"] = project_id
                self._write_registry(data)
                logger.info("Set active project: %s", project_id)
                return True
        return False

    async def get_active_project_id(self) -> str | None:
        """Get the active project ID."""
        data = self._read_registry()
        return data.get("active_project_id")
