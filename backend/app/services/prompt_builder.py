"""PromptBuilder — construct system/user prompts for all 5 LLM call scenarios.

Replaces the 3 subagents (context-agent, reviewer, data-agent) plus the
draft and polish steps from SKILL.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.data.file_io import FileIO

# ── Anti-AI rules (from SKILL.md) ───────────────────────────────────

ANTI_AI_RULES = """
起草时对抗以下 8 种 LLM 倾向：
1. 每段写完整闭环 → 刻意删掉感悟，留余味
2. 副词修饰一切 → 用具体动作替代
3. 所有角色同一套反应 → 设计专属微动作
4. 对话像辩论赛 → 带潜台词、言行不一、有省略和打断
5. 情绪贴标签 → 生理反应 + 微动作
6. 信息均匀分布 → 刻意制造疏密对比
7. 安全着陆 → 每章留未解决的钩子
8. 第一第二第三 → 避免枚举式结构
"""

# ── Core constraints (三大定律 + 防幻觉协议) ─────────────────────────

CORE_CONSTRAINTS = """
三大定律：
1. 大纲是法 — 章纲是最高指令，不得偏离
2. 设定是物理 — 世界观和力量体系是硬性物理法则
3. 发明需要认同 — 不得凭空发明新设定，必须有来源

防幻觉协议：
- 所有角色、势力、地名必须来自合同树或已有设定
- 不得发明未定义的力量体系、金手指能力
- 不得改变已有角色的性格、关系、立场
- 时间线必须与已有章节一致
"""


class PromptBuilder:
    """Build system + user prompts for 5 LLM call scenarios."""

    # ── Step 1: Context Agent Prompt ────────────────────────────────

    @staticmethod
    def build_context_prompt(
        chapter_num: int,
        contract_tree: dict[str, Any],
        prev_chapter_summary: str | None = None,
        project_setting: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Build prompt for context assembly (写作任务书).

        Returns (system_prompt, user_prompt).
        """
        system_prompt = f"""你是中文网文写作助手。你的任务是为第 {chapter_num} 章生成一份完整的写作任务书。

{CORE_CONSTRAINTS}

输出要求：
- 严格按五段输出：本章硬性约束 → CBN/CPNs/CEN → 本章禁区 → 风格指引 → dynamic_context补充参考
- 输出格式为 JSON
- 必须基于合同树中的真实信息，不得编造
"""
        # Build user prompt from contract tree
        chapter_contract = contract_tree.get("chapter", {})
        chapter_directive = chapter_contract.get("chapter_directive", {})
        must_cover = chapter_contract.get("must_cover_nodes", [])
        forbidden = chapter_contract.get("forbidden_zones", [])
        dynamic_ctx = contract_tree.get("dynamic_context", {})

        user_prompt_parts = [
            f"章节号：第 {chapter_num} 章",
            "",
            "=== 本章硬性约束 ===",
            json.dumps(chapter_directive, ensure_ascii=False, indent=2),
            "",
            "=== CBN/CPNs/CEN (结构化节点) ===",
            json.dumps(must_cover, ensure_ascii=False, indent=2),
            "",
            "=== 本章禁区 ===",
            json.dumps(forbidden, ensure_ascii=False, indent=2),
        ]

        if prev_chapter_summary:
            user_prompt_parts.extend([
                "",
                "=== 上一章摘要 ===",
                prev_chapter_summary,
            ])

        if dynamic_ctx:
            user_prompt_parts.extend([
                "",
                "=== dynamic_context 补充参考 ===",
                json.dumps(dynamic_ctx, ensure_ascii=False, indent=2),
            ])

        if project_setting:
            user_prompt_parts.extend([
                "",
                "=== 项目设定 ===",
                json.dumps(project_setting, ensure_ascii=False, indent=2),
            ])

        user_prompt = "\n".join(user_prompt_parts)
        return system_prompt, user_prompt

    # ── Step 2: Draft Prompt ────────────────────────────────────────

    @staticmethod
    def build_draft_prompt(
        context_book: dict[str, Any],
        genre: str = "",
    ) -> tuple[str, str]:
        """Build prompt for chapter drafting.

        context_book is the 写作任务书 JSON from Step 1.
        """
        system_prompt = f"""你是中文网文作家。请根据写作任务书起草章节正文。

要求：
- 默认 2000-2500 字
- 只输出纯正文，无占位符、无说明、无注释
- 围绕 CBN → CPNs → CEN 展开
- 中文思维写作

{ANTI_AI_RULES}
{CORE_CONSTRAINTS}
"""
        user_prompt = (
            f"题材：{genre}\n\n"
            "=== 写作任务书 ===\n"
            f"{json.dumps(context_book, ensure_ascii=False, indent=2)}\n\n"
            "请开始起草正文。"
        )
        return system_prompt, user_prompt

    # ── Step 3: Review Prompt ───────────────────────────────────────

    @staticmethod
    def build_review_prompt(
        chapter_content: str,
        chapter_num: int,
        contract_tree: dict[str, Any] | None = None,
        setting_context: str = "",
    ) -> tuple[str, str]:
        """Build prompt for chapter review (schema v6)."""
        system_prompt = f"""你是中文网文审查专家。请对第 {chapter_num} 章进行严格审查。

审查输出格式为 JSON，使用 schema v6：
- 无总分（不输出 overall_score）
- 每个 issue 必须包含：severity, category, location, description, evidence, fix_hint, blocking
- severity=critical 自动 blocking=true
- blocking issue 必须解决才能进入下一步

检查维度：
1. 设定一致性 — 角色、力量体系、世界观是否偏离
2. 时间线连续性 — 事件顺序是否合理
3. 章纲符合度 — 是否覆盖 CBN/CPNs/CEN
4. 文风质量 — Anti-AI 规则检查、节奏、钩子
5. OOC 检查 — 角色行为是否符合人设

{CORE_CONSTRAINTS}
"""
        # Build context from contract tree if available
        context_parts: list[str] = []
        if contract_tree:
            chapter_contract = contract_tree.get("chapter", {})
            context_parts.append("=== 合同树约束 ===")
            context_parts.append(json.dumps(chapter_contract, ensure_ascii=False, indent=2))

        if setting_context:
            context_parts.append("")
            context_parts.append("=== 设定上下文 ===")
            context_parts.append(setting_context)

        user_prompt = "\n".join(context_parts) if context_parts else ""
        user_prompt += f"\n\n=== 第 {chapter_num} 章正文 ===\n{chapter_content}"
        user_prompt += "\n\n请输出审查结果 JSON。"

        return system_prompt, user_prompt

    # ── Step 4: Polish Prompt ───────────────────────────────────────

    @staticmethod
    def build_polish_prompt(
        draft_content: str,
        review_issues: list[dict[str, Any]] | None = None,
        genre: str = "",
    ) -> tuple[str, str]:
        """Build prompt for chapter polishing.

        Repairs non-blocking issues from review, applies style adaptation,
        typesetting, and final Anti-AI check.
        """
        system_prompt = f"""你是中文网文润色编辑。请对章节正文进行润色。

润色顺序：
1. 修复审查报告中的非 blocking issue
2. 风格适配（题材适配）
3. 排版优化
4. Anti-AI 终检

规则：
- 只改表达，不改事实
- 不改变情节、角色、设定
- 保持原文的核心情感和节奏

{ANTI_AI_RULES}
"""
        user_prompt_parts: list[str] = []

        if review_issues:
            non_blocking = [i for i in review_issues if not i.get("blocking", False)]
            if non_blocking:
                user_prompt_parts.append("=== 需要修复的问题 ===")
                for i, issue in enumerate(non_blocking, 1):
                    user_prompt_parts.append(
                        f"{i}. [{issue.get('severity', '')}] {issue.get('description', '')}"
                    )
                    if issue.get("fix_hint"):
                        user_prompt_parts.append(f"   修复建议：{issue['fix_hint']}")
                user_prompt_parts.append("")

        user_prompt_parts.extend([
            f"题材：{genre}",
            "",
            "=== 正文草稿 ===",
            draft_content,
            "",
            "请输出润色后的正文。",
        ])

        user_prompt = "\n".join(user_prompt_parts)
        return system_prompt, user_prompt

    # ── Step 5: Data Extraction Prompt ──────────────────────────────

    @staticmethod
    def build_data_prompt(
        chapter_content: str,
        chapter_num: int,
        contract_tree: dict[str, Any] | None = None,
        review_results: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Build prompt for fact extraction (data-agent).

        Produces: fulfillment_result, disambiguation_result, extraction_result JSON.
        """
        system_prompt = f"""你是事实提取助手。请从第 {chapter_num} 章正文中提取事实，生成三份 JSON artifact：

1. fulfillment_result — 章纲节点覆盖情况
2. disambiguation_result — 新增/变更的角色、势力、设定
3. extraction_result — 摘要、新实体、新关系、伏笔

输出格式为 JSON，包含三个字段：fulfillment_result, disambiguation_result, extraction_result。

只提取正文中明确出现的事实，不要推断或编造。
"""
        user_prompt_parts = [
            f"章节号：第 {chapter_num} 章",
            "",
            "=== 正文 ===",
            chapter_content,
        ]

        if contract_tree:
            chapter_contract = contract_tree.get("chapter", {})
            user_prompt_parts.extend([
                "",
                "=== 合同树（用于覆盖检查） ===",
                json.dumps(chapter_contract, ensure_ascii=False, indent=2),
            ])

        if review_results:
            user_prompt_parts.extend([
                "",
                "=== 审查结果 ===",
                json.dumps(review_results, ensure_ascii=False, indent=2),
            ])

        user_prompt = "\n".join(user_prompt_parts)
        return system_prompt, user_prompt

    # ── Helper: Load contract tree for a chapter ────────────────────

    @staticmethod
    def load_contract_tree(project_root: Path, chapter_num: int) -> dict[str, Any] | None:
        """Load .story-system/ contract tree for a specific chapter."""
        tree_dir = project_root / ".story-system"
        if not tree_dir.exists():
            return None

        chapter_file = tree_dir / f"chapters" / f"chapter_{chapter_num:04d}.review.json"
        if chapter_file.exists():
            return FileIO.read_json(chapter_file)
        return None

    @staticmethod
    def load_prev_summary(project_root: Path, chapter_num: int) -> str | None:
        """Load previous chapter summary from .webnovel/summaries/."""
        summary_path = project_root / ".webnovel" / "summaries" / f"ch{chapter_num - 1:04d}.md"
        if summary_path.exists():
            return FileIO.read_markdown(summary_path)
        return None

    @staticmethod
    def load_project_setting(project_root: Path) -> dict[str, Any]:
        """Load project state.json as setting context."""
        state_path = project_root / ".webnovel" / "state.json"
        if state_path.exists():
            return FileIO.read_json(state_path)
        return {}

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """Extract JSON from LLM response (may contain markdown fences)."""
        start = text.find("```json")
        if start >= 0:
            start += 7
            end = text.find("```", start)
            if end > 0:
                return text[start:end].strip()
        for opener, closer in [("{", "}"), ("[", "]")]:
            s = text.find(opener)
            if s >= 0:
                e = text.rfind(closer)
                if e > s:
                    return text[s:e + 1]
        return None
