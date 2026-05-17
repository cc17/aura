# IMPLEMENTATION_PLAN.md

> 基于 CURRENT_STATE.md 的现状和 ARCHITECTURE.md 的目标，列出具体改造计划。
> 执行顺序严格按 ROADMAP.md 阶段走。

---

## ⚠️ 改造前必须决策的两个问题

在进入阶段 1 之前，**需要用户确认以下两个决策**，它们影响阶段 1 的所有实现：

### 决策 1：数据库

目标架构需要 PostgreSQL + pgvector（用于向量记忆检索）。
当前用的是 SQLite（无迁移脚本，用 `create_all` 直接建表）。

**三个选项：**

| 选项 | 说明 | 影响 |
|---|---|---|
| A. 迁移到 PostgreSQL | 完整支持 pgvector，向量能力最强 | 需要本地 Postgres 环境（Docker 可解决），阶段 1 需要迁移现有数据 |
| B. 保留 SQLite + sqlite-vec | 引入 sqlite-vec 扩展支持向量搜索，无需额外服务 | 部署简单，但 sqlite-vec 是实验性项目，生产稳定性较低 |
| C. 暂不上向量，文本检索 | user_memories 用关键词/BM25 检索，阶段 4 再决定是否加向量 | 记忆召回质量略差，但实现最快，风险最低 |

**建议**：选 A（PostgreSQL）或 C（先跑通业务再加向量），不建议 B。

---

### 决策 2：用户身份

目标架构所有表（users、user_memories、user_suggestions 等）都有 user_id。
当前系统无认证，所有对话匿名。

**三个选项：**

| 选项 | 说明 | 工作量 |
|---|---|---|
| A. 单用户模式 | 不加登录，系统默认只有 user_id=1，适合内部 MVP | 最小，阶段 1 直接创建 1 条用户记录 |
| B. 匿名持久化（cookie/localStorage） | 浏览器首次访问自动分配 user_id，存 localStorage，后端识别 | 小，不需要密码，支持"多用户"测试 |
| C. 简单登录（用户名+密码） | 加基础 auth 模块，支持真实多用户 | 中，约 1 天工作量，但测试场景最真实 |

**建议**：选 B（匿名持久化）—— 无摩擦、支持多小白鼠、改造量最小。

---

## 改造计划（按阶段）

以下计划**假设选择：数据库=C（暂文本检索）、用户身份=B（匿名持久化）**。
若决策不同，阶段 1 和阶段 4 的实现方式会相应调整。

---

## 阶段 1：数据层基建

### 新增 ORM 模型（在 `backend/memory/models.py` 追加）

```
UserModel          — 对应 users 表（无需实际 auth 字段，只需 id + profile + onboarded）
UserMemoryModel    — 对应 user_memories 表（暂无向量字段，按决策 1 决定是否加）
IndustrySkillModel — 对应 industry_skills 表
UserSuggestionModel — 对应 user_suggestions 表
SkillExecutionModel — 对应 skill_executions 表
```

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/memory/models.py` | 追加 5 个新 ORM 模型类 |
| `backend/memory/database.py` | 无需改动（`create_all` 会自动建新表） |
| `backend/config.py` | 追加 `lite_model`（辅助LLM）、`embedding_model` 配置项 |

### 新增文件

无（纯数据层，不新增业务文件）

### 风险点

- SQLite 不支持 `ALTER TABLE ADD COLUMN NOT NULL`（无 DEFAULT 的情况）。新增模型用 `nullable=True` 或带 `default`。
- pgvector 的 `VECTOR` 类型在 SQLite 上不可用，向量字段留到决策 1 确定后再加。

---

## 阶段 2：用户画像 + Onboarding

### 后端新增文件

| 文件 | 职责 |
|---|---|
| `backend/services/profile_service.py` | 画像 CRUD（get/upsert profile、mark onboarded） |
| `backend/api/onboarding.py` | POST /api/onboarding：接收3问答案，写 users.profile |
| `backend/api/profile.py` | GET/PATCH /api/profile：读取和手动修改画像 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/api/router.py` | 注册 onboarding + profile 路由 |
| `backend/memory/manager.py` | `build_context()` 新增步骤：拉 profile → 生成 system prompt 段 |
| `backend/api/chat.py` | 请求时传入 user_id（从 cookie/header 读取） |

### 前端新增文件

| 文件 | 职责 |
|---|---|
| `frontend/src/components/OnboardingModal.tsx` | 3步问卷弹窗（首次进入时显示） |
| `frontend/src/hooks/useUser.ts` | 管理 user_id（localStorage 持久化） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `frontend/src/App.tsx` | 检查 `users.onboarded`，未完成则显示 OnboardingModal |
| `frontend/src/services/api.ts` | 所有请求带 user_id header；增加 onboarding/profile API 调用 |

---

## 阶段 3：Skills 框架 + 首批 2 个 Skills

### 后端新增文件

| 文件 | 职责 |
|---|---|
| `backend/services/skill_registry.py` | 从 `industry_skills` 表加载 Skills，缓存，支持按 industry/role 过滤 |
| `backend/services/skill_executor.py` | 接收 skill_key + input_data，渲染 prompt_template，调用 LLM，写 skill_executions |

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/agent/intent.py` | 扩展：优先匹配 Skill trigger_keywords；返回 `SkillMatch | IntentResult` |
| `backend/graph/supervisor.py` | Skill 命中时走 Skill 执行路径，不进入 LangGraph worker |
| `backend/api/router.py` | 注册 skills 路由 |

### 新增 API 文件

| 文件 | 路由 |
|---|---|
| `backend/api/skills.py` | GET /api/skills（列出当前用户可用Skills）；POST /api/skills/{key}/execute |

### 数据初始化

- 在 `backend/services/skill_registry.py` 中加 `seed_default_skills()` 函数
- 服务启动时（`main.py startup`）写入 meeting_notes、weekly_report 两条 Skill 记录

### 前端新增文件

| 文件 | 职责 |
|---|---|
| `frontend/src/components/SkillCards.tsx` | 输入框上方展示 Skill 快捷入口卡片 |
| `frontend/src/components/SkillPanel.tsx` | Skill 结构化输入面板（表单渲染） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `frontend/src/App.tsx` | 集成 SkillCards + SkillPanel |
| `frontend/src/hooks/useChat.ts` | 支持 Skill 执行结果在对话流中呈现 |

---

## 阶段 4：记忆系统

> ⚠️ 本阶段实现方式取决于决策 1（数据库）。以下以**文本检索（决策 C）**为基准描述，PostgreSQL + pgvector 版本需调整 UserMemoryModel 加向量字段。

### 后端新增文件

| 文件 | 职责 |
|---|---|
| `backend/services/memory_extractor.py` | 异步：用辅助模型提取 fact/preference/goal/context，写 user_memories |
| `backend/services/memory_service.py` | `retrieve_memories(user_id, query, top_k=5)`，文本检索版用关键词匹配 |
| `backend/services/embedder.py` | 向量化封装（决策 1=A/B 时启用；决策 C 时桩实现） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/memory/manager.py` | `build_context()` 加步骤：召回 user_memories → 拼入 system prompt |
| `backend/api/chat.py` | 后台任务加 `memory_extractor.extract_and_save_memory()` |

### 与现有 user_facts 的关系

- `user_facts`（现有）：全局纯文本，无 user_id，全量替换
- `user_memories`（新增）：per-user，有 category/importance，增量写入
- 两者并存，阶段 4 后 `user_facts` 逐渐被 `user_memories` 取代（但不立刻删除 user_facts，保持兼容）

---

## 阶段 5：画像更新 Agent + 推荐生成

### 后端新增文件

| 文件 | 职责 |
|---|---|
| `backend/services/profile_updater.py` | 异步：用辅助模型推断画像字段更新（置信度累积） |
| `backend/services/suggestion_generator.py` | 异步：生成3条"猜你想问/想做"推荐，写 user_suggestions |

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/api/chat.py` | 后台任务加 profile_updater + suggestion_generator |
| `backend/api/router.py` | 注册 suggestions 读取接口 |

### 前端新增文件

| 文件 | 职责 |
|---|---|
| `frontend/src/components/SuggestionsBar.tsx` | 对话回答下方展示"💡 你可能还想..."区块 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `frontend/src/hooks/useChat.ts` | 每次收到 DONE 事件后拉取最新 suggestions |

---

## 阶段 6：个人档案页 + 数据看板

### 前端新增文件

| 文件 | 职责 |
|---|---|
| `frontend/src/components/ProfilePage.tsx` | 展示/编辑用户画像，展示部分记忆，支持删除记忆条目 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `frontend/src/App.tsx` | 加导航入口（Sidebar 里加"我的档案"） |

### 后端

- `backend/api/stats.py` 扩展：加 Skill 使用次数、推荐点击率等指标
- `backend/api/profile.py` 支持 PATCH（更新画像字段，置信度直接设 1.0）

---

## 阶段 7：小白鼠准备

- 补充 3-5 个 Skills（bug_tracker、requirement_classifier 等），写入数据库
- 完善埋点（skill_execution、suggestion_click）
- 写用户使用引导文档

---

## 文件改动总览

### 新增文件（后端）

```
backend/services/
├── profile_service.py      # 阶段 2
├── skill_registry.py       # 阶段 3
├── skill_executor.py       # 阶段 3
├── memory_extractor.py     # 阶段 4
├── memory_service.py       # 阶段 4
├── embedder.py             # 阶段 4（可先为桩）
├── profile_updater.py      # 阶段 5
└── suggestion_generator.py # 阶段 5

backend/api/
├── onboarding.py           # 阶段 2
├── profile.py              # 阶段 2
└── skills.py               # 阶段 3
```

### 新增文件（前端）

```
frontend/src/components/
├── OnboardingModal.tsx     # 阶段 2
├── SkillCards.tsx          # 阶段 3
├── SkillPanel.tsx          # 阶段 3
├── SuggestionsBar.tsx      # 阶段 5
└── ProfilePage.tsx         # 阶段 6

frontend/src/hooks/
└── useUser.ts              # 阶段 2
```

### 修改文件

```
backend/memory/models.py        # 阶段 1：追加新 ORM 模型
backend/memory/manager.py       # 阶段 2+4：build_context 注入画像/记忆
backend/api/chat.py             # 阶段 2+4+5：加 user_id 识别 + 后台任务扩展
backend/api/router.py           # 阶段 2+3+5：注册新路由
backend/agent/intent.py         # 阶段 3：加 Skill 匹配
backend/graph/supervisor.py     # 阶段 3：加 Skill 执行路径
backend/config.py               # 阶段 1：加辅助模型配置
backend/main.py                 # 阶段 3：startup 加 skill seed
frontend/src/App.tsx            # 阶段 2+3+5+6：集成新组件
frontend/src/services/api.ts    # 阶段 2+：加新 API 调用
frontend/src/hooks/useChat.ts   # 阶段 3+5：Skill 执行 + suggestions 拉取
```

---

## 风险点汇总

| 风险 | 影响阶段 | 说明 |
|---|---|---|
| SQLite vs pgvector | 1、4 | 核心基础设施决策，需用户在进阶段1前确认 |
| 无用户认证 | 1、2 | 影响所有表的 user_id 设计，需确认 |
| 辅助模型配置 | 4、5 | 目前只有豆包主模型，需配置 DeepSeek-Lite 或 Qwen-Turbo |
| 现有 user_facts 与 user_memories 共存 | 4 | 过渡期需两个系统同时运行，build_context 里要合并注入 |
| Skill 路由与现有 agent 路由并存 | 3 | Skill 命中时绕过 LangGraph worker，逻辑需仔细分支 |
| embedding 维度 | 4 | bge-large-zh 是 1024 维，text-embedding-3 是 1536 维，建表前需定好 |
| 前端无路由系统 | 6 | 档案页需要页面导航，现有 App.tsx 是单页，需决定加 react-router 还是用 state 切换 |
