# ARCHITECTURE.md

> 本文件描述改造完成后的**目标技术架构**。Claude Code 应基于本文件理解最终形态,但具体实施顺序看 `ROADMAP.md`。

---

## 1. 整体调用流程(目标态)

```
用户输入
   │
   ▼
┌────────────────────────────────────┐
│  1. 意图识别(Intent Router)       │
│     ├─ 匹配到 Skill → 走 Skill 流程 │
│     └─ 未匹配 → 走通用对话流程       │
└────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────┐
│  2. 上下文组装(Context Builder)   │
│     - 拉取用户画像                  │
│     - 召回相关长期记忆               │
│     - 拼接最近对话历史               │
│     - (Skill 场景)注入 Skill Prompt│
└────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────┐
│  3. 主 LLM 调用                    │
│     - 强模型(DeepSeek-V3 / Claude)│
│     - 流式返回                      │
└────────────────────────────────────┘
   │
   ▼
┌────────────────────────────────────┐
│  4. 返回答案给前端                  │
│     - 主回答                        │
│     - 触发异步任务(下方 5/6/7)    │
└────────────────────────────────────┘
   │
   ▼ (异步,不阻塞用户)
┌────────────────────────────────────┐
│  5. 事实提取 Agent                 │
│     用轻量模型从对话中提取事实       │
│     → 写入 user_memories            │
├────────────────────────────────────┤
│  6. 画像更新 Agent                 │
│     用轻量模型推断画像字段更新       │
│     → 更新 users.profile            │
├────────────────────────────────────┤
│  7. 推荐生成 Agent                 │
│     用轻量模型生成"猜你想问/想做"   │
│     → 写入 user_suggestions         │
└────────────────────────────────────┘
```

---

## 2. 数据模型

### 2.1 users 表(已存在,需扩展)

```sql
-- 在现有 users 表上新增字段
ALTER TABLE users ADD COLUMN profile JSONB DEFAULT '{}'::jsonb;
ALTER TABLE users ADD COLUMN profile_updated_at TIMESTAMP;
ALTER TABLE users ADD COLUMN onboarded BOOLEAN DEFAULT FALSE;
```

**profile 字段的 JSONB 结构**:

```json
{
  "industry": {"value": "互联网", "confidence": 0.9, "updated_at": "..."},
  "role": {"value": "研发助理", "confidence": 0.8, "updated_at": "..."},
  "company_size": {"value": "50-200", "confidence": 0.6, "updated_at": "..."},
  "ai_proficiency": {"value": "新手", "confidence": 0.7, "updated_at": "..."},
  "pain_points": ["写周报", "整理需求", "跟进bug"],
  "style_preference": {
    "length": "简洁",
    "tone": "口语化",
    "emoji": false
  },
  "context_facts": {
    "boss_name": "张总",
    "team_size": 12,
    "current_project": "..."
  }
}
```

**置信度规则**:
- 首次推断:0.4
- 再次确认:+0.2,封顶 1.0
- 矛盾信息:降到 0.3,标记需澄清
- 显式用户填写(onboarding):直接 1.0

### 2.2 user_memories 表(新增)

```sql
CREATE TABLE user_memories (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  category VARCHAR(50) NOT NULL,
  -- category 枚举:
  -- 'fact'      = 客观事实(用户的老板叫张总)
  -- 'preference'= 偏好(用户喜欢简洁回复)
  -- 'goal'      = 目标(用户下周要做项目复盘)
  -- 'context'   = 背景(用户用 Jira 管理项目)
  importance SMALLINT DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
  source_message_id BIGINT,
  embedding VECTOR(1536),
  created_at TIMESTAMP DEFAULT NOW(),
  last_accessed_at TIMESTAMP,
  access_count INT DEFAULT 0,
  expires_at TIMESTAMP -- NULL 表示永久,goal 类型可设过期
);

CREATE INDEX idx_memories_user ON user_memories(user_id);
CREATE INDEX idx_memories_embedding ON user_memories
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memories_category ON user_memories(user_id, category);
```

### 2.3 industry_skills 表(新增)

```sql
CREATE TABLE industry_skills (
  id BIGSERIAL PRIMARY KEY,
  skill_key VARCHAR(100) UNIQUE NOT NULL,  -- 如 "meeting_notes"
  industry VARCHAR(50) NOT NULL,
  role VARCHAR(50) NOT NULL,
  scenario_name VARCHAR(200) NOT NULL,     -- "需求评审会议纪要"
  description TEXT NOT NULL,                -- 用户能看的描述
  trigger_keywords TEXT[] NOT NULL,         -- ["会议纪要", "评审", "录音"]
  prompt_template TEXT NOT NULL,            -- 主 prompt
  input_schema JSONB NOT NULL,              -- 需要用户提供什么
  example_output TEXT,
  enabled BOOLEAN DEFAULT TRUE,
  display_order INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_skills_industry_role ON industry_skills(industry, role, enabled);
```

**input_schema 示例**:

```json
{
  "fields": [
    {"name": "transcript", "type": "text", "label": "会议录音转文字或要点", "required": true},
    {"name": "attendees", "type": "tags", "label": "参会人员", "required": false},
    {"name": "prd_link", "type": "url", "label": "PRD 链接(可选)", "required": false}
  ]
}
```

### 2.4 user_suggestions 表(新增)

```sql
CREATE TABLE user_suggestions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  message_id BIGINT NOT NULL,
  suggestions JSONB NOT NULL,
  -- suggestions 结构:
  -- [
  --   {"type": "question", "text": "...", "skill_key": null},
  --   {"type": "skill", "text": "用[周报生成]整理本周", "skill_key": "weekly_report"}
  -- ]
  clicked_index SMALLINT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_suggestions_user ON user_suggestions(user_id, created_at DESC);
```

### 2.5 skill_executions 表(新增,Skills 调用记录)

```sql
CREATE TABLE skill_executions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  skill_id BIGINT NOT NULL REFERENCES industry_skills(id),
  message_id BIGINT,
  input_data JSONB,
  output_text TEXT,
  status VARCHAR(20),  -- 'pending'/'success'/'failed'
  duration_ms INT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3. 核心模块设计

### 3.1 模块清单

```
src/
├── core/
│   ├── intent_router.{py,ts}       # 意图识别,路由到 Skill 或通用对话
│   ├── context_builder.{py,ts}     # 上下文组装(画像+记忆+历史)
│   └── llm_client.{py,ts}          # LLM 调用封装(主/辅模型)
│
├── profile/
│   ├── profile_service.{py,ts}     # 画像 CRUD
│   └── profile_updater.{py,ts}     # 异步画像更新 Agent
│
├── memory/
│   ├── memory_service.{py,ts}      # 记忆 CRUD + 召回
│   ├── memory_extractor.{py,ts}    # 异步事实提取 Agent
│   └── embedder.{py,ts}            # 向量化
│
├── skills/
│   ├── skill_registry.{py,ts}      # Skill 注册和查询
│   ├── skill_executor.{py,ts}      # Skill 执行引擎
│   └── definitions/                # Skill 定义文件
│       ├── meeting_notes.{py,ts}
│       ├── weekly_report.{py,ts}
│       ├── bug_tracker.{py,ts}
│       └── ...
│
├── suggestions/
│   └── suggestion_generator.{py,ts} # 异步推荐生成 Agent
│
└── api/
    ├── chat.{py,ts}                # 主对话接口(改造现有)
    ├── onboarding.{py,ts}          # 引导接口(新增)
    ├── profile.{py,ts}             # 画像接口(新增)
    └── skills.{py,ts}              # Skills 接口(新增)
```

**Claude Code 注意**: 上面的目录结构是建议,**实际请遵循项目现有的代码组织风格**,不要为了"整齐"重构现有文件结构。

### 3.2 关键函数签名(伪代码)

```
# 主对话入口(改造现有)
handle_user_message(user_id, user_input) -> {answer, message_id, suggestions?}

# 上下文组装
build_context(user_id, user_input) -> {profile, memories, history, skill?}

# 系统 Prompt 生成
build_system_prompt(profile, memories, skill=None) -> str

# 记忆召回(语义+重要性加权)
retrieve_memories(user_id, query, top_k=5) -> [Memory]

# 异步:事实提取
extract_and_save_memory(user_id, user_input, answer, message_id)

# 异步:画像更新
update_user_profile(user_id, user_input)

# 异步:推荐生成
generate_suggestions(user_id, user_input, answer, message_id)

# Skill 路由
match_skill(user_input, user_profile) -> Skill | None

# Skill 执行
execute_skill(user_id, skill_key, input_data) -> output_text
```

---

## 4. System Prompt 设计

主对话场景下,system prompt 应包含以下结构:

```
你是用户的工作搭子,不是通用 AI 助手。

【关于这位用户】
- 行业:{industry}
- 岗位:{role}
- 主要痛点:{pain_points}
- 偏好风格:{style_preference}

【你记得的事】
{memories_text}

【你的行为准则】
1. 回答要紧扣这个用户的行业和岗位,不说放之四海皆准的废话
2. 主动用"你们行业"、"你这个岗位"这类表述,体现"懂他"
3. 如果引用了上面记得的事,自然提一下,不要生硬
4. 答完一个问题,可以自然带出下一步建议
5. 风格遵循用户偏好(简洁/详细、口语/正式)
```

**Skill 场景下**,system prompt 改为 Skill 自带的 prompt_template,但**仍然要拼接画像和记忆**。

---

## 5. 前端改造点

**Claude Code 注意**: 前端改动按现有技术栈和组件风格来,不要引入新的 UI 框架。

需要新增的页面/组件:

1. **Onboarding 弹窗** — 新用户首次进入触发,3 个问题
2. **个人档案页** — 用户可见/可改自己的画像
3. **Skills 入口** — 首页推荐当前用户角色对应的 Skills
4. **Skill 执行面板** — 接收 Skill 的结构化输入
5. **"猜你想问/想做"组件** — 主对话回答下方展示

---

## 6. 模型与成本

| 用途 | 推荐模型 | 备选 |
|---|---|---|
| 主对话 | DeepSeek-V3 | Claude Sonnet 4.6 |
| 画像更新 | DeepSeek-Lite | Qwen-Turbo |
| 事实提取 | DeepSeek-Lite | Qwen-Turbo |
| 推荐生成 | DeepSeek-Lite | Qwen-Turbo |
| Embedding | bge-large-zh / text-embedding-3 | 阿里 text-embedding-v3 |

**预估单用户月成本**:¥2-5(假设日均 10 轮对话)

---

## 7. 关键设计原则

1. **异步优先** — 画像更新、记忆写入、推荐生成全部异步,不阻塞用户响应
2. **置信度累积** — 画像字段不直接覆盖,通过置信度累积更新
3. **召回加权** — 记忆召回不只看相似度,要 importance × similarity 加权
4. **降级友好** — 任何辅助 Agent 失败都不应影响主对话
5. **可观测性** — 关键流程要埋点,便于调优
6. **Skill 数据驱动** — Skills 通过数据库定义,不通过硬编码,方便加新行业
