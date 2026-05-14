"""ChapterOrchestrator — 6-step write flow state machine.

Steps:
  1. 上下文构建 (context)  → LLM
  2. 正文起草 (draft)      → LLM
  3. 审查 (review)         → LLM
  4. 润色 (polish)         → LLM
  5. 事实提取 (fact extract) → LLM
  6. 提交落库 (commit)     → file ops only

Supports pause/resume/cancel, SSE event broadcasting, and recovery
from workflow_state.json.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.core.logger import get_logger
from app.data.file_io import FileIO
from app.data.task_store import TaskStore
from app.llm.anthropic_client import AnthropicClient
from app.llm.openai_client import OpenAICompatibleClient
from app.services.prompt_builder import PromptBuilder
from app.services.task_manager import task_manager

logger = get_logger(__name__)


# ── Step definitions ─────────────────────────────────────────────────

@dataclass
class StepDef:
    name: str
    llm_required: bool
    estimated_seconds: int


STEPS: list[StepDef] = [
    StepDef("上下文构建", llm_required=True, estimated_seconds=15),
    StepDef("正文起草", llm_required=True, estimated_seconds=30),
    StepDef("审查", llm_required=True, estimated_seconds=20),
    StepDef("润色", llm_required=True, estimated_seconds=25),
    StepDef("事实提取", llm_required=True, estimated_seconds=15),
    StepDef("提交落库", llm_required=False, estimated_seconds=5),
]


# ── LLM call interface ───────────────────────────────────────────────

class LLMCaller(Protocol):
    """Abstract interface for LLM calls."""
    async def __call__(
        self,
        system: str,
        user: str,
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> str: ...


def _make_caller(
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
) -> LLMCaller:
    """Create an LLM caller based on provider config."""
    if provider == "anthropic":
        client = AnthropicClient(api_key=api_key, base_url=base_url or None)
        async def call(system: str, user: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
            resp = await client.chat(
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
            )
            return resp["content"]
        return call
    else:
        client = OpenAICompatibleClient(api_key=api_key, base_url=base_url, model=model)
        async def call(system: str, user: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
            resp = await client.chat(
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
            )
            return resp["content"]
        return call


# ── Chapter file helpers ─────────────────────────────────────────────

def _find_chapter_file(project_root: Path, chapter_num: int) -> Path | None:
    """Find chapter file by number in 正文/ directory."""
    chapter_dir = project_root / "正文"
    if not chapter_dir.exists():
        return None
    for f in chapter_dir.iterdir():
        if f.suffix != ".md":
            continue
        # Pattern: 第0005章-xxx.md
        name = f.stem
        if name.startswith("第") and name[1:5].isdigit():
            num = int(name[1:5])
            if num == chapter_num:
                return f
    return None


def _chapter_filename(chapter_num: int, title: str = "未命名") -> str:
    return f"第{chapter_num:04d}章-{title}.md"


def _word_count(content: str) -> int:
    return len(content.replace(" ", "").replace("\n", "").replace("\r", ""))


# ── Orchestrator ─────────────────────────────────────────────────────

class ChapterOrchestrator:
    """6-step chapter write flow orchestrator."""

    def __init__(
        self,
        task_id: str,
        project_id: str,
        chapter_num: int,
        project_root: Path,
        caller: LLMCaller,
        mode: str = "default",
    ) -> None:
        self.task_id = task_id
        self.project_id = project_id
        self.chapter_num = chapter_num
        self.project_root = project_root
        self.caller = caller
        self.mode = mode
        self.current_step = 0
        self.step_results: dict[int, dict[str, Any]] = {}
        self.task_store = TaskStore(project_root)
        self._cancelled = False

    async def execute(self) -> dict[str, Any]:
        """Execute the full 6-step flow.

        Returns a summary dict with final status.
        """
        total_start = time.monotonic()

        # Emit task_start
        task_manager.emit(self.task_id, "task_start", {
            "task_id": self.task_id,
            "type": "draft",
            "chapter_num": self.chapter_num,
            "total_steps": len(STEPS),
            "mode": self.mode,
        })

        # Persist initial state
        self._persist_state()

        for i, step_def in enumerate(STEPS):
            # Check cancel flag
            if self._cancelled:
                return self._finalize_cancelled(total_start)

            # Check pause flag via TaskState
            ts = task_manager.get_task(self.task_id)
            if ts and ts.is_cancelled():
                self._cancelled = True
                return self._finalize_cancelled(total_start)

            # Wait while paused
            while ts and ts.is_paused() and not ts.is_cancelled():
                await asyncio.sleep(0.3)
                ts = task_manager.get_task(self.task_id)
                if ts and ts.is_cancelled():
                    self._cancelled = True
                    return self._finalize_cancelled(total_start)

            # Skip already-completed steps (recovery path)
            if i in self.step_results and self.step_results[i].get("status") == "completed":
                logger.info(f"[draft:{self.task_id}] Skipping completed step {i + 1}: {step_def.name}")
                continue

            step_start = time.monotonic()
            self.current_step = i

            # Update TaskState
            if ts:
                ts.current_step = i
                ts.step_name = step_def.name
                ts.status = "running"

            # Emit step_start
            task_manager.emit(self.task_id, "step_start", {
                "task_id": self.task_id,
                "step_number": i + 1,
                "step_name": step_def.name,
                "estimated_seconds": step_def.estimated_seconds,
            })

            # Run step
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

                # Emit step_complete
                task_manager.emit(self.task_id, "step_complete", {
                    "task_id": self.task_id,
                    "step_number": i + 1,
                    "step_name": step_def.name,
                    "elapsed_ms": elapsed_ms,
                    "output_path": result.get("output_path", ""),
                    "preview": result.get("preview", {}),
                })
                logger.info(
                    f"[draft:{self.task_id}] Step {i + 1} ({step_def.name}) completed in {elapsed_ms}ms"
                )
            except Exception as e:
                elapsed_ms = int((time.monotonic() - step_start) * 1000)
                error_msg = str(e)

                # Special handling: if review step has blocking issues, stop flow
                if i == 2 and isinstance(e, BlockingReviewError):
                    self.step_results[i] = {
                        "status": "blocked",
                        "error": error_msg,
                        "issues": e.issues,
                    }
                    self._persist_state()
                    task_manager.emit(self.task_id, "step_failed", {
                        "task_id": self.task_id,
                        "step_number": i + 1,
                        "step_name": step_def.name,
                        "error_code": "REVIEW_BLOCKING",
                        "error_message": error_msg,
                        "retryable": False,
                    })
                    return self._finalize_blocked(total_start, e.issues)

                logger.error(f"[draft:{self.task_id}] Step {i + 1} failed: {error_msg}")
                task_manager.emit(self.task_id, "task_failed", {
                    "task_id": self.task_id,
                    "failed_step": i + 1,
                    "failed_step_name": step_def.name,
                    "error_message": error_msg,
                    "recoverable": True,
                })
                return {
                    "status": "failed",
                    "failed_step": i + 1,
                    "error": error_msg,
                    "completed_steps": i,
                }

        total_elapsed_ms = int((time.monotonic() - total_start) * 1000)
        task_manager.emit(self.task_id, "task_complete", {
            "task_id": self.task_id,
            "total_elapsed_ms": total_elapsed_ms,
            "final_status": "completed",
            "result_summary": f"第{self.chapter_num}章起草完成",
        })

        # Update TaskState
        ts = task_manager.get_task(self.task_id)
        if ts:
            ts.status = "completed"
            ts.current_step = len(STEPS)

        # Clear workflow state on success
        self.task_store.clear()

        return {
            "status": "completed",
            "chapter_num": self.chapter_num,
            "total_elapsed_ms": total_elapsed_ms,
        }

    async def _run_step(self, step_index: int) -> dict[str, Any]:
        """Execute a single step and return its result dict."""
        if step_index == 0:
            return await self._step_context()
        elif step_index == 1:
            return await self._step_draft()
        elif step_index == 2:
            return await self._step_review()
        elif step_index == 3:
            return await self._step_polish()
        elif step_index == 4:
            return await self._step_fact_extract()
        elif step_index == 5:
            return await self._step_commit()
        else:
            raise ValueError(f"Unknown step index: {step_index}")

    async def _step_context(self) -> dict[str, Any]:
        """Step 1: Build writing task book (写作任务书)."""
        # Load contract tree
        contract = PromptBuilder.load_contract_tree(self.project_root, self.chapter_num)
        if not contract:
            contract = {}

        # Load prev chapter summary
        prev_summary = PromptBuilder.load_prev_summary(self.project_root, self.chapter_num)
        project_setting = PromptBuilder.load_project_setting(self.project_root)

        system_prompt, user_prompt = PromptBuilder.build_context_prompt(
            chapter_num=self.chapter_num,
            contract_tree=contract,
            prev_chapter_summary=prev_summary,
            project_setting=project_setting,
        )

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=8192,
            temperature=0.3,
        )

        # Parse JSON from response
        try:
            context_book = json.loads(response)
        except json.JSONDecodeError:
            # If LLM doesn't return pure JSON, save as-is
            context_book = {"raw": response}

        # Save to tmp
        tmp_dir = self.project_root / ".webnovel" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        ctx_path = tmp_dir / f"context_ch{self.chapter_num}.json"
        FileIO.write_json(ctx_path, context_book)

        return {
            "output": json.dumps(context_book, ensure_ascii=False)[:500],
            "output_path": str(ctx_path),
            "preview": {"type": "context_book"},
        }

    async def _step_draft(self) -> dict[str, Any]:
        """Step 2: Draft chapter content."""
        # Load context book from step 1
        tmp_dir = self.project_root / ".webnovel" / "tmp"
        ctx_path = tmp_dir / f"context_ch{self.chapter_num}.json"
        context_book: dict[str, Any] = {}
        if ctx_path.exists():
            context_book = FileIO.read_json(ctx_path)

        # Load genre from state.json
        state_path = self.project_root / ".webnovel" / "state.json"
        genre = ""
        if state_path.exists():
            state = FileIO.read_json(state_path)
            genre = state.get("project", {}).get("genre", "") or state.get("genre", "")

        system_prompt, user_prompt = PromptBuilder.build_draft_prompt(
            context_book=context_book,
            genre=genre,
        )

        content = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=16384,
            temperature=0.8,
        )

        # Save draft to tmp
        draft_path = tmp_dir / f"draft_ch{self.chapter_num}.md"
        FileIO.write_markdown(draft_path, content)

        return {
            "output": content[:300] + ("..." if len(content) > 300 else ""),
            "output_path": str(draft_path),
            "preview": {"word_count": _word_count(content)},
        }

    async def _step_review(self) -> dict[str, Any]:
        """Step 3: Review chapter content."""
        # Load draft
        tmp_dir = self.project_root / ".webnovel" / "tmp"
        draft_path = tmp_dir / f"draft_ch{self.chapter_num}.md"
        if not draft_path.exists():
            raise FileNotFoundError(f"草稿文件不存在: {draft_path}")

        content = FileIO.read_markdown(draft_path)

        # Load contract tree for review constraints
        contract = PromptBuilder.load_contract_tree(self.project_root, self.chapter_num)

        # Load setting context
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

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=8192,
            temperature=0.1,
        )

        # Parse review JSON
        review_json = self._extract_json(response)
        review_results = json.loads(review_json) if review_json else {"issues": [], "summary": response}

        # Save review results
        review_path = tmp_dir / f"review_ch{self.chapter_num}.json"
        FileIO.write_json(review_path, review_results)

        # Check for blocking issues
        issues = review_results.get("issues", [])
        blocking = [i for i in issues if i.get("blocking", False)]
        if blocking:
            raise BlockingReviewError(
                f"审查发现 {len(blocking)} 个阻断项，需修复后才能继续",
                issues=issues,
            )

        return {
            "output": json.dumps(review_results, ensure_ascii=False)[:500],
            "output_path": str(review_path),
            "preview": {
                "issues_count": len(issues),
                "blocking": len(blocking) > 0,
            },
        }

    async def _step_polish(self) -> dict[str, Any]:
        """Step 4: Polish chapter content."""
        tmp_dir = self.project_root / ".webnovel" / "tmp"

        # Load draft
        draft_path = tmp_dir / f"draft_ch{self.chapter_num}.md"
        draft_content = FileIO.read_markdown(draft_path)

        # Load review issues
        review_path = tmp_dir / f"review_ch{self.chapter_num}.json"
        review_results: dict[str, Any] = {}
        if review_path.exists():
            review_results = FileIO.read_json(review_path)

        # Load genre
        state_path = self.project_root / ".webnovel" / "state.json"
        genre = ""
        if state_path.exists():
            state = FileIO.read_json(state_path)
            genre = state.get("project", {}).get("genre", "") or state.get("genre", "")

        system_prompt, user_prompt = PromptBuilder.build_polish_prompt(
            draft_content=draft_content,
            review_issues=review_results.get("issues", []),
            genre=genre,
        )

        polished = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=16384,
            temperature=0.5,
        )

        # Save polished
        polished_path = tmp_dir / f"polished_ch{self.chapter_num}.md"
        FileIO.write_markdown(polished_path, polished)

        return {
            "output": polished[:300] + ("..." if len(polished) > 300 else ""),
            "output_path": str(polished_path),
            "preview": {"word_count": _word_count(polished)},
        }

    async def _step_fact_extract(self) -> dict[str, Any]:
        """Step 5: Extract facts from polished content (data-agent)."""
        tmp_dir = self.project_root / ".webnovel" / "tmp"

        # Load polished content
        polished_path = tmp_dir / f"polished_ch{self.chapter_num}.md"
        if not polished_path.exists():
            raise FileNotFoundError(f"润色文件不存在: {polished_path}")

        content = FileIO.read_markdown(polished_path)

        # Load contract tree and review results
        contract = PromptBuilder.load_contract_tree(self.project_root, self.chapter_num)
        review_path = tmp_dir / f"review_ch{self.chapter_num}.json"
        review_results: dict[str, Any] | None = None
        if review_path.exists():
            review_results = FileIO.read_json(review_path)

        system_prompt, user_prompt = PromptBuilder.build_data_prompt(
            chapter_content=content,
            chapter_num=self.chapter_num,
            contract_tree=contract,
            review_results=review_results,
        )

        response = await self.caller(
            system=system_prompt,
            user=user_prompt,
            max_tokens=4096,
            temperature=0.1,
        )

        # Parse extraction JSON
        extraction = self._extract_json(response)
        extraction_data = json.loads(extraction) if extraction else {"raw": response}

        # Save extraction artifacts
        ful_path = tmp_dir / f"fulfillment_result_ch{self.chapter_num}.json"
        dis_path = tmp_dir / f"disambiguation_result_ch{self.chapter_num}.json"
        ext_path = tmp_dir / f"extraction_result_ch{self.chapter_num}.json"

        FileIO.write_json(ful_path, extraction_data.get("fulfillment_result", {}))
        FileIO.write_json(dis_path, extraction_data.get("disambiguation_result", {}))
        FileIO.write_json(ext_path, extraction_data.get("extraction_result", {}))

        return {
            "output": json.dumps(extraction_data, ensure_ascii=False)[:300],
            "output_path": str(ext_path),
            "preview": {"type": "fact_extraction"},
        }

    async def _step_commit(self) -> dict[str, Any]:
        """Step 6: Commit chapter — write polished content to 正文/, update state."""
        tmp_dir = self.project_root / ".webnovel" / "tmp"

        # Load polished content
        polished_path = tmp_dir / f"polished_ch{self.chapter_num}.md"
        if not polished_path.exists():
            # Fallback to draft if polish failed/was skipped
            draft_path = tmp_dir / f"draft_ch{self.chapter_num}.md"
            if draft_path.exists():
                polished_path = draft_path
            else:
                raise FileNotFoundError("无可用正文内容（草稿和润色均未完成）")

        content = FileIO.read_markdown(polished_path)

        # Write to 正文/ directory
        chapter_dir = self.project_root / "正文"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        # Try to extract title from context book
        ctx_path = tmp_dir / f"context_ch{self.chapter_num}.json"
        title = "未命名"
        if ctx_path.exists():
            ctx = FileIO.read_json(ctx_path)
            # Try to get title from chapter directive or CBN
            directive = ctx.get("chapter_directive", {})
            title = directive.get("title", "未命名")

        filename = _chapter_filename(self.chapter_num, title)
        chapter_file = chapter_dir / filename
        FileIO.write_markdown(chapter_file, content)

        wc = _word_count(content)

        # Update word count in state.json
        state_path = self.project_root / ".webnovel" / "state.json"
        if state_path.exists():
            try:
                state = FileIO.read_json(state_path)
                counts = state.setdefault("chapter_word_counts", {})
                key = str(self.chapter_num)
                old_wc = counts.get(key, 0)
                state["word_count"] = state.get("word_count", 0) - old_wc + wc
                counts[key] = wc
                # Update chapter progress
                chapters_done = state.get("chapters_done", {})
                chapters_done[str(self.chapter_num)] = "committed"
                state["chapters_done"] = chapters_done
                FileIO.write_json(state_path, state)
            except Exception as e:
                logger.warning(f"Failed to update state.json: {e}")

        return {
            "output": f"已写入 {filename} ({wc}字)",
            "output_path": str(chapter_file),
            "preview": {"word_count": wc, "title": title},
        }

    # ── State persistence ────────────────────────────────────────────

    def _persist_state(self) -> None:
        """Atomically persist current progress to workflow_state.json."""
        self.task_store.save({
            "active_task": {
                "task_id": self.task_id,
                "type": "draft",
                "chapter_num": self.chapter_num,
                "status": "running",
                "current_step": self.current_step,
                "total_steps": len(STEPS),
                "step_results": {
                    str(k): v for k, v in self.step_results.items()
                },
                "mode": self.mode,
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        })

    # ── Finalization ─────────────────────────────────────────────────

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

    def _finalize_blocked(self, total_start: float, issues: list) -> dict[str, Any]:
        total_elapsed_ms = int((time.monotonic() - total_start) * 1000)
        return {
            "status": "blocked",
            "blocking_issues": issues,
            "total_elapsed_ms": total_elapsed_ms,
        }

    # ── Utilities ────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """Extract JSON from LLM response (may contain markdown fences)."""
        # Try to find ```json ... ``` block
        start = text.find("```json")
        if start >= 0:
            start += 7
            end = text.find("```", start)
            if end > 0:
                return text[start:end].strip()
        # Try to find any ``` block
        start = text.find("```")
        if start >= 0:
            start += 3
            end = text.find("```", start)
            if end > 0:
                return text[start:end].strip()
        # Try direct parse
        text = text.strip()
        if text.startswith("{"):
            return text
        return None


class BlockingReviewError(Exception):
    """Raised when review finds blocking issues."""
    def __init__(self, message: str, issues: list) -> None:
        super().__init__(message)
        self.issues = issues
