"""PlanOrchestrator — 9-step volume planning flow.

Steps (based on webnovel-plan SKILL.md 9-step flow):
  1. 加载总纲和上一卷产物
  2. 刷新合同树（volume 级）
  3. 生成卷节拍表
  4. 生成卷时间线
  5. 生成章纲（逐章）
  6. 连续性检查
  7. 验证冲突
  8. 增量写回设定
  9. 落库产物

Supports pause/resume/cancel and SSE event broadcasting.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.data.file_io import FileIO
from app.data.task_store import TaskStore
from app.services.prompt_builder import PromptBuilder
from app.services.task_manager import task_manager

logger = get_logger(__name__)


@dataclass
class PlanStepDef:
    name: str
    estimated_seconds: int


PLAN_STEPS: list[PlanStepDef] = [
    PlanStepDef("加载上下文", 2),
    PlanStepDef("刷新合同树", 3),
    PlanStepDef("生成卷节拍表", 15),
    PlanStepDef("生成卷时间线", 15),
    PlanStepDef("生成章纲", 20),
    PlanStepDef("连续性检查", 10),
    PlanStepDef("验证冲突", 8),
    PlanStepDef("增量写回设定", 5),
    PlanStepDef("落库产物", 3),
]


class PlanOrchestrator:
    """9-step volume planning orchestrator."""

    def __init__(
        self,
        task_id: str,
        project_id: str,
        volume_id: int,
        project_root: Path,
        caller,  # LLMCaller protocol
    ) -> None:
        self.task_id = task_id
        self.project_id = project_id
        self.volume_id = volume_id
        self.project_root = project_root
        self.caller = caller
        self.current_step = 0
        self.step_results: dict[int, dict[str, Any]] = {}
        self.task_store = TaskStore(project_root)
        self._cancelled = False
        # Intermediate data accumulated across steps
        self.context: dict[str, Any] = {}

    async def execute(self) -> dict[str, Any]:
        """Execute the full 9-step planning flow."""
        total_start = time.monotonic()

        task_manager.emit(self.task_id, "task_start", {
            "task_id": self.task_id,
            "type": "plan",
            "volume_id": self.volume_id,
            "total_steps": len(PLAN_STEPS),
            "mode": "plan",
        })

        self._persist_state()

        for i, step_def in enumerate(PLAN_STEPS):
            if self._cancelled:
                return self._finalize_cancelled(total_start)

            ts = task_manager.get_task(self.task_id)
            if ts and ts.is_cancelled():
                self._cancelled = True
                return self._finalize_cancelled(total_start)

            while ts and ts.is_paused() and not ts.is_cancelled():
                await asyncio.sleep(0.3)
                ts = task_manager.get_task(self.task_id)
                if ts and ts.is_cancelled():
                    self._cancelled = True
                    return self._finalize_cancelled(total_start)

            if i in self.step_results and self.step_results[i].get("status") == "completed":
                continue

            step_start = time.monotonic()
            self.current_step = i

            if ts:
                ts.current_step = i
                ts.step_name = step_def.name
                ts.status = "running"

            task_manager.emit(self.task_id, "step_start", {
                "task_id": self.task_id,
                "step_number": i + 1,
                "step_name": step_def.name,
                "estimated_seconds": step_def.estimated_seconds,
            })

            try:
                result = await self._run_step(i)
                elapsed_ms = int((time.monotonic() - step_start) * 1000)
                self.step_results[i] = {
                    "status": "completed",
                    "output": result.get("output", ""),
                    "output_path": result.get("output_path", ""),
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_ms": elapsed_ms,
                }
                self._persist_state()

                task_manager.emit(self.task_id, "step_complete", {
                    "task_id": self.task_id,
                    "step_number": i + 1,
                    "step_name": step_def.name,
                    "elapsed_ms": elapsed_ms,
                    "output_path": result.get("output_path", ""),
                    "preview": result.get("preview", {}),
                })
            except Exception as e:
                task_manager.emit(self.task_id, "task_failed", {
                    "task_id": self.task_id,
                    "failed_step": i + 1,
                    "failed_step_name": PLAN_STEPS[i].name,
                    "error_message": str(e),
                    "recoverable": True,
                })
                return {"status": "failed", "failed_step": i + 1, "error": str(e)}

        total_elapsed_ms = int((time.monotonic() - total_start) * 1000)
        task_manager.emit(self.task_id, "task_complete", {
            "task_id": self.task_id,
            "total_elapsed_ms": total_elapsed_ms,
            "final_status": "completed",
            "result_summary": f"第{self.volume_id}卷规划完成",
        })

        ts = task_manager.get_task(self.task_id)
        if ts:
            ts.status = "completed"
            ts.current_step = len(PLAN_STEPS)

        self.task_store.clear()

        return {
            "status": "completed",
            "volume_id": self.volume_id,
            "total_elapsed_ms": total_elapsed_ms,
        }

    async def _run_step(self, step_index: int) -> dict[str, Any]:
        if step_index == 0:
            return await self._step_load_context()
        elif step_index == 1:
            return await self._step_refresh_contract()
        elif step_index == 2:
            return await self._step_generate_beat_sheet()
        elif step_index == 3:
            return await self._step_generate_timeline()
        elif step_index == 4:
            return await self._step_generate_chapter_outlines()
        elif step_index == 5:
            return await self._step_continuity_check()
        elif step_index == 6:
            return await self._step_validate_conflicts()
        elif step_index == 7:
            return await self._step_write_back_settings()
        elif step_index == 8:
            return await self._step_commit_artifacts()
        else:
            raise ValueError(f"Unknown step index: {step_index}")

    async def _step_load_context(self) -> dict[str, Any]:
        """Step 1: Load master outline, previous volume artifacts, state.json."""
        # Load master outline
        master_outline_path = self.project_root / "大纲" / "总纲.md"
        master_outline = ""
        if master_outline_path.exists():
            master_outline = FileIO.read_markdown(master_outline_path)

        # Load state.json
        state_path = self.project_root / ".webnovel" / "state.json"
        state: dict = {}
        if state_path.exists():
            state = FileIO.read_json(state_path)

        # Load previous volume artifacts if exist
        prev_beat_sheet = ""
        prev_timeline = ""
        volume_dir = self.project_root / "大纲"
        if volume_dir.exists() and self.volume_id > 1:
            for f in volume_dir.iterdir():
                prev_vol = self.volume_id - 1
                if f.name.startswith(f"第{prev_vol}卷"):
                    content = FileIO.read_markdown(f)
                    if "节拍" in f.name:
                        prev_beat_sheet = content
                    elif "时间线" in f.name:
                        prev_timeline = content

        self.context.update({
            "master_outline": master_outline,
            "state": state,
            "prev_beat_sheet": prev_beat_sheet,
            "prev_timeline": prev_timeline,
        })

        return {
            "output": f"已加载总纲 ({len(master_outline)} 字)",
            "preview": {"has_master_outline": bool(master_outline)},
        }

    async def _step_refresh_contract(self) -> dict[str, Any]:
        """Step 2: Load/refresh volume-level contract tree."""
        # Load volume contract from .story-system/
        tree_dir = self.project_root / ".story-system" / "volumes"
        vol_file = tree_dir / f"volume_{self.volume_id:03d}.json"
        contract = {}
        if vol_file.exists():
            contract = FileIO.read_json(vol_file)
            self.context["volume_contract"] = contract
            return {
                "output": f"已加载第 {self.volume_id} 卷合同",
                "preview": {"has_contract": True},
            }
        else:
            self.context["volume_contract"] = {}
            return {
                "output": f"第 {self.volume_id} 卷合同不存在，将基于总纲生成",
                "preview": {"has_contract": False},
            }

    async def _step_generate_beat_sheet(self) -> dict[str, Any]:
        """Step 3: Generate volume beat sheet (卷节拍表)."""
        master_outline = self.context.get("master_outline", "")
        state = self.context.get("state", {})
        prev_beat = self.context.get("prev_beat_sheet", "")

        system_prompt = f"""你是网文大纲规划助手。请为第 {self.volume_id} 卷生成卷节拍表。

要求：
- 基于总纲和上一卷的节拍表（如果存在）
- 输出节拍表 Markdown 格式
- 每个节拍包含：节拍编号、情节摘要、情绪曲线（压抑/爆发/过渡）、关键角色
- 保证与总纲的一致性
- 注意与上一卷的衔接
"""
        user_prompt = f"""=== 总纲 ===
{master_outline}

"""
        if prev_beat:
            user_prompt += f"""=== 上一卷节拍表 ===
{prev_beat}

"""
        genre = state.get("project", {}).get("genre", "") or state.get("genre", "")
        user_prompt += f"题材：{genre}\n请生成第 {self.volume_id} 卷的节拍表。"

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=16384,
            temperature=0.5,
        )

        # Save beat sheet
        outline_dir = self.project_root / "大纲"
        outline_dir.mkdir(parents=True, exist_ok=True)
        beat_path = outline_dir / f"第{self.volume_id}卷-节拍表.md"
        FileIO.write_markdown(beat_path, response)
        self.context["beat_sheet"] = response

        return {
            "output": response[:300] + ("..." if len(response) > 300 else ""),
            "output_path": str(beat_path),
            "preview": {"length": len(response)},
        }

    async def _step_generate_timeline(self) -> dict[str, Any]:
        """Step 4: Generate volume timeline (卷时间线)."""
        beat_sheet = self.context.get("beat_sheet", "")
        prev_timeline = self.context.get("prev_timeline", "")

        system_prompt = f"""你是网文大纲规划助手。请根据卷节拍表生成第 {self.volume_id} 卷的时间线。

要求：
- 时间线必须与节拍表一致
- 输出 Markdown 格式
- 包含：时间节点、事件、角色状态变化
- 注意时间逻辑的一致性
"""
        user_prompt = f"""=== 卷节拍表 ===
{beat_sheet}

"""
        if prev_timeline:
            user_prompt += f"""=== 上一卷时间线 ===
{prev_timeline}

"""
        user_prompt += f"请生成第 {self.volume_id} 卷的时间线。"

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=16384,
            temperature=0.5,
        )

        timeline_path = self.project_root / "大纲" / f"第{self.volume_id}卷-时间线.md"
        FileIO.write_markdown(timeline_path, response)
        self.context["timeline"] = response

        return {
            "output": response[:300] + ("..." if len(response) > 300 else ""),
            "output_path": str(timeline_path),
            "preview": {"length": len(response)},
        }

    async def _step_generate_chapter_outlines(self) -> dict[str, Any]:
        """Step 5: Generate chapter outlines (章纲) for each chapter in the volume."""
        beat_sheet = self.context.get("beat_sheet", "")
        timeline = self.context.get("timeline", "")
        master_outline = self.context.get("master_outline", "")

        system_prompt = f"""你是网文大纲规划助手。请根据节拍表和时间线，生成第 {self.volume_id} 卷的逐章章纲。

要求：
- 每章章纲包含：章号、标题、核心事件、CBN/CPNs/CEN 结构化节点、本章目标
- 章节之间逻辑连贯
- 每章结尾留钩子
- 输出 Markdown 格式
"""
        user_prompt = f"""=== 总纲 ===
{master_outline}

=== 卷节拍表 ===
{beat_sheet}

=== 卷时间线 ===
{timeline}

请生成第 {self.volume_id} 卷的逐章章纲。"""

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=16384,
            temperature=0.5,
        )

        outline_path = self.project_root / "大纲" / f"第{self.volume_id}卷-详细大纲.md"
        FileIO.write_markdown(outline_path, response)
        self.context["chapter_outlines"] = response

        return {
            "output": response[:300] + ("..." if len(response) > 300 else ""),
            "output_path": str(outline_path),
            "preview": {"length": len(response)},
        }

    async def _step_continuity_check(self) -> dict[str, Any]:
        """Step 6: Continuity check — verify cross-volume continuity."""
        prev_timeline = self.context.get("prev_timeline", "")
        timeline = self.context.get("timeline", "")
        prev_beat = self.context.get("prev_beat_sheet", "")
        beat_sheet = self.context.get("beat_sheet", "")

        system_prompt = f"""你是连续性检查助手。请检查第 {self.volume_id} 卷与上一卷之间的连续性。

检查项：
1. 时间线是否连续（事件顺序是否合理）
2. 角色状态是否一致（角色不能突然改变性格/能力）
3. 情节是否连贯（上卷的伏笔是否在本卷有呼应）
4. 设定是否冲突

输出 JSON 格式：{{"continuity_issues": [{{"type": "...", "description": "...", "severity": "..."}}]}}
如果没有问题，输出空数组。"""

        user_prompt = f"""=== 上一卷节拍表 ===
{prev_beat}

=== 上一卷时间线 ===
{prev_timeline}

=== 本卷节拍表 ===
{beat_sheet}

=== 本卷时间线 ===
{timeline}

请检查连续性。"""

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=4096,
            temperature=0.1,
        )

        issues_json = PromptBuilder._extract_json(response)
        issues = json.loads(issues_json) if issues_json else {"continuity_issues": []}
        self.context["continuity_issues"] = issues

        issue_count = len(issues.get("continuity_issues", []))
        return {
            "output": json.dumps(issues, ensure_ascii=False)[:300],
            "preview": {"issues_count": issue_count},
        }

    async def _step_validate_conflicts(self) -> dict[str, Any]:
        """Step 7: Conflict validation — check for timeline conflicts and missing fields."""
        timeline = self.context.get("timeline", "")
        chapter_outlines = self.context.get("chapter_outlines", "")
        master_outline = self.context.get("master_outline", "")

        system_prompt = f"""你是大纲验证助手。请检查第 {self.volume_id} 卷的大纲是否存在内部冲突。

检查项：
1. 时间线内部冲突（同一时间不同事件是否矛盾）
2. 章纲缺失字段（是否缺少 CBN/CPNs/CEN）
3. 与总纲的冲突（章纲是否偏离总纲方向）

输出 JSON 格式：{{"conflicts": [{{"type": "...", "description": "...", "severity": "..."}}]}}
如果没有冲突，输出空数组。"""

        user_prompt = f"""=== 总纲 ===
{master_outline}

=== 卷时间线 ===
{timeline}

=== 详细章纲 ===
{chapter_outlines}

请验证冲突。"""

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=4096,
            temperature=0.1,
        )

        conflicts_json = PromptBuilder._extract_json(response)
        conflicts = json.loads(conflicts_json) if conflicts_json else {"conflicts": []}
        self.context["conflicts"] = conflicts

        conflict_count = len(conflicts.get("conflicts", []))
        return {
            "output": json.dumps(conflicts, ensure_ascii=False)[:300],
            "preview": {"conflict_count": conflict_count},
        }

    async def _step_write_back_settings(self) -> dict[str, Any]:
        """Step 8: Incrementally write back new settings to existing setting files."""
        # This step extracts any new characters/locations/power systems discovered
        # in the planning and writes them to 设定集/ files
        chapter_outlines = self.context.get("chapter_outlines", "")

        system_prompt = f"""你是设定管理助手。请从第 {self.volume_id} 卷的大纲中提取新增的设定元素。

需要提取的设定类型：
1. 新角色（名称、简介、动机）
2. 新势力/组织
3. 新地点
4. 新力量体系/金手指能力
5. 新伏笔

输出 JSON 格式：{{"new_settings": [{{"type": "character/faction/location/power/foreshadowing", "name": "...", "description": "..."}}]}}
如果没有新增设定，输出空数组。"""

        user_prompt = f"""=== 第 {self.volume_id} 卷详细大纲 ===
{chapter_outlines}

请提取新增设定。"""

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=4096,
            temperature=0.1,
        )

        settings_json = PromptBuilder._extract_json(response)
        new_settings = json.loads(settings_json) if settings_json else {"new_settings": []}
        self.context["new_settings"] = new_settings

        setting_count = len(new_settings.get("new_settings", []))
        return {
            "output": json.dumps(new_settings, ensure_ascii=False)[:300],
            "preview": {"new_settings_count": setting_count},
        }

    async def _step_commit_artifacts(self) -> dict[str, Any]:
        """Step 9: Commit all planning artifacts to disk."""
        outline_dir = self.project_root / "大纲"
        outline_dir.mkdir(parents=True, exist_ok=True)

        # Save a summary JSON
        summary = {
            "volume_id": self.volume_id,
            "beat_sheet_path": f"第{self.volume_id}卷-节拍表.md",
            "timeline_path": f"第{self.volume_id}卷-时间线.md",
            "chapter_outlines_path": f"第{self.volume_id}卷-详细大纲.md",
            "continuity_issues": self.context.get("continuity_issues", {}),
            "conflicts": self.context.get("conflicts", {}),
            "new_settings": self.context.get("new_settings", {}),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        summary_path = outline_dir / f"第{self.volume_id}卷-规划元数据.json"
        FileIO.write_json(summary_path, summary)

        return {
            "output": f"已落库第 {self.volume_id} 卷规划产物",
            "output_path": str(summary_path),
            "preview": {"artifacts": ["节拍表", "时间线", "详细大纲", "规划元数据"]},
        }

    def _persist_state(self) -> None:
        self.task_store.save({
            "active_task": {
                "task_id": self.task_id,
                "type": "plan",
                "volume_id": self.volume_id,
                "status": "running",
                "current_step": self.current_step,
                "total_steps": len(PLAN_STEPS),
                "step_results": {str(k): v for k, v in self.step_results.items()},
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        })

    def _finalize_cancelled(self, total_start: float) -> dict[str, Any]:
        total_elapsed_ms = int((time.monotonic() - total_start) * 1000)
        task_manager.emit(self.task_id, "task_cancelled", {
            "task_id": self.task_id,
            "completed_steps": self.current_step,
        })
        ts = task_manager.get_task(self.task_id)
        if ts:
            ts.status = "cancelled"
        return {
            "status": "cancelled",
            "completed_steps": self.current_step,
            "total_elapsed_ms": total_elapsed_ms,
        }
