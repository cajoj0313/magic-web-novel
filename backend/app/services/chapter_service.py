"""Chapter management service — list, get, save."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.error_codes import ErrorCode
from app.data.file_io import FileIO
from app.services.project_service import ProjectService

# Pattern: 正文/第0005章-xxx.md
CHAPTER_RE = re.compile(r"^第(\d{4})章-(.+?)\.md$")


def _word_count(content: str) -> int:
    """Count non-whitespace characters."""
    return len(content.replace(" ", "").replace("\n", "").replace("\r", ""))


def _iso_time(timestamp: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


class ChapterService:
    """Chapter CRUD operations."""

    @staticmethod
    async def list_chapters(project_id: str, volume: int | None = None) -> list[dict[str, Any]]:
        root = ProjectService.get_project_root(project_id)
        chapter_dir = root / "正文"
        if not chapter_dir.exists():
            return []

        chapters: dict[int, dict[str, Any]] = {}

        for f in sorted(chapter_dir.iterdir()):
            if f.suffix != ".md":
                continue
            m = CHAPTER_RE.match(f.name)
            if not m:
                continue
            num = int(m.group(1))
            title = m.group(2)
            stat = f.stat()
            content = f.read_text(encoding="utf-8")
            wc = _word_count(content)
            chapters[num] = {
                "chapter_num": num,
                "title": title,
                "word_count": wc,
                "status": "written",
                "review_score": None,
                "last_updated": _iso_time(stat.st_mtime),
            }

        # Also check state.json for total chapters
        state_path = root / ".webnovel" / "state.json"
        total = 0
        if state_path.exists():
            try:
                state = FileIO.read_json(state_path)
                total = state.get("total_chapters", 0)
            except Exception:
                pass

        # Fill unwritten chapters as placeholders
        result = []
        for i in range(1, max(total, len(chapters)) + 1):
            if i in chapters:
                result.append(chapters[i])
            else:
                result.append({
                    "chapter_num": i,
                    "title": None,
                    "word_count": 0,
                    "status": "unwritten",
                    "review_score": None,
                    "last_updated": None,
                })
        return result

    @staticmethod
    def get_chapter(project_id: str, chapter_num: int) -> dict[str, Any]:
        root = ProjectService.get_project_root(project_id)
        chapter_dir = root / "正文"

        if not chapter_dir.exists():
            raise ValueError(f"Chapter {chapter_num} not found")

        # Find file by chapter number
        for f in chapter_dir.iterdir():
            if f.suffix != ".md":
                continue
            m = CHAPTER_RE.match(f.name)
            if m and int(m.group(1)) == chapter_num:
                content = FileIO.read_markdown(f)
                stat = f.stat()
                title = m.group(2)
                return {
                    "chapter_num": chapter_num,
                    "title": title,
                    "content": content,
                    "word_count": _word_count(content),
                    "last_updated": _iso_time(stat.st_mtime),
                }
        raise ValueError(f"Chapter {chapter_num} not found")

    @staticmethod
    def save_chapter(project_id: str, chapter_num: int, content: str) -> int:
        root = ProjectService.get_project_root(project_id)
        chapter_dir = root / "正文"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        # Find existing file or create new one
        existing = None
        for f in chapter_dir.iterdir():
            if f.suffix != ".md":
                continue
            m = CHAPTER_RE.match(f.name)
            if m and int(m.group(1)) == chapter_num:
                existing = f
                break

        wc = _word_count(content)
        if existing:
            FileIO.write_markdown(existing, content)
            ChapterService._update_word_count(root, chapter_num, wc)
            return wc
        else:
            # Create new chapter file with placeholder title
            filename = f"第{chapter_num:04d}章-未命名.md"
            path = chapter_dir / filename
            FileIO.write_markdown(path, content)
            return wc

    @staticmethod
    def _update_word_count(root: Path, chapter_num: int, wc: int) -> None:
        state_path = root / ".webnovel" / "state.json"
        if state_path.exists():
            try:
                state = FileIO.read_json(state_path)
                counts = state.setdefault("chapter_word_counts", {})
                key = str(chapter_num)
                old_wc = counts.get(key, 0)
                state["word_count"] = state.get("word_count", 0) - old_wc + wc
                counts[key] = wc
                FileIO.write_json(state_path, state)
            except Exception:
                pass
