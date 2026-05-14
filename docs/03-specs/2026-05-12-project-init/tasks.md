# 实施任务清单

> 由 spec.md 生成
> 任务总数: 18
> 核心原则: 先搭建基础设施和后端核心层，再逐步构建前端页面——后端先于前端，基础先于业务，每个模块先 API 后 UI。

## 依赖关系总览

```
Task 1 (项目脚手架 - 后端)
  ↓
Task 2 (项目脚手架 - 前端)
  ↓
Task 3 (数据访问层 - FileIO/SQLite/ProjectRegistry)
  ↓
Task 4 (LLM Client 层 - Anthropic/OpenAI兼容)
  ↓
Task 5 (跨切面 - 错误码/日志/配置体系)
  ↙         ↘
Task 6      Task 7
(LLM配置)   (项目管理)
  ↓           ↓
Task 8      Task 9
(章节API)   (章节Orchestrator)
  ↓           ↓
Task 10     Task 11
(审查API)   (大纲规划API)
  ↓           ↓
Task 12     Task 13
(查询API)   (设定API)
  ↓           ↓
Task 14     Task 15
(学习API)   (SSE推送)
  ↓
Task 16 (前端 - 项目首页 + 布局框架)
  ↓
Task 17 (前端 - 章节管理页 + 编辑器)
  ↓
Task 18 (前端 - 其余页面 + 集成测试)
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `backend/` 目录 | 新建 | Task 1-15 | 后端 FastAPI 应用全量创建 |
| `frontend/` 目录 | 新建 | Task 2, 16-18 | 前端 Vue 3 应用全量创建 |
| `pyproject.toml` | 新建 | Task 1 | Python 项目配置 |
| `package.json` | 新建 | Task 2 | Node.js 项目配置 |
| `~/.webnovel-app/project_registry.json` | 新建(运行时) | Task 7 | 项目注册表 |
| `~/.webnovel-app/llm_configs.json` | 新建(运行时) | Task 6 | LLM 配置 |

### 受影响接口

无现有接口受影响（全新项目）。

### 构建系统变更

- `pyproject.toml`: 定义 Python 依赖 (fastapi, uvicorn, anthropic, openai, cryptography 等)
- `package.json`: 定义 Node.js 依赖 (vue, vite, element-plus, pinia, axios 等)

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | spec 中提到的 `CLAUDE_PLUGIN_ROOT/scripts/` 目录路径在运行时动态解析 | Task 9, 10, 11 | 假设启动时可通过环境变量 `CLAUDE_PLUGIN_ROOT` 获取，否则 fallback 到默认路径 |
| 2 | Python 脚本的 `data_modules/` 模块结构未知 | Task 9, 10, 11 | 假设可通过 `sys.path` 导入；若模块不存在，先实现 stub 返回占位响应 |
| 3 | 现有 `.webnovel/state.json`、`.story-system/` 等文件 schema 可能有未文档化的字段 | Task 3, 7, 8 | 采用宽松解析策略，只读取已知字段，忽略未知字段 |
| 4 | API Key 加密的 `APP_SECRET_KEY` 未配置时 fallback 到明文 | Task 6 | 开发环境允许明文，生产环境强制要求环境变量 |
| 5 | spec 中的 `mode` 参数 (`default`/`fast`/`minimal`) 的具体含义未明确定义 | Task 9 | 假设 `default` 为完整 6 步流程，`fast`/`minimal` 后续扩展，当前仅实现 `default` |

## 任务列表

### 任务 1: [x] 后端项目脚手架
- 文件: `backend/` (新建目录), `backend/pyproject.toml` (新建), `backend/main.py` (新建), `backend/app/__init__.py` (新建)
- 依赖: 无
- spec 映射: spec 章节 4.1 (整体架构)
- 说明: 初始化 FastAPI 项目结构，创建基础目录和配置文件
- context:
  - `backend/main.py` — FastAPI 应用入口
  - `backend/app/` — 应用核心代码目录
  - `backend/pyproject.toml` — Python 依赖和构建配置
- 验收标准:
  - [x] `uvicorn backend.main:app --reload` 启动成功，返回 health check 响应
  - [x] `pyproject.toml` 包含所有 spec 中提到的依赖声明
- 子任务:
  - [x] 1.1: 创建 `backend/` 目录结构
  - [x] 1.2: 创建 `pyproject.toml` 声明依赖
  - [x] 1.3: 创建 `main.py` FastAPI 入口 + health endpoint
  - [x] 1.4: 创建 `app/` 子目录 (__init__.py)

### 任务 2: [x] 前端项目脚手架
- 文件: `frontend/` (新建目录), `frontend/package.json` (新建), `frontend/vite.config.ts` (新建), `frontend/src/main.ts` (新建), `frontend/src/App.vue` (新建)
- 依赖: Task 1 (需要确认项目整体结构)
- spec 映射: spec 章节 4.1 (整体架构), 4.2.1 (前端模块划分)
- 说明: 初始化 Vue 3 + Vite + Element Plus 项目
- context:
  - `frontend/package.json` — Node.js 依赖声明
  - `frontend/vite.config.ts` — Vite 构建配置 + CORS proxy
  - `frontend/src/App.vue` — 根组件
- 验收标准:
  - [x] `npm install && npm run dev` 启动成功，页面可访问
  - [x] Element Plus 正确注册
  - [x] `package.json` 包含所有 spec 中提到的依赖
- 子任务:
  - [x] 2.1: 使用 Vite 创建 Vue 3 项目
  - [x] 2.2: 安装 Element Plus、Pinia、Axios
  - [x] 2.3: 配置 Vite (代理到后端 8000 端口)
  - [x] 2.4: 创建 `App.vue` 根组件 + 路由框架

### 任务 3: [x] 数据访问层
- 文件: `backend/app/data/file_io.py` (新建), `backend/app/data/sqlite_access.py` (新建), `backend/app/data/project_registry.py` (新建), `backend/app/data/task_store.py` (新建)
- 依赖: Task 1
- spec 映射: spec 章节 4.2.1 (Layer 5 — Data Access), 4.2.3 (数据模型)
- 说明: 实现文件读写、SQLite 访问、项目注册表、任务状态持久化
- context:
  - `backend/app/data/file_io.py` — JSON/Markdown/CSV 统一读写，UTF-8 编码处理
  - `backend/app/data/sqlite_access.py` — index.db 的读写封装
  - `backend/app/data/project_registry.py` — project_registry.json 读写
  - `backend/app/data/task_store.py` — workflow_state.json 持久化
- 验收标准:
  - [x] 编译通过且无新 warning (pyright 或 mypy 通过)
  - [x] `FileIO` 正确读写 JSON/Markdown/CSV (UTF-8 with BOM)
  - [x] `ProjectRegistryStore` 支持 CRUD 操作
  - [x] `TaskStore` 支持原子写入（临时文件 + rename）
- 子任务:
  - [x] 3.1: 实现 FileIO (read_json, write_json, read_markdown, read_csv)
  - [x] 3.2: 实现 SQLiteAccess (查询 entities/relationships 等表)
  - [x] 3.3: 实现 ProjectRegistryStore (CRUD project_registry.json)
  - [x] 3.4: 实现 TaskStore (workflow_state.json 原子读写)

### 任务 4: [x] LLM Client 层
- 文件: `backend/app/llm/anthropic_client.py` (新建), `backend/app/llm/openai_client.py` (新建), `backend/app/llm/model_router.py` (新建)
- 依赖: Task 1
- spec 映射: spec 章节 4.2.1 (Layer 4 — LLM Client), 4.3.2 (LLM 调用替代 Agent)
- 说明: 实现 Anthropic SDK 和 OpenAI 兼容接口的客户端封装
- context:
  - `backend/app/llm/anthropic_client.py` — Claude API 调用封装
  - `backend/app/llm/openai_client.py` — OpenAI 兼容接口调用封装
  - `backend/app/llm/model_router.py` — 根据配置选择模型，支持 fallback
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] `AnthropicClient.chat()` 正确调用 Claude API 并返回响应
  - [x] `OpenAICompatibleClient.chat()` 正确调用 OpenAI 兼容接口
  - [x] `ModelRouter` 根据 provider 选择正确的客户端
- 子任务:
  - [x] 4.1: 实现 AnthropicClient (async chat 方法)
  - [x] 4.2: 实现 OpenAICompatibleClient (async chat 方法)
  - [x] 4.3: 实现 ModelRouter (配置解析 + 客户端选择 + fallback)

### 任务 5: [x] 跨切面 - 错误码/日志/配置体系
- 文件: `backend/app/core/error_codes.py` (新建), `backend/app/core/logger.py` (新建), `backend/app/core/config.py` (新建), `backend/app/models/schemas.py` (新建)
- 依赖: Task 1
- spec 映射: spec 章节 4.2.2 (统一错误格式), 3.2 (非功能性需求 - 可观测)
- 说明: 定义全局错误码体系、日志格式、配置加载、统一响应/请求 schema
- context:
  - `backend/app/core/error_codes.py` — 错误码枚举 (PROJECT_NOT_FOUND, TASK_NOT_FOUND, 等)
  - `backend/app/core/logger.py` — 结构化日志配置
  - `backend/app/core/config.py` — 应用配置 (APP_SECRET_KEY 等)
  - `backend/app/models/schemas.py` — Pydantic 请求/响应模型
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] 所有 spec 中定义的错误码已定义
  - [x] 统一错误响应格式符合 spec 定义
  - [x] 请求/响应 schema 与 spec 接口定义一致
- 子任务:
  - [x] 5.1: 定义错误码枚举和统一错误响应模型
  - [x] 5.2: 配置结构化日志
  - [x] 5.3: 加载应用配置 (环境变量读取)
  - [x] 5.4: 定义所有 API 的 Pydantic 请求/响应模型

### 任务 6: [x] LLM 配置管理 API
- 文件: `backend/app/api/llm_config_router.py` (新建), `backend/app/services/llm_service.py` (新建)
- 依赖: Task 3, Task 4, Task 5
- spec 映射: spec 章节 3.1 (模块一), 4.2.2 (LLM 配置接口)
- 说明: 实现 LLM 配置的 CRUD API 和测试连接功能
- context:
  - `backend/app/api/llm_config_router.py` — /api/llm-configs/* 路由
  - `backend/app/services/llm_service.py` — 多模型路由、API Key 管理、调用封装、重试
  - `backend/app/data/project_registry.py` — 读取 LLM 配置存储
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/llm-configs/list 返回配置列表
  - [x] POST /api/llm-configs/add 成功添加配置
  - [x] POST /api/llm-configs/test 返回连接测试结果
  - [x] API Key 加密存储 (使用 APP_SECRET_KEY)
- 子任务:
  - [x] 6.1: 实现 LLM 配置 CRUD 服务
  - [x] 6.2: 实现 API Key 加密/解密
  - [x] 6.3: 实现测试连接 API
  - [x] 6.4: 注册路由到 FastAPI

### 任务 7: [x] 小说项目管理 API
- 文件: `backend/app/api/project_router.py` (新建), `backend/app/services/project_service.py` (新建)
- 依赖: Task 3, Task 5, Task 6
- spec 映射: spec 章节 3.1 (模块二), 4.2.2 (项目相关接口)
- 说明: 实现项目 CRUD API 和概览查询
- context:
  - `backend/app/api/project_router.py` — /api/projects/* 路由
  - `backend/app/services/project_service.py` — 项目配置管理、project_registry.json 读写
  - `backend/app/data/project_registry.py` — 底层存储
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/projects/list 返回项目列表
  - [x] POST /api/projects/create 成功创建项目
  - [x] POST /api/projects/overview 返回项目进度信息
  - [x] POST /api/projects/delete 删除项目（不移除文件）
- 子任务:
  - [x] 7.1: 实现 ProjectService (CRUD + 概览)
  - [x] 7.2: 实现项目路由
  - [x] 7.3: 实现项目预检逻辑 (调用 webnovel.py preflight 等价逻辑)

### 任务 8: [x] 章节管理 API (列表/查看/编辑)
- 文件: `backend/app/api/chapter_router.py` (新建), `backend/app/services/chapter_service.py` (新建)
- 依赖: Task 3, Task 5, Task 7
- spec 映射: spec 章节 3.1 (模块三), 4.2.2 (章节相关接口)
- 说明: 实现章节列表、正文查看/编辑 API
- context:
  - `backend/app/api/chapter_router.py` — /api/chapters/* 路由
  - `backend/app/services/chapter_service.py` — 章节列表、正文读写
  - `backend/app/data/file_io.py` — Markdown 文件读写
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/chapters/list 返回章节列表 (含未写章节占位)
  - [x] POST /api/chapters/get 返回已写章节 Markdown 正文
  - [x] POST /api/chapters/save 保存正文并更新 word_count
- 子任务:
  - [x] 8.1: 实现章节列表服务 (扫描 正文/ 目录)
  - [x] 8.2: 实现章节正文读取/保存
  - [x] 8.3: 实现字数统计
  - [x] 8.4: 注册路由

### 任务 9: [x] 章节 Orchestrator (6 步写章流程)
- 文件: `backend/app/services/chapter_orchestrator.py` (新建), `backend/app/services/prompt_builder.py` (新建)
- 依赖: Task 3, Task 4, Task 5, Task 6, Task 8
- spec 映射: spec 章节 4.2.1 (Layer 2 — ChapterOrchestrator), 4.3.1 (状态机), 4.3.2 (LLM 替代 Agent), 4.3.3 (断点恢复), 4.3.4 (SSE 推送)
- 说明: 实现 6 步写章流程的状态机、暂停/恢复/取消、PromptBuilder
- context:
  - `backend/app/services/chapter_orchestrator.py` — 6 步流程编排，步骤间状态机，暂停/恢复/取消
  - `backend/app/services/prompt_builder.py` — 构建 context-agent / reviewer / data-agent / 起草 / 润色的 prompt
  - `backend/app/data/task_store.py` — 任务状态持久化
  - `backend/app/llm/model_router.py` — LLM 调用
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] 6 步状态机正确执行 (mock LLM)
  - [x] 暂停/恢复/取消机制工作正常
  - [x] workflow_state.json 正确持久化
  - [x] PromptBuilder 能构建 5 种场景的 prompt
- 子任务:
  - [x] 9.1: 实现 ChapterOrchestrator 状态机框架
  - [x] 9.2: 实现暂停/恢复/取消机制
  - [x] 9.3: 实现断点恢复 (从 workflow_state.json)
  - [x] 9.4: 实现 PromptBuilder (5 种 prompt 构建)
  - [x] 9.5: 实现 SSE 事件推送集成

### 任务 10: [x] 审查功能 API
- 文件: `backend/app/api/review_router.py` (新建), `backend/app/services/review_service.py` (新建)
- 依赖: Task 3, Task 4, Task 5, Task 8, Task 9
- spec 映射: spec 章节 3.1 (模块四), 4.2.2 (审查相关接口)
- 说明: 实现单章审查、审查历史、审查报告 API
- context:
  - `backend/app/api/review_router.py` — /api/review/* 路由
  - `backend/app/services/review_service.py` — 审查流程 (加载参考→调用 LLM→生成报告→落库)
  - `backend/app/services/prompt_builder.py` — 构建审查 prompt
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/review/start 返回 task_id
  - [x] POST /api/review/history 返回审查历史
  - [x] POST /api/review/report 返回审查报告 (含问题清单)
  - [x] 审查报告使用 schema v6 格式
- 子任务:
  - [x] 10.1: 实现 ReviewService (审查流程)
  - [x] 10.2: 实现审查报告生成和落盘
  - [x] 10.3: 实现审查历史查询
  - [x] 10.4: 注册路由

### 任务 11: [x] 大纲规划 API
- 文件: `backend/app/api/plan_router.py` (新建), `backend/app/services/plan_orchestrator.py` (新建)
- 依赖: Task 3, Task 4, Task 5, Task 7, Task 9
- spec 映射: spec 章节 3.1 (模块五), 4.2.2 (大纲规划接口)
- 说明: 实现总纲查看/编辑、卷级大纲生成 API
- context:
  - `backend/app/api/plan_router.py` — /api/plan/* 路由
  - `backend/app/services/plan_orchestrator.py` — 9 步大纲规划流程编排
  - `backend/app/data/file_io.py` — Markdown/JSON 文件读写
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/plan/master-outline/get 返回总纲内容
  - [x] POST /api/plan/master-outline/save 保存总纲
  - [x] POST /api/plan/volume/start 返回 task_id 开始规划
  - [x] POST /api/plan/volume/get 返回节拍表/时间线/章纲
- 子任务:
  - [x] 11.1: 实现总纲查看/编辑 API
  - [x] 11.2: 实现 PlanOrchestrator 框架 (9 步流程)
  - [x] 11.3: 实现卷级规划 API
  - [x] 11.4: 注册路由

### 任务 12: [x] 查询功能 API
- 文件: `backend/app/api/query_router.py` (新建), `backend/app/services/query_service.py` (新建)
- 依赖: Task 3, Task 5, Task 7
- spec 映射: spec 章节 3.1 (模块六), 4.2.2 (查询接口)
- 说明: 实现角色/势力/伏笔/金手指查询 API
- context:
  - `backend/app/api/query_router.py` — /api/query/* 路由
  - `backend/app/services/query_service.py` — 查询聚合 (合同树 + index.db + 设定文件)
  - `backend/app/data/sqlite_access.py` — index.db 查询
  - `backend/app/data/file_io.py` — 设定文件读取
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/query/entity 返回实体信息
  - [x] POST /api/query/power-system 返回力量体系内容
  - [x] POST /api/query/foreshadowing 返回伏笔列表
  - [x] POST /api/query/golden-finger 返回金手指状态
- 子任务:
  - [x] 12.1: 实现 QueryService (多数据源聚合)
  - [x] 12.2: 实现角色/势力查询
  - [x] 12.3: 实现伏笔/金手指查询
  - [x] 12.4: 注册路由

### 任务 13: [x] 设定管理 API
- 文件: `backend/app/api/setting_router.py` (新建), `backend/app/services/setting_service.py` (新建)
- 依赖: Task 3, Task 5, Task 7
- spec 映射: spec 章节 3.1 (模块六), 4.2.2 (设定接口)
- 说明: 实现设定集查看/编辑 API
- context:
  - `backend/app/api/setting_router.py` — /api/settings/* 路由
  - `backend/app/services/setting_service.py` — 设定文件读写
  - `backend/app/data/file_io.py` — Markdown 文件读写
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/settings/get 返回设定内容
  - [x] POST /api/settings/save 保存设定
  - [x] 支持所有设定类型 (世界观、力量体系、主角卡等)
- 子任务:
  - [x] 13.1: 实现 SettingService (Markdown 文件读写)
  - [x] 13.2: 实现设定路由
  - [x] 13.3: 注册路由

### 任务 14: [x] 学习模式 API
- 文件: `backend/app/api/learn_router.py` (新建), `backend/app/services/learn_service.py` (新建)
- 依赖: Task 3, Task 5, Task 7
- spec 映射: spec 章节 3.1 (模块七), 4.2.2 (学习模式接口)
- 说明: 实现学习模式 (添加/查看/去重模式) API
- context:
  - `backend/app/api/learn_router.py` — /api/learn/* 路由
  - `backend/app/services/learn_service.py` — 学习模式管理
  - `backend/app/data/file_io.py` — project_memory.json 读写
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/learn/list 返回已学习模式列表
  - [x] POST /api/learn/add 添加新模式 (含去重检查)
  - [x] 重复模式返回 duplicated=true
- 子任务:
  - [x] 14.1: 实现 LearnService (CRUD + 去重)
  - [x] 14.2: 实现学习路由
  - [x] 14.3: 注册路由

### 任务 15: [x] 任务管理 API + SSE 推送
- 文件: `backend/app/api/task_router.py` (新建), `backend/app/api/sse_router.py` (新建), `backend/app/services/task_manager.py` (新建)
- 依赖: Task 3, Task 5, Task 9, Task 10, Task 11
- spec 映射: spec 章节 4.2.2 (任务管理接口, SSE 接口), 4.3.4 (SSE 推送事件格式)
- 说明: 实现任务暂停/恢复/取消/状态查询 API 和 SSE 实时推送
- context:
  - `backend/app/api/task_router.py` — /api/tasks/* 路由
  - `backend/app/api/sse_router.py` — /api/events SSE 路由
  - `backend/app/services/task_manager.py` — 任务状态管理 (内存 + 持久化)
  - `backend/app/data/task_store.py` — 任务状态持久化
- 验收标准:
  - [x] 编译通过且无新 warning
  - [x] POST /api/tasks/status 返回任务状态和进度
  - [x] POST /api/tasks/pause 设置暂停信号
  - [x] POST /api/tasks/resume 恢复执行
  - [x] POST /api/tasks/cancel 取消任务
  - [x] GET /api/events?task_id=xxx SSE 连接建立并推送事件
- 子任务:
  - [x] 15.1: 实现 TaskManager (状态管理 + 暂停/恢复/取消)
  - [x] 15.2: 实现任务状态 API
  - [x] 15.3: 实现 SSE 事件推送 (EventSource 兼容)
  - [x] 15.4: 注册路由

### 任务 16: [x] 前端 - 项目首页 + 布局框架
- 文件: `frontend/src/layouts/MainLayout.vue` (新建), `frontend/src/views/ProjectHome.vue` (新建), `frontend/src/router/index.ts` (新建), `frontend/src/api/` (新建目录)
- 依赖: Task 2, Task 5 (需要 API schema)
- spec 映射: spec 章节 4.2.1 (前端模块划分), 4.2.2 (项目相关接口)
- 说明: 实现主布局框架、路由、项目概览页、API 客户端封装
- context:
  - `frontend/src/layouts/MainLayout.vue` — 侧边栏 + 主内容区布局
  - `frontend/src/views/ProjectHome.vue` — 项目概览页 (进度、审查状态)
  - `frontend/src/router/index.ts` — Vue Router 配置
  - `frontend/src/api/` — Axios 请求封装
  - `frontend/src/stores/` — Pinia 状态管理
- 验收标准:
  - [x] 编译通过 (npm run build 成功)
  - [x] 页面可访问，布局正确 (侧边栏 + 主内容区)
  - [x] 项目列表可展示，切换项目功能正常
  - [x] API 客户端正确调用后端接口
- 子任务:
  - [x] 16.1: 实现 MainLayout (侧边栏 + 主内容区)
  - [x] 16.2: 配置 Vue Router
  - [x] 16.3: 实现 API 客户端 (Axios 封装)
  - [x] 16.4: 实现 Pinia stores (项目状态)
  - [x] 16.5: 实现 ProjectHome 页面

### 任务 17: [x] 前端 - 章节管理页 + 编辑器 + 执行进度面板
- 文件: `frontend/src/views/ChapterList.vue` (新建), `frontend/src/views/ChapterEditor.vue` (新建), `frontend/src/components/ExecutionProgress.vue` (新建), `frontend/src/components/ReviewReport.vue` (新建)
- 依赖: Task 8, Task 9, Task 10, Task 15, Task 16
- spec 映射: spec 章节 3.1 (模块三、模块四), 4.2.1 (ChapterList, ChapterEditor, ExecutionProgress, ReviewReport)
- 说明: 实现章节列表、Markdown 编辑器、执行进度面板 (SSE)、审查报告展示
- context:
  - `frontend/src/views/ChapterList.vue` — 章节列表 + 起草/审查按钮
  - `frontend/src/views/ChapterEditor.vue` — Markdown 编辑器
  - `frontend/src/components/ExecutionProgress.vue` — SSE 接收进度展示
  - `frontend/src/components/ReviewReport.vue` — 审查报告展示 (问题清单、阻断项高亮)
  - `frontend/src/stores/` — 章节/任务进度 stores
- 验收标准:
  - [x] 编译通过 (npm run build 成功)
  - [x] 章节列表正确展示，含状态标识
  - [x] 起草按钮点击后显示进度面板
  - [x] SSE 实时推送步骤进度
  - [x] 审查报告展示问题清单和阻断项
  - [x] Markdown 编辑器可查看/编辑正文
- 子任务:
  - [x] 17.1: 实现 ChapterList (列表 + 状态标识 + 起草/审查按钮)
  - [x] 17.2: 实现 ChapterEditor (Markdown 编辑器)
  - [x] 17.3: 实现 ExecutionProgress (SSE 客户端 + 进度展示)
  - [x] 17.4: 实现 ReviewReport (审查报告展示)

### 任务 18: [x] 前端 - 其余页面 + 集成测试
- 文件: `frontend/src/views/PlanView.vue` (新建), `frontend/src/views/SettingView.vue` (新建), `frontend/src/views/QueryView.vue` (新建), `frontend/src/views/LLMConfigView.vue` (新建), `frontend/src/views/LearnView.vue` (新建), `tests/` (新建目录)
- 依赖: Task 11, Task 12, Task 13, Task 14, Task 6, Task 17
- spec 映射: spec 章节 3.1 (模块一、模块五、模块六、模块七), 第 7 节 (测试计划)
- 说明: 实现剩余前端页面 (规划、设定、查询、LLM 配置、学习模式) 和基础测试
- context:
  - `frontend/src/views/PlanView.vue` — 大纲规划页面
  - `frontend/src/views/SettingView.vue` — 设定集查看/编辑
  - `frontend/src/views/QueryView.vue` — 设定查询
  - `frontend/src/views/LLMConfigView.vue` — 模型配置管理
  - `frontend/src/views/LearnView.vue` — 学习模式
  - `tests/` — 测试目录
- 验收标准:
  - [x] 编译通过 (npm run build 成功)
  - [x] 所有页面可访问并正确调用后端 API
  - [x] LLM 配置管理页面可添加/删除/测试连接
  - [x] 规划页面可展示总纲和卷规划产物
  - [x] 查询页面可展示角色/伏笔等信息
  - [x] 至少 5 个后端单元测试通过
- 子任务:
  - [x] 18.1: 实现 LLMConfigView
  - [x] 18.2: 实现 PlanView
  - [x] 18.3: 实现 SettingView
  - [x] 18.4: 实现 QueryView
  - [x] 18.5: 实现 LearnView
  - [x] 18.6: 编写后端单元测试 (至少 5 个)

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
|-----------|------|------|
| 1. 背景 | Task 1-2 | 项目脚手架搭建 |
| 2. 目标 | All | 整体目标，所有任务共同实现 |
| 3.1 模块一 (模型配置) | Task 6, 18.1 | LLM 配置 API + 前端页面 |
| 3.1 模块二 (项目管理) | Task 7, 16.5 | 项目管理 API + 项目首页 |
| 3.1 模块三 (章节管理) | Task 8, 9, 17.1-17.3 | 章节 API + Orchestrator + 前端 |
| 3.1 模块四 (审查功能) | Task 10, 17.4 | 审查 API + 审查报告组件 |
| 3.1 模块五 (大纲规划) | Task 11, 18.2 | 规划 API + 规划页面 |
| 3.1 模块六 (查询与设定) | Task 12, 13, 18.3-18.4 | 查询/设定 API + 前端页面 |
| 3.1 模块七 (学习模式) | Task 14, 18.5 | 学习模式 API + 页面 |
| 3.2 非功能性需求 | Task 5, 9, 15 | 错误码/日志/配置 + Orchestrator + SSE |
| 4.1 方案概览 | Task 1-2 | 前后端架构搭建 |
| 4.2.1 组件设计 | Task 3-15 | 所有后端层实现 |
| 4.2.2 接口设计 | Task 6-15 | 所有 API 实现 |
| 4.2.3 数据模型 | Task 3, 5, 6, 7 | 数据存储和 schema |
| 4.2.4 并发模型 | Task 9, 15 | Orchestrator + 任务管理 |
| 4.2.5 错误处理 | Task 5, 9 | 错误码体系 + Orchestrator 错误处理 |
| 4.3.1 状态机 | Task 9 | ChapterOrchestrator |
| 4.3.2 LLM 替代 Agent | Task 4, 9 | LLM Client + PromptBuilder |
| 4.3.3 断点恢复 | Task 9 | 恢复逻辑 |
| 4.3.4 SSE 推送 | Task 15 | SSE 事件推送 |
| 4.3.5 Python 脚本内部化 | Task 9 | sys.path 导入脚本模块 |
| 7. 测试计划 | Task 18.6 | 基础测试覆盖 |
