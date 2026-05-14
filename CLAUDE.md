# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## 项目概述

这是一个 **Claude Code 技能/插件仓库**，用于 AI 辅助中文网文创作。它不是传统软件项目 —— 而是一套 prompt engineering + 知识管理系统，通过 Claude Code agent 框架运作。

## 核心技能（Skills）

| 技能 | 入口文件 | 用途 | 步骤数 |
|------|----------|------|--------|
| `/webnovel-write` | `webnovel-write/SKILL.md` | 起草章节：上下文→起草→审查→润色→提交→备份 | 6 |
| `/webnovel-review` | `webnovel-review/SKILL.md` | 章节质量审查，生成结构化报告 | 6 |
| `/webnovel-plan` | `webnovel-plan/SKILL.md` | 基于总纲生成卷纲、时间线和章纲 | 9 |
| `/webnovel-query` | `webnovel-query/SKILL.md` | 查询项目设定、角色、伏笔等信息 | — |
| `/webnovel-learn` | `webnovel-learn/SKILL.md` | 从成功章节提取写作模式并持久化 | — |

### 评估文件

- `webnovel-write/evals/evals.json` — 3 个写章评估用例
- `webnovel-review/evals/evals.json` — 1 个审查评估用例

### Subagents

- `webnovel-writer:context-agent` — 写前 research，输出写作任务书
- `webnovel-writer:data-agent` — 从正文提取事实，生成 commit artifacts
- `webnovel-writer:reviewer` — 统一审查 agent，输出结构化问题清单

## 数据流

```
Init (外部) → Plan → Write → Review → Backup
                                     ↓
                                   Learn
```

## 关键路径

### Python 脚本（在 `CLAUDE_PLUGIN_ROOT/scripts/` 下，不在此仓库）

- `webnovel.py` — 主 CLI 入口（preflight、story-system、review-pipeline、chapter-commit、backup、knowledge 查询、memory-contract 等）
- `reference_search.py` — BM25 检索 CSV 知识库
- `validate_csv.py` — CSV schema 校验

所有 Python 脚本使用 `python -X utf8` 执行以确保中文 UTF-8 正确处理。

### 核心命令

```bash
# 预检项目
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" preflight

# 解析真实项目根
export PROJECT_ROOT="$(python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" where)"

# 刷新 Story System 合同
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${WORKSPACE_ROOT}" \
  story-system "${CHAPTER_GOAL}" --genre "${GENRE}" --chapter {N} \
  --persist --emit-runtime-contracts --format both

# 审查管线
python -X utf8 "${SCRIPTS_DIR}/webnovel.py" --project-root "${PROJECT_ROOT}" review-pipeline \
  --chapter {N} --review-results review_results.json \
  --metrics-out review_metrics.json --report-file 审查报告.md

# CSV 检索
python -X utf8 "${SCRIPTS_DIR}/reference_search.py" \
  --skill write --table {表名} --query "{关键词}" --genre {题材}

# CSV 校验
python -X utf8 "${SCRIPTS_DIR}/validate_csv.py"
```

### 环境变量

- `CLAUDE_PROJECT_DIR` — 当前 Claude Code 工作目录
- `CLAUDE_PLUGIN_ROOT` — 插件根目录（技能文件所在路径，通常不在此仓库内）
- `PROJECT_ROOT` — 通过 `webnovel.py where` 解析的真实书项目根（必须含 `.webnovel/state.json`）

## 项目结构（完整）

```
magic-web-novel/
│
├── webnovel-write/                    # 写章技能
│   ├── SKILL.md                       #   6 步流程定义
│   ├── evals/evals.json               #   3 个评估用例
│   └── references/
│       ├── anti-ai-guide.md           #   Anti-AI 写作指南（8 种 LLM 倾向对抗）
│       ├── polish-guide.md            #   润色指导
│       ├── style-adapter.md           #   风格适配
│       ├── style-variants.md          #   风格变体
│       └── writing/
│           ├── combat-scenes.md       #   战斗场景写法
│           ├── desire-description.md  #   欲望描写
│           ├── dialogue-writing.md    #   对话写作
│           ├── emotion-psychology.md  #   情感心理学
│           ├── genre-hook-payoff-library.md  # 题材钩子与兑现库
│           ├── scene-description.md   #   场景描写
│           └── typesetting.md         #   排版规范
│
├── webnovel-review/                   # 审查技能
│   ├── SKILL.md                       #   6 步审查流程
│   ├── evals/evals.json               #   1 个评估用例
│   └── references/
│       ├── common-mistakes.md         #   常见误区
│       └── pacing-control.md          #   节奏控制
│
├── webnovel-plan/                     # 规划技能
│   ├── SKILL.md                       #   9 步规划流程
│   └── references/outlining/
│       ├── chapter-planning.md        #   章纲规划
│       ├── conflict-design.md         #   冲突设计
│       ├── genre-volume-pacing.md     #   题材卷级节奏
│       ├── outline-structure.md       #   大纲结构
│       └── plot-frameworks.md         #   情节框架
│
├── webnovel-query/                    # 查询技能
│   ├── SKILL.md                       #   查询流程
│   └── references/
│       ├── advanced/
│       │   └── foreshadowing.md       #   伏笔分析
│       ├── system-data-flow.md        #   系统数据流
│       └── tag-specification.md       #   标签规范
│
├── webnovel-learn/                    # 学习技能
│   └── SKILL.md                       #   模式提取流程
│
├── references/                        # 共享知识库
│   ├── README.md                      #   参考目录说明
│   ├── genre-profiles.md              #   题材 profile（fallback）
│   ├── reading-power-taxonomy.md      #   追读力分类学
│   ├── review-schema.md               #   审查输出格式 v6
│   ├── csv/                           #   9 张 CSV 知识表
│   │   ├── README.md                  #     CSV 数据规范
│   │   ├── genre-canonical.md         #     题材权威枚举
│   │   ├── 命名规则.csv               #     NR- 角色/地点/势力命名
│   │   ├── 场景写法.csv               #     SP- 战斗/对话/桥段场景
│   │   ├── 写作技法.csv               #     WT- 对话/情感/场景/节奏技法
│   │   ├── 桥段套路.csv               #     TR- 套路/前置/爽点/转折
│   │   ├── 人设与关系.csv             #     CH- 人设模板/动机/互动
│   │   ├── 爽点与节奏.csv             #     PA- 压抑/爆发/兑现节奏
│   │   ├── 金手指与设定.csv           #     SY- 系统/传承/血脉设定
│   │   ├── 题材与调性推理.csv         #     GR- 题材路由与调性
│   │   └── 裁决规则.csv               #     RS- 题材级裁决规则
│   ├── shared/                        #   跨 skill 共享
│   │   ├── core-constraints.md        #     三大定律 + 防幻觉协议
│   │   ├── cool-points-guide.md       #     爽点指导
│   │   ├── naming-and-voice-gaps.md   #     命名与声音差距
│   │   └── strand-weave-pattern.md    #     多线编织模式
│   ├── outlining/
│   │   └── plot-signal-vs-spoiler.md  #   情节信号与剧透区分
│   ├── review/
│   │   └── blocking-override-guidelines.md  # 阻断覆盖指南
│   └── index/
│       ├── reference-loading-map.md   #   引用加载映射
│       └── reference-gap-register.md  #   差距登记表
│
├── templates/                         # 模板
│   ├── genres/                        #   37 种题材初始化模板
│   │   ├── 修仙.md / 克苏鲁.md / 西幻.md / 黑暗题材.md
│   │   ├── 都市日常.md / 都市异能.md / 都市脑洞.md
│   │   ├── 历史古代.md / 历史脑洞.md / 抗战谍战.md
│   │   ├── 古言.md / 现言脑洞.md / 幻想言情.md / 狗血言情.md
│   │   ├── 豪门总裁.md / 青春甜宠.md / 民国言情.md / 职场婚恋.md
│   │   ├── 年代.md / 种田.md
│   │   ├── 科幻.md / 末世.md / 游戏体育.md / 电竞.md
│   │   ├── 悬疑灵异.md / 悬疑脑洞.md / 女频悬疑.md
│   │   ├── 规则怪谈.md / 无限流.md / 系统流.md / 直播文.md
│   │   ├── 多子多福.md / 替身文.md / 宫斗宅斗.md / 知乎短篇.md
│   │   └── 高武.md / 现实题材.md
│   └── output/                        #   输出 schema 模板
│       ├── 大纲-总纲.md
│       ├── 大纲-卷节拍表.md
│       ├── 大纲-卷时间线.md
│       ├── 设定集-世界观.md
│       ├── 设定集-力量体系.md
│       ├── 设定集-主角卡.md / 设定集-女主卡.md / 设定集-主角组.md
│       ├── 设定集-反派设计.md
│       ├── 设定集-金手指.md
│       ├── 复合题材-融合逻辑.md
│       ├── index-schema.md
│       └── state-schema.md
│   └── golden-finger-templates.md     #   金手指模板（独立文件）
│
├── genres/                            # 6 个流派的写作指南
│   ├── dog-blood-romance/             #   狗血言情（7 文件）
│   ├── period-drama/                  #   年代剧（6 文件）
│   ├── realistic/                     #   现实题材（5 文件）
│   ├── rules-mystery/                 #   规则怪谈（7 文件）
│   ├── xuanhuan/                      #   玄幻（4 文件）
│   └── zhihu-short/                   #   知乎短篇（7 文件）
│
├── web-novel-init/                    # init 技能的 references 快照
│   └── references/                    #   （与顶层 references/ 结构一致）
│
├── CLAUDE.md                          # Claude Code 项目指引（本文件）
├── README.md                          # 项目说明与索引地图
└── puppeteer-config.json              # Puppeteer 浏览器参数（--no-sandbox）
```

## 核心概念

### 数据源优先级

1. **写前真源**：`.story-system/` 合同树（MASTER_SETTING、volumes、chapters）
2. **写后真源**：`.story-system/commits/chapter_XXX.commit.json`（已发布定稿）
3. **投影层**：`.webnovel/state.json` / `index.db`（read-model/fallback，非事实真源）

### 优先级链

用户要求 > blocking 硬门槛 > 项目私有约束 > skill 流程 > reference 建议

### 三大定律（写章核心约束）

1. **大纲是法** — 章纲是最高指令，不得偏离
2. **设定是物理** — 世界观和力量体系是硬性物理法则
3. **发明需要认同** — 不得凭空发明新设定，必须有来源

### 审查 Schema (v6)

- reviewer 输出 JSON 是审查唯一事实源
- 无总分（不输出 overall_score）
- `blocking=true` 问题必须解决才能进入下一步
- `severity=critical` 自动 `blocking=true`
- 每个 issue 必须有 `evidence` 字段

### 结构化节点

- **CBN**（Chapter Begin Node）：章节起点
- **CPNs**（Chapter Progress Nodes）：推进节点（2-4 个）
- **CEN**（Chapter End Node）：章节终点
- 格式：`主体 | 动作/变化 | 对象/结果`
- 相邻章节 CEN → 下一章 CBN 必须逻辑承接
- 每章必须覆盖节点最多 4 个（CBN + CEN + 1~2 核心 CPN）

## CSV 知识库

9 张表，编号前缀：`NR-`（命名）、`SP-`（场景）、`WT-`（技法）、`TR-`（桥段）、`CH-`（人设）、`PA-`（节奏）、`SY-`（设定）、`GR-`（题材）、`RS-`（裁决）

15 个 canonical 题材：都市、玄幻、仙侠、奇幻、科幻、历史、悬疑、游戏、古言、现言、幻言、年代、种田、快穿、衍生

CSV 使用 UTF-8 with BOM 编码，多值字段以 `|` 分隔。内容迁移只允许人工手动修改，禁止自动脚本。

## 写章 Anti-AI 规则

起草时必须对抗的 8 种 LLM 倾向：
1. 每段写完整闭环 → 刻意删掉感悟，留余味
2. 副词修饰一切 → 用具体动作替代
3. 所有角色同一套反应 → 设计专属微动作
4. 对话像辩论赛 → 带潜台词、言行不一、有省略和打断
5. 情绪贴标签 → 生理反应 + 微动作
6. 信息均匀分布 → 刻意制造疏密对比
7. 安全着陆 → 每章留未解决的钩子
8. 第一第二第三 → 避免枚举式结构

## SKILL.md 修改规范

每个技能的 `SKILL.md` 文件包含 YAML front matter（name、description、allowed-tools）和执行流程。修改时注意：

- 不要破坏 YAML front matter 格式
- 不要改变步骤编号或流程顺序，除非明确意图
- CSV 内容迁移只允许人工手动修改，禁止自动脚本
- 文件命名：kebab-case，全小写
- 所有 reference 文件必须有 YAML front matter（name + purpose）
