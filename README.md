# magic-web-novel

AI 辅助中文网文创作的 Claude Code 技能/插件仓库。通过 prompt engineering + 知识管理系统，引导 LLM 完成从大纲规划到章节起草、质量审查的完整网文创作流程。

## 快速开始

```bash
# 技能通过 Claude Code 斜杠命令调用
/webnovel-write     # 起草章节
/webnovel-review    # 审查章节
/webnovel-plan      # 生成卷纲、时间线、章纲
/webnovel-query     # 查询项目设定
/webnovel-learn     # 提取写作模式
```

## 项目索引地图

### 核心技能

| 技能 | 入口 | 流程 | 评估 |
|------|------|------|------|
| [写章](webnovel-write/SKILL.md) | `SKILL.md` | 预检→合同刷新→context-agent→起草→审查→润色→data-agent→commit→备份 | [evals](webnovel-write/evals/evals.json) |
| [审查](webnovel-review/SKILL.md) | `SKILL.md` | 解析项目根→加载参考→审查 Agent→报告→落库→用户裁决 | [evals](webnovel-review/evals/evals.json) |
| [规划](webnovel-plan/SKILL.md) | `SKILL.md` | 加载总纲→补齐设定→确认卷→节拍表→时间线→卷纲→章纲→写回→验证 | — |
| [查询](webnovel-query/SKILL.md) | `SKILL.md` | 识别类型→加载参考→合同树→数据源检索→格式化输出 | — |
| [学习](webnovel-learn/SKILL.md) | `SKILL.md` | 解析输入→归类 pattern→脚本写入 project_memory.json | — |

### 知识库

| 类别 | 路径 | 内容 |
|------|------|------|
| CSV 知识库 | [references/csv/](references/csv/) | 9 张结构化知识表（命名规则、场景写法、写作技法、桥段套路、人设与关系、爽点与节奏、金手指与设定、题材与调性推理、裁决规则） |
| 共享参考 | [references/shared/](references/shared/) | 核心约束、爽点指导、strand 编织模式、命名与声音差距 |
| 大纲参考 | [references/outlining/](references/outlining/) | 情节信号与剧透区分 |
| 审查参考 | [references/review/](references/review/) | 阻断覆盖指南 |
| 索引元数据 | [references/index/](references/index/) | 引用加载映射、差距登记表 |
| 题材 Profile | [references/genre-profiles.md](references/genre-profiles.md) | 题材 profile（fallback） |
| 审查 Schema | [references/review-schema.md](references/review-schema.md) | 审查输出格式 v6 |
| 追读力分类学 | [references/reading-power-taxonomy.md](references/reading-power-taxonomy.md) | 读者追读动力分类 |

### 题材写作指南

| 流派 | 路径 | 文件数 | 核心内容 |
|------|------|--------|----------|
| 狗血言情 | [genres/dog-blood-romance/](genres/dog-blood-romance/) | 7 | 角色原型、情感张力、情节模板、节奏、爽点、甜虐点 |
| 年代剧 | [genres/period-drama/](genres/period-drama/) | 6 | 古对话、角色设计、历史设定、宫斗、情节模式 |
| 现实题材 | [genres/realistic/](genres/realistic/) | 5 | 角色深度、对话真实性、情节逻辑、现实锚定、社会议题 |
| 规则怪谈 | [genres/rules-mystery/](genres/rules-mystery/) | 7 | 线索设计、核心元素、侦探设计、揭示设计、结构节奏、嫌疑人管理、诡计设计 |
| 玄幻 | [genres/xuanhuan/](genres/xuanhuan/) | 4 | 修炼等级、力量体系、爽点、情节模式 |
| 知乎短篇 | [genres/zhihu-short/](genres/zhihu-short/) | 7 | 角色速建、情感高峰、结尾模式、题材模板、钩子技法、节奏、情节压缩 |

### 模板

| 类别 | 路径 | 内容 |
|------|------|------|
| 题材模板 | [templates/genres/](templates/genres/) | 37 种网文题材初始化模板（修仙、克苏鲁、都市、历史、言情等） |
| 输出模板 | [templates/output/](templates/output/) | 总纲、卷节拍表、卷时间线、世界观、主角卡、女主卡、力量体系、反派设计、金手指、复合题材融合逻辑 |
| 金手指模板 | [templates/golden-finger-templates.md](templates/golden-finger-templates.md) | 金手指（系统/传承/血脉）模板 |

### 外部依赖

| 组件 | 位置 | 说明 |
|------|------|------|
| Python 脚本 | `CLAUDE_PLUGIN_ROOT/scripts/` | `webnovel.py`（主 CLI）、`reference_search.py`（BM25 检索）、`validate_csv.py`（CSV 校验） |
| Subagents | Claude Code agent 定义 | `webnovel-writer:context-agent`、`webnovel-writer:reviewer`、`webnovel-writer:data-agent` 及 evals 配置 |
| Init 快照 | [web-novel-init/](web-novel-init/) | init 技能的 references 完整快照 |

## 数据流

```
Init（项目初始化）
  ↓
Plan（总纲 → 卷纲 → 时间线 → 章纲）
  ↓
Write（上下文 → 起草 → 审查 → 润色 → 事实提取 → 提交 → 备份）
  ↓
Review（独立审查 → 报告 → 指标落库 → 用户裁决）
  ↓
Learn（成功模式提取 → project_memory.json）
```

## 目录结构

```
magic-web-novel/
├── webnovel-write/                # 写章技能
│   ├── SKILL.md                   #   6 步流程定义
│   ├── evals/evals.json           #   3 个评估用例
│   └── references/                #   起草参考（反 AI 指南、润色、风格适配、场景写法等）
├── webnovel-review/               # 审查技能
│   ├── SKILL.md                   #   6 步审查流程
│   ├── evals/evals.json           #   1 个评估用例
│   └── references/                #   常见误区、节奏控制
├── webnovel-plan/                 # 规划技能
│   ├── SKILL.md                   #   9 步规划流程
│   └── references/outlining/      #   章纲规划、冲突设计、卷级节奏等
├── webnovel-query/                # 查询技能
│   ├── SKILL.md                   #   查询流程
│   └── references/                #   数据流、伏笔分析、标签规范
├── webnovel-learn/                # 学习技能
│   └── SKILL.md                   #   模式提取流程
│
├── references/                    # 共享知识库
│   ├── csv/                       #   9 张 CSV 知识表
│   ├── shared/                    #   跨 skill 共享参考
│   ├── outlining/                 #   大纲参考
│   ├── review/                    #   审查参考
│   └── index/                     #   元数据索引
├── templates/                     # 模板
│   ├── genres/                    #   37 种题材模板
│   └── output/                    #   14 种输出 schema 模板
├── genres/                        # 6 个流派的写作指南
├── web-novel-init/                # init 技能的 references 快照
├── CLAUDE.md                      # Claude Code 项目指引
└── puppeteer-config.json          # Puppeteer 浏览器参数
```
