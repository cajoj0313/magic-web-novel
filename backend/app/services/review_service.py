"""ReviewService — single chapter review flow.

Loads chapter content → builds review prompt → calls LLM → generates report → persists.
Uses the same PromptBuilder as ChapterOrchestrator for consistent review logic.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.data.file_io import FileIO
from app.services.chapter_service import ChapterService
from app.services.prompt_builder import PromptBuilder
from app.services.task_manager import task_manager

logger = get_logger(__name__)

# Review report storage directory per project
_REVIEW_DIR = "审查报告"


class ReviewService:
    """Single chapter review flow (LLM-based)."""

    def __init__(
        self,
        task_id: str,
        project_id: str,
        chapter_num: int,
        project_root: Path,
        caller,  # LLMCaller protocol
    ) -> None:
        self.task_id = task_id
        self.project_id = project_id
        self.chapter_num = chapter_num
        self.project_root = project_root
        self.caller = caller

    async def execute(self) -> dict[str, Any]:
        """Execute review flow: load content → call LLM → save report."""
        total_start = time.monotonic()

        task_manager.emit(self.task_id, "task_start", {
            "task_id": self.task_id,
            "type": "review",
            "chapter_num": self.chapter_num,
            "total_steps": 3,
            "mode": "review",
        })

        # Step 1: Load chapter content
        task_manager.emit(self.task_id, "step_start", {
            "task_id": self.task_id,
            "step_number": 1,
            "step_name": "加载章节",
            "estimated_seconds": 2,
        })
        try:
            chapter = ChapterService.get_chapter(self.project_id, self.chapter_num)
            content = chapter["content"]
            title = chapter["title"]
        except ValueError as e:
            task_manager.emit(self.task_id, "task_failed", {
                "task_id": self.task_id,
                "failed_step": 1,
                "error_message": str(e),
                "recoverable": False,
            })
            return {"status": "failed", "error": str(e)}

        task_manager.emit(self.task_id, "step_complete", {
            "task_id": self.task_id,
            "step_number": 1,
            "step_name": "加载章节",
            "elapsed_ms": 100,
            "output_path": "",
            "preview": {"word_count": chapter["word_count"], "title": title},
        })

        # Step 2: Call LLM for review
        task_manager.emit(self.task_id, "step_start", {
            "task_id": self.task_id,
            "step_number": 2,
            "step_name": "审查分析",
            "estimated_seconds": 20,
        })
        step2_start = time.monotonic()

        contract = PromptBuilder.load_contract_tree(self.project_root, self.chapter_num)
        setting_path = self.project_root / "设定集" / "世界观.md"
        setting_context = ""
        if setting_path.exists():
            setting_context = FileIO.read_markdown(setting_path)

        system_prompt, user_prompt = PromptBuilder.build_review_prompt(
            chapter_content=content,
            chapter_num=self.chapter_num,
            contract_tree=contract,
            setting_context=setting_context,
        )

        try:
            response = await self.caller(
                system=system_prompt,
                user=user_prompt,
                max_tokens=8192,
                temperature=0.1,
            )
        except Exception as e:
            task_manager.emit(self.task_id, "task_failed", {
                "task_id": self.task_id,
                "failed_step": 2,
                "error_message": str(e),
                "recoverable": True,
            })
            return {"status": "failed", "error": str(e)}

        # Parse review JSON
        review_json = self._extract_json(response)
        review_results = json.loads(review_json) if review_json else {"issues": [], "summary": response}

        step2_elapsed = int((time.monotonic() - step2_start) * 1000)
        issues = review_results.get("issues", [])
        blocking = [i for i in issues if i.get("blocking", False)]

        task_manager.emit(self.task_id, "step_complete", {
            "task_id": self.task_id,
            "step_number": 2,
            "step_name": "审查分析",
            "elapsed_ms": step2_elapsed,
            "output_path": "",
            "preview": {
                "issues_count": len(issues),
                "blocking": len(blocking) > 0,
            },
        })

        # Step 3: Save report
        task_manager.emit(self.task_id, "step_start", {
            "task_id": self.task_id,
            "step_number": 3,
            "step_name": "保存报告",
            "estimated_seconds": 2,
        })
        step3_start = time.monotonic()

        # Save JSON report to tmp
        tmp_dir = self.project_root / ".webnovel" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        report_id = f"review_ch{self.chapter_num}_{int(time.time())}"
        json_path = tmp_dir / f"{report_id}.json"
        FileIO.write_json(json_path, review_results)

        # Also save markdown report
        review_dir = self.project_root / _REVIEW_DIR
        review_dir.mkdir(parents=True, exist_ok=True)
        md_path = review_dir / f"第{self.chapter_num}章审查报告.md"
        md_content = self._format_report_md(review_results, self.chapter_num)
        FileIO.write_markdown(md_path, md_content)

        step3_elapsed = int((time.monotonic() - step3_start) * 1000)
        task_manager.emit(self.task_id, "step_complete", {
            "task_id": self.task_id,
            "step_number": 3,
            "step_name": "保存报告",
            "elapsed_ms": step3_elapsed,
            "output_path": str(md_path),
            "preview": {"report_id": report_id},
        })

        total_elapsed_ms = int((time.monotonic() - total_start) * 1000)
        task_manager.emit(self.task_id, "task_complete", {
            "task_id": self.task_id,
            "total_elapsed_ms": total_elapsed_ms,
            "final_status": "completed",
            "result_summary": f"第{self.chapter_num}章审查完成，{len(issues)} 个问题",
        })

        ts = task_manager.get_task(self.task_id)
        if ts:
            ts.status = "completed"
            ts.current_step = 3

        return {
            "status": "completed",
            "report_id": report_id,
            "issues_count": len(issues),
            "blocking_count": len(blocking),
            "total_elapsed_ms": total_elapsed_ms,
        }

    @staticmethod
    def list_review_history(project_root: Path, chapter_num: int) -> list[dict[str, Any]]:
        """List all review reports for a chapter."""
        review_dir = project_root / _REVIEW_DIR
        if not review_dir.exists():
            return []

        results = []
        # Match files like 第5章审查报告.md or 第0005章审查报告.md
        for f in sorted(review_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix != ".md":
                continue
            name = f.stem
            # Simple pattern matching
            if f"第{chapter_num}章审查报告" in name or f"第{chapter_num:04d}章审查报告" in name:
                stat = f.stat()
                results.append({
                    "report_id": f.stem,
                    "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
                    "issues_count": 0,  # Would need to parse the file to get count
                    "blocking_count": 0,
                    "overall_score": None,
                })

        # Also check tmp for JSON reports
        tmp_dir = project_root / ".webnovel" / "tmp"
        if tmp_dir.exists():
            for f in sorted(tmp_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.suffix != ".json":
                    continue
                if f"review_ch{chapter_num}" in f.stem or f"review_ch{chapter_num:04d}" in f.stem:
                    try:
                        data = FileIO.read_json(f)
                        issues = data.get("issues", [])
                        stat = f.stat()
                        results.append({
                            "report_id": f.stem,
                            "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
                            "issues_count": len(issues),
                            "blocking_count": len([i for i in issues if i.get("blocking", False)]),
                            "overall_score": None,
                        })
                    except Exception:
                        pass

        return results

    @staticmethod
    def get_report(project_root: Path, report_id: str) -> dict[str, Any]:
        """Get a specific review report."""
        # Try tmp JSON first
        tmp_dir = project_root / ".webnovel" / "tmp"
        json_path = tmp_dir / f"{report_id}.json"
        if json_path.exists():
            data = FileIO.read_json(json_path)
            return data

        # Try markdown report
        review_dir = project_root / _REVIEW_DIR
        md_path = review_dir / f"{report_id}.md"
        if md_path.exists():
            content = FileIO.read_markdown(md_path)
            return {"raw_markdown": content}

        # Try glob patterns
        for dir_path in [tmp_dir, review_dir]:
            if dir_path.exists():
                for f in dir_path.iterdir():
                    if report_id in f.stem or report_id in f.name:
                        if f.suffix == ".json":
                            return FileIO.read_json(f)
                        elif f.suffix == ".md":
                            return {"raw_markdown": FileIO.read_markdown(f)}

        return {}

    @staticmethod
    def _format_report_md(review_results: dict, chapter_num: int) -> str:
        """Format review results as markdown report."""
        issues = review_results.get("issues", [])
        summary = review_results.get("summary", "")

        lines = [
            f"# 第 {chapter_num} 章审查报告",
            "",
            f"**审查时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**问题总数**: {len(issues)}",
            f"**阻断项**: {sum(1 for i in issues if i.get('blocking', False))}",
            "",
            "---",
            "",
        ]

        if summary:
            lines.extend(["## 审查摘要", "", summary, "", "---", ""])

        if issues:
            lines.append("## 问题清单")
            lines.append("")
            lines.append("| # | 严重度 | 类别 | 位置 | 描述 | 证据 | 修复建议 | 阻断 |")
            lines.append("|---|--------|------|------|------|------|----------|------|")
            for i, issue in enumerate(issues, 1):
                severity = issue.get("severity", "unknown")
                category = issue.get("category", "")
                location = issue.get("location", "")
                description = issue.get("description", "")
                evidence = issue.get("evidence", "")
                fix_hint = issue.get("fix_hint", "")
                blocking = "是" if issue.get("blocking", False) else "否"
                lines.append(
                    f"| {i} | {severity} | {category} | {location} | "
                    f"{description} | {evidence} | {fix_hint} | {blocking} |"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """Extract JSON from LLM response."""
        start = text.find("```json")
        if start >= 0:
            start += 7
            end = text.find("```", start)
            if end > 0:
                return text[start:end].strip()
        start = text.find("```")
        if start >= 0:
            start += 3
            end = text.find("```", start)
            if end > 0:
                return text[start:end].strip()
        text = text.strip()
        if text.startswith("{"):
            return text
        return None
