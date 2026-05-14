# Feature: Web 网文创作应用

**作者**: cajoj0313
**日期**: 2026-05-12
**状态**: Draft

---

## 1. 背景 (Background)

### 1.1 问题描述

当前网文创作系统通过 Claude Code CLI 斜杠命令（`/webnovel-write`、`/webnovel-review` 等）驱动，依赖终端交互，无可视化界面。作者无法直观地：
- 查看章节列表和进度
- 在页面上操作起草、审查、规划等流程
- 实时查看执行进度和中间产物（任务书、审查报告等）
- 管理多本书的创作状态

需要一套独立的 Web 应用，将 CLI skill 流程转化为可视化页面操作。

### 1.2 现状分析

**现有系统架构**：纯 Claude Code skill/plugin 系统，包含 5 个技能 + 3 个 Python 脚本 + 3 个 Subagent。

**代码路径与数据流**：

- **技能定义**：`webnovel-{write,review,plan,query,learn}/SKILL.md` — YAML front matter + 步骤化流程定义
- **Python 脚本**（在 `CLAUDE_PLUGIN_ROOT/scripts/` 下，不在此仓库）：
  - `webnovel.py` — 主 CLI 入口（preflight、story-system、review-pipeline、chapter-commit、backup、knowledge 查询、memory-contract 等 20+ 子命令）
  - `reference_search.py` — BM25 检索 CSV 知识库
  - `validate_csv.py` — CSV schema 校验
- **Subagent**（Claude Code agent 定义）：
  - `webnovel-writer:context-agent` — 写前 research，输出写作任务书
  - `webnovel-writer:reviewer` — 统一审查，输出结构化 JSON
  - `webnovel-writer:data-agent` — 从正文提取事实，生成 commit artifacts

**数据存储方式**：
- `.story-system/` 合同树（MASTER_SETTING、volumes、chapters、commits、anti_patterns）— JSON 文件
- `.webnovel/state.json` — 项目配置快照 + 进度状态
- `.webnovel/index.db` — SQLite 数据库（实体、关系、审查指标等 15+ 表）
- `.webnovel/summaries/` — 章节摘要 Markdown
- `正文/第{NNNN}章-{title}.md` — 章节正文
- `大纲/` — 总纲、卷节拍表、卷时间线、详细大纲
- `设定集/` — 世界观、力量体系、角色卡等
- `references/csv/` — 9 张 CSV 知识表（UTF-8 with BOM）

**技术约束**：
- 所有 Python 脚本使用 `python -X utf8` 执行
- 项目根通过 `webnovel.py where` 解析（需含 `.webnovel/state.json`）
- 写章流程 6 步串行，每步依赖上步产物
- 审查 schema 为 v6，blocking=true 阻断后续步骤
- 当前 LLM 调用通过 Claude Code Agent tool 完成

### 1.3 主要使用场景

1. **章节起草**：作者在页面选择/创建章节，点击起草按钮，系统执行 6 步写章流程（上下文→起草→审查→润色→事实提取→提交），每步展示进度，中间可暂停/查看产物
2. **章节审查**：对已有章节一键审查，查看结构化审查报告，决定是否修复
3. **大纲规划**：查看总纲，按卷生成节拍表、时间线、详细章纲，跨卷连续性检查
4. **设定查询**：查询角色、力量体系、势力、伏笔、金手指状态等
5. **模型配置**：维护多个 LLM 配置（供应商、URL、API Key），切换默认模型
6. **项目管理**：创建/切换/删除小说项目，查看项目概览和进度
7. **学习模式**：手动标注成功写作模式，追加到项目记忆

## 2. 目标 (Goals)

将现有 CLI skill 流程完整迁移为独立 Web 应用，提供可视化章节管理、起草流程、审查报告、大纲规划、设定查询等功能，后端复用现有 Python 脚本逻辑，直接读取现有文件数据源，使用 Claude API 直接调用 LLM 替代 Claude Code Agent tool。

### 2.1 非目标 (Non-Goals)

- 不做移动端适配，仅桌面端
- 不做用户权限/多租户系统（个人自用）
- 不做数据迁移（直接读现有 JSON/SQLite/Markdown 文件）
- 不支持并发写多章（一本书同一时间只跑一个流程，单章生成）
- 不需要 Git 备份（数据库/文件系统是唯一数据源）
- 不改变现有写章流程的业务逻辑和步骤顺序

## 3. 需求细化 (Requirements)

### 3.1 功能性需求

#### 模块一：模型配置管理
- 维护 LLM 列表：名称、供应商（Anthropic/DeepSeek/OpenAI兼容）、API URL、API Key、模型标识
- 设置/切换默认模型
- 测试连接（验证 API Key 和 URL 是否可用）

#### 模块二：小说项目管理
- 创建小说项目（指定项目根目录、题材、目标字数、目标章节数）
- 切换项目（加载对应 `.webnovel/state.json` 和合同树）
- 项目概览页：当前进度（已写/已规划章节数）、审查状态、最后更新时间
- 删除项目（仅移除配置，不删除项目文件）

#### 模块三：章节管理（核心）
- 章节列表：章节号、标题、字数、状态（未写/起草中/已完成/已驳回）、审查结果、最后更新时间
- 起草按钮 → 启动 6 步写章流程
- 实时进度展示：当前步骤名称、执行状态（等待/运行中/完成/失败）、耗时、中间产物预览
  - Step 1：写作任务书（可查看 JSON）
  - Step 2：正文草稿（可查看/编辑）
  - Step 3：审查结果（可查看 JSON + 报告）
  - Step 4：润色后正文
  - Step 5：commit 状态（fulfillment/disambiguation/extraction 结果）
  - Step 6：备份状态
- 暂停/恢复/取消当前执行
- 支持批量起草：选择连续章节范围，按顺序串行执行
- 章节正文在线查看和编辑（Markdown 编辑器）

#### 模块四：审查功能
- 对已写章节一键审查
- 审查报告展示：问题清单（severity、category、location、description、evidence、fix_hint）、阻断项高亮
- 用户决策：立即修复 / 仅保存报告稍后处理
- 审查历史：按章节查看历次审查记录

#### 模块五：大纲规划
- 总纲查看与编辑
- 选择目标卷 → 生成节拍表、时间线、详细章纲（9 步流程，带进度展示）
- 已有卷的连续性检查提示
- 新增设定增量写回现有设定集
- 验证结果展示（时间线冲突、缺失字段等）

#### 模块六：查询与设定
- 角色/力量体系/势力/伏笔/金手指查询（对应 webnovel-query 功能）
- 设定集查看与在线编辑（世界观、力量体系、主角卡、反派设计等）
- 查询结果格式化输出（带文件路径和行号）

#### 模块七：学习模式
- 手动输入成功模式描述
- 自动归类 pattern_type（hook/pacing/dialogue/payoff/emotion/format/other）
- 查看已学习模式列表
- 去重检查

### 3.2 非功能性需求

| 类别 | 约束 |
|------|------|
| 性能 | LLM API 调用延迟由上游决定，后端不增加显著延迟；页面响应 < 1s（非 LLM 请求） |
| 可用性 | LLM 调用失败时可重试；执行中断后支持从断点恢复（基于现有 .webnovel/tmp/ 中间文件） |
| 兼容性 | 直接读取现有 JSON/SQLite/Markdown 文件格式，不做格式变更 |
| 可观测 | 每个执行步骤记录日志（步骤名、开始/结束时间、成功/失败、错误信息）；LLM API 调用记录 token 消耗和费用 |
| 安全 | API Key 加密存储（环境变量或加密文件），不明文暴露到前端 |
| 资源 | 单章起草过程中内存占用稳定，无内存泄漏；不限制并发页面请求数 |
| 可扩展 | 模型配置支持新增供应商；后续可接入新的 skill 流程 |

## 4. 设计方案 (Design)

### 4.1 方案概览

**整体架构：前后端分离的单体应用**

```
┌─────────────────────────────────────────────┐
│                  浏览器                      │
│  Vue 3 + Vite + Element Plus + Pinia        │
│  ┌─────────┬──────────┬──────────────────┐  │
│  │ 项目首页 │ 章节列表 │  大纲/设定/查询  │  │
│  │         │ + 编辑器  │  页面            │  │
│  └─────────┴──────────┴──────────────────┘  │
│  ┌──────────────────────────────────────┐   │
│  │  执行进度面板（SSE 实时推送）         │   │
│  │  Step 1/2/3/4/5/6 状态 + 中间产物    │   │
│  └──────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │ REST API + SSE
                   │ (localhost)
┌──────────────────▼──────────────────────────┐
│          FastAPI (Python)                    │
│  ┌────────────────────────────────────────┐ │
│  │ API Router Layer                       │ │
│  │ /api/projects  /api/chapters           │ │
│  │ /api/review    /api/plan               │ │
│  │ /api/query     /api/settings           │ │
│  │ /api/llm-configs  /api/learn           │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ Service Layer (业务编排)               │ │
│  │ - ChapterOrchestrator (6步流程)        │ │
│  │ - ReviewService                        │ │
│  │ - PlanOrchestrator (9步流程)           │ │
│  │ - QueryService                         │ │
│  │ - LLMService (多模型路由)              │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ Script Integration Layer               │ │
│  │ - webnovel.py 子命令封装               │ │
│  │ - reference_search.py 封装             │ │
│  │ - validate_csv.py 封装                 │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ LLM Client Layer                       │ │
│  │ - Anthropic API (Claude Sonnet/Opus)   │ │
│  │ - OpenAI 兼容接口 (DeepSeek 等)        │ │
│  │ - Prompt Builder (context/review/data) │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ Data Access Layer                      │ │
│  │ - FileIO (JSON/Markdown/CSV 读写)      │ │
│  │ - SQLite Access (index.db)             │ │
│  │ - Project Registry (项目配置)           │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**技术选型：**

| 层级 | 技术 | 理由 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 响应式适合实时进度展示，中文生态好 |
| 组件库 | Element Plus | 中文支持成熟，表格/表单/进度组件齐全 |
| 状态管理 | Pinia | Vue 3 官方推荐，轻量 |
| HTTP 客户端 | Axios | SSE 支持成熟 |
| 后端框架 | FastAPI (Python) | 异步原生，SSE 支持好，与现有 Python 脚本天然兼容 |
| LLM 调用 | anthropic Python SDK + openai Python SDK | 官方 SDK，支持 Claude 和 OpenAI 兼容接口 |
| 实时推送 | SSE (Server-Sent Events) | 单向推送，后端→前端，适合进度通知，比 WebSocket 简单 |
| 数据存储 | 现有文件（JSON/SQLite/Markdown）+ 新增 project_registry.json | 不做迁移 |

**通信模式：**

- **短请求**（列表、查询、配置 CRUD）：REST API 同步返回
- **长任务**（起草、审查、规划）：POST 启动 → 返回 task_id → SSE 推送步骤进度 → GET 查询最终结果
- **中断控制**：POST /api/tasks/{task_id}/pause|resume|cancel

**部署形态：**

- 本地开发：`npm run dev`（前端 5173）+ `uvicorn`（后端 8000），CORS 跨域
- 生产部署：`npm run build` 静态文件由 FastAPI 挂载服务，单进程启动

### 4.2 组件设计 (Component Design)

#### 4.2.1 核心类/模块设计

**后端模块划分（5 层架构）：**

**Layer 1 — API Router（路由层）**

| 模块 | 路径前缀 | 职责 |
|------|----------|------|
| `project_router` | `/api/projects` | 项目 CRUD（创建/切换/删除/概览） |
| `chapter_router` | `/api/chapters` | 章节列表、正文查看/编辑、起草/批量起草 |
| `review_router` | `/api/review` | 单章审查、审查历史、审查报告查看 |
| `plan_router` | `/api/plan` | 大纲规划（卷节拍表、时间线、章纲生成） |
| `query_router` | `/api/query` | 角色/势力/伏笔/金手指查询 |
| `setting_router` | `/api/settings` | 设定集查看/编辑、总纲查看/编辑 |
| `llm_config_router` | `/api/llm-configs` | 模型配置 CRUD、测试连接 |
| `learn_router` | `/api/learn` | 学习模式（添加/查看/去重模式） |
| `task_router` | `/api/tasks` | 任务管理（暂停/恢复/取消/状态查询） |
| `sse_router` | `/api/events` | SSE 实时进度推送流 |

**Layer 2 — Service（业务编排层）**

| 模块 | 职责 |
|------|------|
| `ChapterOrchestrator` | 6 步写章流程编排，步骤间状态机，暂停/恢复/取消，中间产物缓存 |
| `ReviewService` | 单章审查流程（加载参考→调用 LLM→生成报告→落库） |
| `PlanOrchestrator` | 9 步大纲规划流程编排 |
| `QueryService` | 查询聚合（合同树 + index.db + 设定文件），按优先级检索 |
| `LLMService` | 多模型路由、API Key 管理、调用封装、重试、token 统计 |
| `ProjectService` | 项目配置管理、project_registry.json 读写 |

**Layer 3 — Core（核心业务逻辑层）**

| 模块 | 对应原脚本逻辑 | 职责 |
|------|---------------|------|
| `story_system` | `webnovel.py story-system` | 生成/刷新 Story Contract 合同树 |
| `review_pipeline` | `webnovel.py review-pipeline` | 审查结果处理、报告生成、指标计算 |
| `chapter_commit` | `webnovel.py chapter-commit` | 生成 CHAPTER_COMMIT、accepted/rejected 判定 |
| `update_state` | `webnovel.py update-state` | 原子更新 state.json |
| `preflight` | `webnovel.py preflight` | 项目预检（文件完整性、合同树验证） |
| `placeholder_scan` | `webnovel.py placeholder-scan` | 扫描占位符 |
| `master_outline_sync` | `webnovel.py master-outline-sync` | 总纲同步写回 |
| `reference_search` | `reference_search.py` | BM25 检索 CSV 知识库 |
| `validate_csv` | `validate_csv.py` | CSV 校验 |
| `backup_manager` | `webnovel.py backup` | 项目文件备份（原 Git 备份改为文件级） |

**Layer 4 — LLM Client（大模型调用层）**

| 模块 | 职责 |
|------|------|
| `AnthropicClient` | Claude API 调用（Sonnet/Opus），使用 `anthropic` SDK |
| `OpenAICompatibleClient` | OpenAI 兼容接口调用（DeepSeek 等），使用 `openai` SDK |
| `PromptBuilder` | 构建 context-agent / reviewer / data-agent 的系统 prompt 和用户 prompt（替代原有 subagent 行为） |
| `ModelRouter` | 根据配置选择模型，支持 fallback |

**Layer 5 — Data Access（数据访问层）**

| 模块 | 职责 |
|------|------|
| `FileIO` | 统一读写 JSON/Markdown/CSV 文件，UTF-8 编码处理 |
| `SQLiteAccess` | index.db 的读写（entities、relationships、chapters、review_metrics 等） |
| `ProjectRegistryStore` | project_registry.json 的读写（多项目管理） |
| `TaskStore` | 任务状态持久化（.webnovel/workflow_state.json），支持中断恢复 |

**前端模块划分：**

| 模块 | 职责 |
|------|------|
| `App` | 路由、布局框架（侧边栏 + 主内容区） |
| `ProjectHome` | 项目概览页（进度、审查状态） |
| `ChapterList` | 章节列表、起草/审查/批量起草按钮 |
| `ChapterEditor` | 章节正文查看和编辑（Markdown 编辑器） |
| `ExecutionProgress` | 执行进度面板（SSE 接收、步骤状态、中间产物展示） |
| `ReviewReport` | 审查报告展示（问题清单、阻断项高亮） |
| `PlanView` | 大纲规划（总纲、卷节拍表、时间线、章纲） |
| `SettingView` | 设定集查看/编辑 |
| `QueryView` | 设定查询 |
| `LLMConfigView` | 模型配置管理 |
| `LearnView` | 学习模式 |
| `stores/` | Pinia 状态管理（项目、章节、任务进度、模型配置） |
| `api/` | Axios 请求封装、SSE 客户端

#### 4.2.2 接口设计

**统一 POST，所有参数走请求 body。**

**项目相关：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/projects/list` | `{}` | `{ projects: [{id, title, genre, progress, last_updated}] }` |
| `POST /api/projects/create` | `{ root_path, genre, target_words, target_chapters }` | `{ id, title }` |
| `POST /api/projects/overview` | `{ project_id }` | `{ title, genre, current_chapter, total_chapters, total_words, review_status, last_updated }` |
| `POST /api/projects/delete` | `{ project_id }` | `{ ok: true }` |
| `POST /api/projects/switch` | `{ project_id }` | `{ ok: true, project_info }` |

**章节相关：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/chapters/list` | `{ project_id, volume? }` | `{ chapters: [{chapter_num, title, word_count, status, review_score, last_updated}] }` |
| `POST /api/chapters/get` | `{ project_id, chapter_num }` | `{ chapter_num, title, content, word_count, last_updated }` |
| `POST /api/chapters/save` | `{ project_id, chapter_num, content }` | `{ ok: true, word_count }` |
| `POST /api/chapters/draft` | `{ project_id, chapter_num, mode?: "default"|"fast"|"minimal" }` | `{ task_id }` |
| `POST /api/chapters/draft-batch` | `{ project_id, start_chapter, end_chapter, mode? }` | `{ task_id }` |

**审查相关：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/review/start` | `{ project_id, chapter_num }` | `{ task_id }` |
| `POST /api/review/history` | `{ project_id, chapter_num }` | `{ reviews: [{report_id, reviewed_at, issues_count, blocking_count, overall_score}] }` |
| `POST /api/review/report` | `{ project_id, report_id }` | `{ report: { issues: [{severity, category, location, description, evidence, fix_hint, blocking}], summary } }` |

**大纲规划：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/plan/master-outline/get` | `{ project_id }` | `{ content, last_updated }` |
| `POST /api/plan/master-outline/save` | `{ project_id, content }` | `{ ok: true }` |
| `POST /api/plan/volume/start` | `{ project_id, volume_id }` | `{ task_id }` |
| `POST /api/plan/volume/get` | `{ project_id, volume_id }` | `{ beat_sheet, timeline, chapter_outlines }` |

**查询：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/query/entity` | `{ project_id, entity_id, at_chapter? }` | `{ entity: { name, type, state, relationships } }` |
| `POST /api/query/power-system` | `{ project_id }` | `{ content }` |
| `POST /api/query/foreshadowing` | `{ project_id, chapter? }` | `{ foreshadowing: [{ content, level, status, buried_chapter, payoff_chapter }] }` |
| `POST /api/query/golden-finger` | `{ project_id, chapter? }` | `{ golden_finger: { name, level, status, skills } }` |

**设定：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/settings/get` | `{ project_id, setting_type }` | `{ content, last_updated }` |
| `POST /api/settings/save` | `{ project_id, setting_type, content }` | `{ ok: true }` |

**LLM 配置：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/llm-configs/list` | `{}` | `{ configs: [{ id, name, provider, model, url, is_default }] }` |
| `POST /api/llm-configs/add` | `{ name, provider, model, url, api_key }` | `{ id }` |
| `POST /api/llm-configs/update` | `{ id, name?, provider?, model?, url?, api_key? }` | `{ ok: true }` |
| `POST /api/llm-configs/delete` | `{ id }` | `{ ok: true }` |
| `POST /api/llm-configs/set-default` | `{ id }` | `{ ok: true }` |
| `POST /api/llm-configs/test` | `{ id }` | `{ ok: true, latency_ms, model_info? }` 或 `{ ok: false, error }` |

**任务管理：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/tasks/status` | `{ task_id }` | `{ task_id, type, status, progress: { current_step, total_steps, step_name, elapsed_ms }, result? }` |
| `POST /api/tasks/pause` | `{ task_id }` | `{ ok: true }` |
| `POST /api/tasks/resume` | `{ task_id }` | `{ ok: true }` |
| `POST /api/tasks/cancel` | `{ task_id }` | `{ ok: true }` |

**SSE 进度推送：**

| 接口 | 参数 | 推送格式 |
|------|------|----------|
| `GET /api/events?task_id={task_id}` | query param | `event: step_start|step_progress|step_complete|step_failed|task_complete|task_failed` + `data: { task_id, step, payload }` |

**学习模式：**

| 接口 | 请求体 | 返回 |
|------|--------|------|
| `POST /api/learn/list` | `{ project_id }` | `{ patterns: [{ pattern_type, description, category, importance, learned_at }] }` |
| `POST /api/learn/add` | `{ project_id, pattern_type, description, category?, importance? }` | `{ ok: true, duplicated? }` |

**统一错误格式：**

```json
{
  "ok": false,
  "error": {
    "code": "PROJECT_NOT_FOUND" | "TASK_NOT_FOUND" | "CHAPTER_NOT_FOUND" | "LLM_CALL_FAILED" | "FILE_NOT_FOUND" | "VALIDATION_ERROR" | "INTERNAL_ERROR",
    "message": "项目不存在",
    "details": {}
  }
}
```

#### 4.2.3 数据模型

**新增数据文件（后端自行管理）：**

**1. `project_registry.json`（项目注册表）**

存储位置：应用数据目录（如 `~/.webnovel-app/project_registry.json`）

```json
{
  "projects": [
    {
      "id": "uuid",
      "title": "书名",
      "root_path": "/path/to/book-project",
      "genre": "玄幻",
      "target_words": 300000,
      "target_chapters": 200,
      "created_at": "2026-05-12T10:00:00Z",
      "last_opened": "2026-05-12T10:00:00Z"
    }
  ],
  "active_project_id": "uuid"
}
```

**2. `llm_configs.json`（LLM 配置）**

存储位置：应用数据目录（如 `~/.webnovel-app/llm_configs.json`）

```json
{
  "configs": [
    {
      "id": "uuid",
      "name": "Claude Sonnet 4.6",
      "provider": "anthropic",
      "model": "claude-sonnet-4-6-20250514",
      "url": "https://api.anthropic.com",
      "api_key_encrypted": "enc:...",
      "is_default": true
    },
    {
      "id": "uuid",
      "name": "DeepSeek V3",
      "provider": "openai_compatible",
      "model": "deepseek-chat",
      "url": "https://api.deepseek.com",
      "api_key_encrypted": "enc:...",
      "is_default": false
    }
  ]
}
```

- `api_key` 使用 `cryptography` 库 AES-GCM 加密存储，启动时从环境变量 `APP_SECRET_KEY` 读取密钥，未设置时 fallback 到明文（开发环境）

**3. `task_state.json`（任务状态持久化）**

存储位置：项目目录（`{project_root}/.webnovel/workflow_state.json`）

```json
{
  "active_task": {
    "task_id": "uuid",
    "type": "draft" | "review" | "plan",
    "chapter_num": 5,
    "volume_id": 1,
    "status": "running" | "paused" | "cancelled",
    "current_step": 3,
    "total_steps": 6,
    "step_results": {
      "1": { "status": "completed", "output": "...", "completed_at": "..." },
      "2": { "status": "completed", "output": "正文/第0005章-xxx.md", "completed_at": "..." },
      "3": { "status": "running", "started_at": "..." }
    },
    "started_at": "2026-05-12T10:00:00Z",
    "last_updated": "2026-05-12T10:10:00Z"
  }
}
```

- 每步完成后立即持久化，进程崩溃后可读取此文件恢复执行
- 同一项目同一时间只允许一个 active_task

**沿用现有数据格式（只读/只写，不改 schema）：**

| 文件 | 用途 | 操作 |
|------|------|------|
| `.webnovel/state.json` | 项目配置+进度快照 | 读/写（通过 update_state 模块） |
| `.webnovel/index.db` | SQLite 实体存储 | 读/写（通过 SQLiteAccess 模块） |
| `.story-system/` | 合同树 | 读/写（通过 story_system 模块） |
| `正文/第{NNNN}章-{title}.md` | 章节正文 | 读/写 |
| `大纲/总纲.md` | 总纲 | 读/写 |
| `大纲/第{volume_id}卷-*.md` | 卷规划产物 | 读/写 |
| `设定集/*.md` | 设定文件 | 读/写 |
| `审查报告/第{N}章审查报告.md` | 审查报告 | 读/写 |
| `.webnovel/tmp/` | 中间产物 | 读/写 |
| `.webnovel/summaries/ch{NNNN}.md` | 章节摘要 | 读/写 |
| `references/csv/*.csv` | CSV 知识库 | 只读 |
| `.webnovel/project_memory.json` | 学习模式数据 | 读/追加 |

#### 4.2.4 并发模型

- **异步基础**：FastAPI 原生 `asyncio`，LLM API 调用使用异步 SDK 方法（`client.messages.create(...)`），不阻塞其他请求
- **长任务串行化**：同一项目的起草/审查/规划任务使用 `asyncio.Lock(project_id)` 串行化，重复启动返回 409 Conflict
- **短请求无锁**：列表、查询、配置 CRUD 等短请求直接读文件，不加锁
- **文件写保护**：`state.json`、合同树等关键文件的写操作使用 `asyncio.Lock(f"{project_id}:{filename}")`，避免并发写导致脏数据
- **任务状态可见性**：长任务运行时状态存储在内存（`dict[task_id, TaskState]`）+ `workflow_state.json` 持久化，任何请求都可通过 `/api/tasks/status` 查询
- **前端并发安全**：多标签页同时操作同一项目时，长任务 Lock 保证后端不重复执行，前端通过 SSE 或轮询感知任务状态

#### 4.2.5 错误处理

**失败模式分类：**

| 类别 | 场景 | 处理策略 |
|------|------|----------|
| LLM 调用失败 | API 超时 / rate limit | 指数退避重试（最多 3 次），仍失败返回 `LLM_CALL_FAILED`，用户可手动重试 |
| LLM 调用失败 | API Key 无效 / 余额不足 | 立即返回错误，提示用户更新配置 |
| LLM 调用失败 | 返回内容不符合预期 schema | 记录原始响应，返回 `LLM_RESPONSE_INVALID`，标记当前步骤失败 |
| 文件操作失败 | 项目路径不存在 / 无权限 | 返回 `PROJECT_ROOT_INVALID` |
| 文件操作失败 | 合同树文件缺失 | 返回 `CONTRACT_MISSING`，提示先刷新合同 |
| 文件操作失败 | JSON 解析失败 / 文件损坏 | 返回 `FILE_CORRUPTED`，提示用户检查文件 |
| 任务执行异常 | 某一步骤失败 | 保存进度到 `workflow_state.json`，任务状态置 `failed`，用户可选择恢复或取消 |
| 任务执行异常 | 进程崩溃 / 重启 | 从 `workflow_state.json` 恢复，用户点"继续"从失败步骤重试 |
| 并发冲突 | 同一项目重复启动任务 | 返回 409，附带当前任务 ID 和进度 |
| 数据一致性 | state.json 与 index.db 不一致 | 记录警告日志，以 state.json 为准（投影层 fallback） |

**恢复机制：**

- 每步完成后立即持久化 `workflow_state.json`（task_id、当前步骤、步骤产物路径）
- 恢复时读取 `workflow_state.json`，跳过已完成步骤，从失败步骤继续
- 用户取消任务时清理临时文件（`.webnovel/tmp/` 下的中间产物保留不删）

### 4.3 核心逻辑实现

#### 4.3.1 ChapterOrchestrator 状态机

**6 步写章流程状态机：**

```
[INIT] ──draft()──▶ [STEP_1: context] ──▶ [STEP_2: drafting]
  │                                              │
  │                                              ▼
  │                                         [STEP_3: review]
  │                                              │
  │                   [STEP_6: commit] ◀── [STEP_4: polish]
  │                                              │
  │                   [STEP_5: fact_extract] ◀────┘
  │                                              │
  └──────────────────────────▶ [DONE] ◀──────────┘
```

**步骤定义：**

| Step | 名称 | 对应原 SKILL.md 步骤 | LLM 调用 | 产出物 |
|------|------|---------------------|----------|--------|
| 1 | 上下文构建 | Step 1: Context Assembly | 是 (context-agent) | 写作任务书 JSON |
| 2 | 正文起草 | Step 2: Draft | 是 (起草 prompt) | 正文草稿 Markdown |
| 3 | 审查 | Step 3: Review | 是 (reviewer) | 审查报告 JSON |
| 4 | 润色 | Step 4: Polish | 是 (润色 prompt) | 润色后正文 |
| 5 | 事实提取 | Step 5: Data Agent | 是 (data-agent) | commit JSON |
| 6 | 提交落库 | Step 6: Commit + Backup | 否 | state.json 更新 + 备份 |

**状态机核心类设计：**

```python
class ChapterOrchestrator:
    """6步写章流程编排器"""

    STEPS = [
        Step(name="上下文构建", fn=build_context, llm_required=True),
        Step(name="正文起草", fn=draft_chapter, llm_required=True),
        Step(name="审查", fn=review_chapter, llm_required=True),
        Step(name="润色", fn=polish_chapter, llm_required=True),
        Step(name="事实提取", fn=extract_facts, llm_required=True),
        Step(name="提交落库", fn=commit_chapter, llm_required=False),
    ]

    async def execute(self, project_id, chapter_num, mode="default"):
        """执行完整流程，每步完成后检查暂停信号"""
        for i, step in enumerate(self.STEPS):
            if self._is_cancelled():
                return TaskResult(status="cancelled", completed_steps=i)
            while self._is_paused():
                await asyncio.sleep(0.5)
            await self._run_step(i, project_id, chapter_num, mode)
            await self._persist_state(i + 1)

    def pause(self):
        """设置暂停信号，当前步骤完成后停止"""
        self._pause_flag.set()

    def resume(self):
        """恢复执行，从暂停的下一步继续"""
        self._pause_flag.clear()

    def cancel(self):
        """取消任务，清理锁和临时状态"""
        self._cancel_flag.set()
        self._pause_flag.clear()

    async def recover(self, project_id):
        """从 workflow_state.json 恢复中断的任务"""
        state = await self._load_workflow_state(project_id)
        if state and state["status"] in ("running", "paused"):
            resume_from = state["current_step"]
            for i in range(resume_from, len(self.STEPS)):
                await self._run_step(i, project_id, state["chapter_num"])
                await self._persist_state(i + 1)
```

**暂停/恢复/取消机制：**

- **暂停**：设置 `_pause_flag`，当前正在执行的步骤（LLM 调用）不会被中断（LLM API 不支持中途取消），完成后检查标志位并停止。用户可在暂停期间查看中间产物。
- **恢复**：清除 `_pause_flag`，从下一个未完成的步骤继续。读取 `workflow_state.json` 确认当前进度。
- **取消**：设置 `_cancel_flag`，行为同暂停但状态标记为 `cancelled`。不删除已生成的中间产物。
- **批量起草**：对章节范围 `[start, end]` 串行执行，每章完成后自动进入下一章。暂停/取消对整批生效。

#### 4.3.2 LLM 调用替代 Agent

原有的 3 个 subagent（context-agent、reviewer、data-agent）通过 Claude Code Agent tool 调用。Web 应用中改为直接调用 LLM API，使用原 agent 的 prompt 作为系统 prompt。

**Agent → LLM 映射：**

| 原 Agent | 新实现 | 系统 Prompt 来源 | 用户 Prompt 来源 |
|----------|--------|-----------------|-----------------|
| `context-agent` | `PromptBuilder.build_context_prompt()` | 原 `context-agent.md` 的指令部分 | 章节号 + 合同树 + 上一章摘要 |
| `reviewer` | `PromptBuilder.build_review_prompt()` | 原 `reviewer.md` 的指令部分 | 章节正文 + 审查 schema v6 |
| `data-agent` | `PromptBuilder.build_data_prompt()` | 原 `data-agent.md` 的指令部分 | 章节正文 + commit schema |
| 起草（无对应 agent） | `PromptBuilder.build_draft_prompt()` | SKILL.md Step 2 的指令 + Anti-AI 规则 | 写作任务书 JSON |
| 润色（无对应 agent） | `PromptBuilder.build_polish_prompt()` | SKILL.md Step 4 的指令 + polish-guide | 草稿 + 审查报告 |

**LLM 调用封装：**

```python
class LLMService:
    async def call(self, config_id, system_prompt, user_prompt, max_tokens=8192, temperature=0.7):
        """统一 LLM 调用入口，支持多模型路由"""
        config = await self._get_config(config_id)
        client = self._get_client(config)  # AnthropicClient 或 OpenAICompatibleClient

        for attempt in range(3):
            try:
                response = await client.chat(
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                self._record_usage(config_id, response.usage)
                return response.content
            except RateLimitError:
                await asyncio.sleep(2 ** attempt * 5)
            except APIError as e:
                if attempt == 2:
                    raise LLMCallFailed(f"API call failed after 3 retries: {e}")
                await asyncio.sleep(2 ** attempt)
```

**关键参数配置：**

| 调用场景 | 模型 | max_tokens | temperature | 说明 |
|----------|------|------------|-------------|------|
| 上下文构建（context-agent） | Sonnet | 8192 | 0.3 | 需要结构化输出，低温 |
| 正文起草 | Sonnet/Opus | 16384 | 0.8 | 创作场景，较高温度 |
| 审查（reviewer） | Sonnet | 8192 | 0.1 | 分析场景，极低温度 |
| 润色 | Sonnet | 16384 | 0.5 | 中等温度 |
| 事实提取（data-agent） | Sonnet | 4096 | 0.1 | 提取事实，低温 |
| 大纲规划 | Sonnet | 16384 | 0.5 | 规划场景 |
| 查询 | Haiku/Sonnet | 4096 | 0.1 | 查询场景，可用小模型 |

**Prompt 构建规则：**

- 系统 prompt = 原 agent 定义的核心指令 + 题材特定约束（从 profile 加载）
- 用户 prompt = 具体输入数据（章节内容、合同树等）
- 审查输出要求 JSON 格式，使用 `response_format` 参数约束
- 起草/润色输出为 Markdown 文本

#### 4.3.3 断点恢复逻辑

**触发场景：**
1. 用户主动暂停后恢复
2. 后端进程崩溃重启
3. LLM 调用超时后重试

**恢复流程：**

```
1. 读取 workflow_state.json
2. 校验 active_task 状态：
   - status="running" 或 "paused" → 可恢复
   - status="cancelled" → 不可恢复，提示用户重新启动
   - 无 active_task → 无需恢复
3. 确认当前步骤 (current_step) 和已完成步骤 (step_results)
4. 从 current_step + 1 开始继续执行
5. 已完成的步骤不重复执行，直接使用 step_results 中的产出物
6. 恢复后通过 SSE 推送完整进度（包括已完成的步骤状态）
```

**状态一致性保障：**
- `workflow_state.json` 是唯一的恢复真源
- 每次步骤完成后原子写入（先写临时文件，再 rename）
- 恢复时校验步骤产物文件是否存在，若丢失则重新执行该步骤

#### 4.3.4 SSE 推送事件格式

**事件类型与 payload：**

| 事件 | 触发时机 | payload 字段 |
|------|----------|-------------|
| `task_start` | 任务启动 | `{ task_id, type, chapter_num, total_steps, mode }` |
| `step_start` | 步骤开始 | `{ task_id, step_number, step_name, estimated_seconds }` |
| `step_progress` | 步骤进行中（可选，用于长 LLM 调用时的 token 流式输出） | `{ task_id, step_number, token_delta, partial_text? }` |
| `step_complete` | 步骤完成 | `{ task_id, step_number, step_name, elapsed_ms, output_path, preview }` |
| `step_failed` | 步骤失败 | `{ task_id, step_number, step_name, error_code, error_message, retryable }` |
| `task_paused` | 任务暂停 | `{ task_id, completed_steps, current_step_name }` |
| `task_resumed` | 任务恢复 | `{ task_id, resume_from_step }` |
| `task_complete` | 任务完成 | `{ task_id, total_elapsed_ms, final_status, result_summary }` |
| `task_failed` | 任务失败 | `{ task_id, failed_step, error_message, recoverable }` |
| `task_cancelled` | 任务取消 | `{ task_id, completed_steps }` |

**SSE 数据格式：**

```
event: step_complete
data: {"task_id": "uuid-xxx", "step_number": 3, "step_name": "审查", "elapsed_ms": 45200, "output_path": ".webnovel/tmp/review_ch5.json", "preview": {"issues_count": 2, "blocking": false}}

event: step_start
data: {"task_id": "uuid-xxx", "step_number": 4, "step_name": "润色", "estimated_seconds": 30}
```

**前端 SSE 客户端行为：**
- 调用 `POST /api/chapters/draft` 获取 task_id
- 建立 SSE 连接：`EventSource(/api/events?task_id={task_id})`
- 根据事件类型更新进度面板状态
- `step_complete` 事件时展示中间产物预览
- `task_complete` / `task_failed` 事件时关闭 SSE 连接，刷新章节列表

#### 4.3.5 Python 脚本内部化策略

原有 24 个子命令通过 CLI 调用，现改为 Python 内部直接导入。所有脚本逻辑位于外部插件目录 `CLAUDE_PLUGIN_ROOT/scripts/`，通过 `sys.path` 添加到 Python 路径后直接 import。

**脚本 → 内部模块映射：**

| 原脚本/子命令 | 内部化方式 | 目标模块 | 说明 |
|--------------|-----------|----------|------|
| `webnovel.py preflight` | 直接 import `data_modules.preflight` | `core.preflight` | 项目预检，文件完整性检查 |
| `webnovel.py story-system` | 直接 import `data_modules.story_system` | `core.story_system` | 生成/刷新合同树 |
| `webnovel.py review-pipeline` | 直接 import `data_modules.review_pipeline` | `core.review_pipeline` | 审查管线，报告生成 |
| `webnovel.py chapter-commit` | 直接 import `data_modules.chapter_commit` | `core.chapter_commit` | 章节提交，accepted/rejected |
| `webnovel.py update-state` | 直接 import `data_modules.update_state` | `core.update_state` | 原子更新 state.json |
| `webnovel.py backup` | 直接 import `data_modules.backup_manager` | `core.backup_manager` | 文件级备份（替代 Git） |
| `webnovel.py where` | 直接 import `data_modules.project_locator` | `core.project_locator` | 解析项目根路径 |
| `webnovel.py placeholder-scan` | 直接 import `data_modules.placeholder_scan` | `core.placeholder_scan` | 扫描正文占位符 |
| `webnovel.py master-outline-sync` | 直接 import `data_modules.master_outline_sync` | `core.master_outline_sync` | 总纲同步写回 |
| `reference_search.py` | 直接 import `reference_search` | `core.reference_search` | BM25 CSV 检索 |
| `validate_csv.py` | 直接 import `validate_csv` | `core.validate_csv` | CSV schema 校验 |
| `webnovel.py memory-contract` | 直接 import `data_modules.memory_contract` | `core.memory_contract` | 记忆合同管理 |

**导入策略：**

```python
# 启动时将插件脚本目录加入 sys.path
import sys
from pathlib import Path

SCRIPTS_DIR = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", "/path/to/plugin/scripts"))
sys.path.insert(0, str(SCRIPTS_DIR))

# 然后直接 import
from data_modules import story_system, review_pipeline, chapter_commit
from reference_search import BM25Searcher
from validate_csv import validate_schema
```

**不内部化的部分：**
- `context-agent.md`、`reviewer.md`、`data-agent.md` — 这些是 agent 定义文件，内容转为 PromptBuilder 的系统 prompt 字符串，不作为模块导入
- SKILL.md 的步骤流程 — 流程逻辑编码到 Orchestrator 中，不直接读取 SKILL.md 文件

**依赖处理：**
- 50+ `data_modules/` 模块之间存在内部依赖，一并加入 `sys.path`
- 确保 `python -X utf8` 效果：启动时设置 `sys.stdout.reconfigure(encoding='utf-8')`

## 5. 备选方案 (Alternatives Considered)

无

## 6. 业界调研 (Industry Research)

无

## 7. 测试计划 (Test Plan)

### 7.1 测试策略

采用分层测试，覆盖从单元到 E2E 的全链路：

```
┌─────────────────────────────────────────┐
│ E2E 测试 (Playwright)                   │ ← 关键用户流程，UI 层
│   - 起草完整流程  - 审查流程             │
│   - 项目管理      - 模型配置             │
├─────────────────────────────────────────┤
│ 集成测试 (pytest)                       │ ← API 层 + 文件/DB 交互
│   - API 端点 CRUD  - LLM 调用模拟        │
│   - 文件读写        - SSE 推送验证        │
├─────────────────────────────────────────┤
│ 单元测试 (pytest)                       │ ← 纯函数逻辑
│   - PromptBuilder   - LLMService 重试    │
│   - 状态机转换      - 加密/解密          │
│   - CSV 检索        - 数据解析           │
└─────────────────────────────────────────┘
```

**覆盖率目标：80%+**

### 7.2 单元测试

**PromptBuilder 测试：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_build_context_prompt_loads_contract` | 正确加载合同树，系统 prompt 包含章节信息 |
| `test_build_review_prompt_schema_v6` | 审查 prompt 包含 v6 schema 要求，输出格式为 JSON |
| `test_build_draft_prompt_anti_ai_rules` | 起草 prompt 注入 8 条 Anti-AI 规则 |
| `test_build_polish_prompt_with_review_report` | 润色 prompt 包含审查报告中的问题列表 |
| `test_build_data_prompt_commit_schema` | 数据提取 prompt 要求输出符合 commit JSON schema |

**LLMService 测试：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_retry_on_rate_limit` | RateLimitError 触发指数退避重试，3 次后抛出 LLMCallFailed |
| `test_no_retry_on_auth_error` | 401 错误立即抛出，不重试 |
| `test_fallback_to_default_model` | 指定模型不可用时 fallback 到默认模型 |
| `test_token_usage_tracking` | 每次调用记录 prompt_tokens + completion_tokens |
| `test_openai_compatible_client_call` | OpenAI 兼容接口调用 DeepSeek，参数正确传递 |

**ChapterOrchestrator 状态机测试：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_full_flow_6_steps` | 无中断时 6 步全部完成，状态变为 DONE |
| `test_pause_after_step_2` | 暂停后 current_step=2，不继续执行步骤 3 |
| `test_resume_from_pause` | 恢复后从步骤 3 继续，完成剩余步骤 |
| `test_cancel_mid_execution` | 取消后状态为 cancelled，已完成的步骤产物保留 |
| `test_recovery_from_state_file` | 模拟进程崩溃后从 workflow_state.json 恢复，跳过已完成步骤 |
| `test_double_start_returns_409` | 同一项目重复启动返回 409 Conflict |
| `test_blocking_review_stops_flow` | 审查 blocking=true 时后续步骤不执行 |

**数据访问层测试：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_fileio_read_utf8_with_bom` | 正确读取 UTF-8 with BOM 的 CSV 文件 |
| `test_fileio_write_json_atomic` | JSON 写入使用临时文件 + rename，保证原子性 |
| `test_sqlite_access_query_entity` | 从 index.db 查询实体，返回正确字段 |
| `test_project_registry_crud` | 项目注册表的增删改查 |
| `test_task_state_persist_and_load` | 任务状态持久化后能正确恢复 |

**脚本内部化测试：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_preflight_import_succeeds` | 正确 import data_modules.preflight，路径配置无误 |
| `test_story_system_module_generates_contract` | story_system 模块能生成合同树文件 |
| `test_reference_search_bm25_returns_results` | BM25 检索 CSV 返回匹配结果 |
| `test_validate_csv_schema_valid` | 合法 CSV 通过校验 |
| `test_validate_csv_schema_invalid` | 缺失列的 CSV 返回具体错误字段 |

### 7.3 集成测试

**API 端点测试（使用 httpx AsyncClient + pytest-asyncio）：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_projects_create_and_list` | 创建项目后 list 能返回 |
| `test_projects_overview_returns_progress` | 概览返回章节进度、字数统计 |
| `test_chapters_list_returns_all` | 返回所有章节，含未写章节占位 |
| `test_chapters_get_returns_content` | 获取已写章节的 Markdown 正文 |
| `test_chapters_save_updates_word_count` | 保存正文后 word_count 正确 |
| `test_draft_returns_task_id` | 起草接口返回 task_id |
| `test_review_start_returns_task_id` | 审查接口返回 task_id |
| `test_tasks_status_reflects_progress` | 任务状态接口返回当前步骤和耗时 |
| `test_tasks_pause_resumes_correctly` | 暂停后恢复，从断点继续不重复执行 |
| `test_tasks_cancel_cleans_up` | 取消后任务状态变为 cancelled |
| `test_llm_configs_test_connection` | 测试连接接口返回延迟和模型信息 |
| `test_concurrent_draft_returns_409` | 同项目并发起草返回 409 |

**LLM 调用集成测试（使用 mocked LLM）：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_draft_flow_with_mock_llm` | 模拟 LLM 返回草稿，6 步流程完整跑通 |
| `test_review_flow_with_mock_llm` | 模拟 LLM 返回审查 JSON，报告正确落盘 |
| `test_llm_failure_marks_step_failed` | LLM 调用失败时步骤状态为 failed |
| `test_retry_succeeds_on_third_attempt` | 前 2 次失败、第 3 次成功，流程继续 |

**SSE 推送集成测试：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_sse_emits_step_start_events` | 每步开始时 SSE 推送 step_start |
| `test_sse_emits_step_complete_events` | 步骤完成时推送 step_complete，含 preview |
| `test_sse_emits_task_complete_at_end` | 任务完成时推送 task_complete |
| `test_sse_closes_on_task_done` | task_complete 后 SSE 连接关闭 |
| `test_sse_handles_task_failure` | 任务失败时推送 task_failed，含错误信息 |

**文件系统集成测试（使用真实项目文件）：**

| 测试用例 | 验证内容 |
|----------|---------|
| `test_read_existing_chapter_file` | 读取已有章节正文，内容完整 |
| `test_write_new_chapter_creates_file` | 起草新章节，生成正确路径的 Markdown 文件 |
| `test_update_state_json_atomic` | state.json 更新后所有字段一致，无脏数据 |
| `test_csv_knowledge_base_readable` | 9 张 CSV 都能被 BM25 检索 |
| `test_story_system_contract_parsable` | 合同树 JSON 能被 story_system 模块解析 |

### 7.4 E2E 测试（Playwright）

**关键用户流程：**

| 测试用例 | 步骤 | 预期 |
|----------|------|------|
| `test_full_draft_flow` | 1. 打开项目首页 2. 进入章节列表 3. 点击起草 4. 等待进度完成 | 6 步全部完成，章节状态变为"已完成" |
| `test_view_intermediate_products` | 起草过程中暂停 | 能看到已完成的中间产物（任务书、草稿、审查报告） |
| `test_resume_after_pause` | 暂停后点击恢复 | 从断点继续，不重复执行已完成步骤 |
| `test_review_existing_chapter` | 选择已写章节 → 点击审查 | 审查报告展示问题清单，阻断项高亮 |
| `test_manage_llm_configs` | 添加新模型配置 → 测试连接 → 设为默认 | 列表显示新模型，默认标记正确 |
| `test_create_new_project` | 填写项目信息 → 创建 → 切换到此项目 | 新项目出现在列表，切换成功 |
| `test_query_character` | 查询页面输入角色名 | 返回角色设定信息 |
| `test_edit_chapter_content` | 打开章节 → 编辑正文 → 保存 | 字数更新，保存成功 |
| `test_batch_draft_chapters` | 选择章节 3-5 → 批量起草 | 3 章串行完成，每章状态正确 |

### 7.5 测试数据准备

**测试夹具（conftest.py）：**

```python
@pytest.fixture
def sample_project(tmp_path):
    """创建一个测试用项目，含 state.json、合同树、3 个已写章节"""
    # 在 tmp_path 下构建完整项目结构
    # 返回 project_id 和 root_path

@pytest.fixture
def mock_llm_response():
    """模拟 LLM 返回内容，按调用场景返回不同文本"""
    return {
        "context": "{...写作任务书JSON...}",
        "draft": "正文草稿内容...",
        "review": '{"issues": [], "summary": "..."}',
        "polish": "润色后正文内容...",
        "data": "{...commit JSON...}",
    }

@pytest.fixture
def mock_anthropic_client(mock_llm_response):
    """替换 AnthropicClient，返回预定义的 mock 响应"""

@pytest.fixture
def sample_csv_data(tmp_path):
    """生成 9 张测试 CSV，含合法数据"""
```

### 7.6 测试执行

| 阶段 | 触发时机 | 执行内容 |
|------|----------|---------|
| 开发中 | 每次保存文件 | 相关单元测试（通过 hooks） |
| 提交前 | git commit 前 | 全部单元 + 集成测试 |
| PR 创建 | 推送到分支 | 全部测试 + E2E |
| 本地验证 | 手动运行 | `pytest --cov=backend --cov-report=html` |

**命令：**

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定模块
pytest tests/unit/test_orchestrator.py -v
pytest tests/integration/test_api_chapters.py -v

# 覆盖率检查
pytest --cov=backend --cov-report=term-missing --cov-report=html

# E2E 测试
pytest tests/e2e/ --browser chromium --headed
```

## 8. 可观测性 & 运维 (Observability & Operations)

无

## 9. Changelog

| 日期 | 变更内容 | 作者 |
|------|----------|------|
| 2026-05-12 | 初始创建，填写第 1-3 章节（背景、目标、需求） | cajoj0313 |
| 2026-05-12 | 补充 4.1-4.2 章节（架构、组件、接口、数据模型、并发、错误处理） | cajoj0313 |
| 2026-05-12 | 补充 4.3 章节（核心逻辑实现：状态机、LLM 替代、断点恢复、SSE、脚本内部化） | cajoj0313 |
| 2026-05-12 | 补充第 5/6/8 节（无）、第 7 节（测试计划：分层策略、单元/集成/E2E 用例、测试数据） | cajoj0313 |

## 10. 参考资料 (References)

- 项目现有 SKILL.md 文件：`webnovel-write/SKILL.md`、`webnovel-review/SKILL.md`、`webnovel-plan/SKILL.md`、`webnovel-query/SKILL.md`、`webnovel-learn/SKILL.md`
- 审查 Schema v6：`references/review-schema.md`
- CSV 数据规范：`references/csv/README.md`
- 核心约束：`references/shared/core-constraints.md`
