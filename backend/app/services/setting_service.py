"""Setting management service — read/write setting files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.data.file_io import FileIO
from app.services.project_service import ProjectService

# Map setting_type to file path relative to project root
SETTING_FILES = {
    "world": "设定集/世界观.md",
    "power-system": "设定集/力量体系.md",
    "protagonist": "设定集/主角卡.md",
    "female-lead": "设定集/女主卡.md",
    "protagonist-group": "设定集/主角组.md",
    "antagonist": "设定集/反派设计.md",
    "golden-finger": "设定集/金手指.md",
    "master-outline": "大纲/总纲.md",
}


class SettingService:
    """Read and write setting files."""

    @staticmethod
    def get_setting(project_id: str, setting_type: str) -> tuple[str, str | None]:
        root = ProjectService.get_project_root(project_id)
        rel_path = SETTING_FILES.get(setting_type)
        if not rel_path:
            # Try direct path lookup for custom types
            rel_path = f"设定集/{setting_type}.md"

        path = root / rel_path
        if path.exists():
            stat = path.stat()
            from datetime import datetime, timezone
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            return FileIO.read_markdown(path), mtime
        return "", None

    @staticmethod
    def save_setting(project_id: str, setting_type: str, content: str) -> None:
        root = ProjectService.get_project_root(project_id)
        rel_path = SETTING_FILES.get(setting_type)
        if not rel_path:
            rel_path = f"设定集/{setting_type}.md"
        path = root / rel_path
        FileIO.write_markdown(path, content)
