# ROADMAP.md

> **Claude Code 的执行依据**。本文件按阶段拆解改造任务,每个阶段独立可交付,可独立验收。
>
> **执行原则**:
> 1. 严格按阶段顺序推进,**不要跳阶段**
> 2. 每个阶段完成后**停下来**,等用户 review 通过再进下一阶段
> 3. 每个阶段结束在末尾追加 `## 完成记录` 章节
> 4. 遇到与现有代码冲突,**先报告再决策**,不要擅自重构

---

## 阶段 0:勘查与对齐(必做,先于一切)

**目标**:理解现有项目,产出共识文档。

### 任务

1. 扫描整个项目代码库
2. 生成 `docs/CURRENT_STATE.md`,包含:
   - 技术栈(语言、框架、数据库、ORM)
   - 目录结构和每个核心目录的职责
   - 现有的核心数据库表结构(尤其是 users 表的现有字段)
   - 主要代码模块的调用关系
   - 现有 LLM 调用流程是怎么走的(从前端到后端到模型)
   - 现有的对话历史是怎么存的
   - 当前项目使用的命名规范、代码风格
3. 输出 `docs/IMPLEMENTATION_PLAN.md`,基于 `ARCHITECTURE.md` 列出:
   - 需要新增的文件清单
   - 需要修改的现有文件清单
   - 每个改动的目的
   - 可能的风险点和兼容性问题

### 验收标准

- [ ] `CURRENT_STATE.md` 准确无误,用户 review 通过
- [ ] `IMPLEMENTATION_PLAN.md` 计划清晰,用户 review 通过
- [ ] **不写任何代码**

### ⚠️ 阶段 0 完成前不要进入阶段 1

---

## 阶段 1:数据层基建(Day 1-2)

**目标**:扩展数据库,为后续功能打地基。

### 任务

1. 编写数据库迁移脚本,遵循项目现有的迁移工具(Alembic / Knex / Prisma 等):
   - 扩展 `users` 表:`profile JSONB`, `profile_updated_at TIMESTAMP`, `onboarded BOOLEAN`
   - 新建 `user_memories` 表(含 pgvector 扩展)
   - 新建 `industry_skills` 表
   - 新建 `user_suggestions` 表
   - 新建 `skill_executions` 表
2. 检查 PostgreSQL 是否已启用 pgvector 扩展,未启用则:
   - 在迁移脚本中加 `CREATE EXTENSION IF NOT EXISTS vector;`
   - 在 `docs/SETUP.md` 中记录该依赖
3. 编写对应的 ORM 模型/数据访问层代码,**风格严格遵循现有项目**
4. 不写业务逻辑,只写数据层

### 验收标准

- [ ] 迁移脚本能在本地数据库正确执行
- [ ] 能正向迁移和回滚
- [ ] ORM 模型与项目现有风格一致
- [ ] **暂不动业务代码**

---

## 阶段 2:用户画像系统 + Onboarding(Day 3)

**目标**:让用户进来时能被打上画像,主对话能感知画像。

### 任务

1. **后端**:
   - 实现 `profile_service`:画像 CRUD
   - 实现 `onboarding` API:接收 3 问的答案,写入 users.profile
   - 在主对话流程中:**调用 LLM 前,拉取 profile,注入到 system prompt**
   - 实现 `build_system_prompt(profile, memories=None, skill=None)` 函数,本阶段先只支持 profile
2. **前端**:
   - 新用户首次登录(`users.onboarded=false`)弹出 Onboarding 引导
   - 3 个问题(单选/多选,UI 风格沿用项目现有组件):
     - "你是做什么工作的?" → 行业 + 角色(可先做研发助理一档,加"其他"占位)
     - "你最希望我帮你解决?" → 多选痛点
     - "你用 AI 多久了?" → 单选熟练度
   - 提交后写入 profile,标记 onboarded=true
3. **降级处理**:已有用户没填画像,system prompt 跳过画像段,正常对话

### 验收标准

- [ ] 新用户能完整走完 Onboarding 流程
- [ ] 已有用户登录不报错
- [ ] 主对话调用前能看到 profile 已注入 prompt(可加日志验证)
- [ ] **对话效果开始有"行业感"** —— 这是关键体感测试

### 关键体感测试

完成本阶段后,用研发助理身份问"帮我写个周报",对比改造前后回答的差异。**如果差异不明显,说明 prompt 没注入成功或 prompt 写得太弱,要排查。**

---

## 阶段 3:Skills 框架 + 首批 2 个 Skills(Day 4-5)

**目标**:让产品从"会聊天"升级到"会干活"。

### 任务

1. **Skill 数据模型**:
   - 实现 `skill_registry`:从 `industry_skills` 表加载 Skills
   - 设计 Skill 定义格式(数据库存储 + 代码层包装类)
2. **意图识别(简版)**:
   - 实现 `intent_router`
   - 简单实现:基于关键词匹配 + LLM 兜底判断
   - 路由结果:Skill | 通用对话
3. **Skill 执行引擎**:
   - 实现 `skill_executor`:接收 skill_key + input_data,执行 prompt_template,返回结果
   - 记录到 `skill_executions` 表
4. **填充首批 2 个 Skills**(研发助理场景):
   
   **Skill A:meeting_notes(需求评审会议纪要)**
   - 输入:transcript(必填)、attendees(可选)、prd_link(可选)
   - 输出格式:决议项 ✓ / 待跟进 ⏳ / 风险 ⚠️ 三段式
   - prompt_template 见附录 A
   
   **Skill B:weekly_report(研发周报生成)**
   - 输入:本周完成(必填)、下周计划(必填)、风险(可选)
   - 输出格式:数据先行 + 进展 + 计划 + 风险
   - prompt_template 见附录 B

5. **前端**:
   - 在主对话输入框上方,展示当前用户角色对应的 Skills 入口卡片
   - 点击 Skill 卡片,弹出 input_schema 对应的表单
   - 提交表单后,在主对话流里以 Skill 执行结果的形式呈现

### 验收标准

- [ ] 2 个 Skills 能完整跑通(从前端点击到后端执行到结果呈现)
- [ ] 用户在主对话里输入"帮我写个会议纪要"能被路由到 Skill 入口
- [ ] Skill 执行结果质量明显优于通用对话

---

## 阶段 4:记忆系统(Day 6-7)

**目标**:让 Bot 记住用户提过的事,实现"用得越久越懂你"。

### 任务

1. **Embedding 服务**:
   - 实现 `embedder`:封装 embedding 模型调用
   - 选型:bge-large-zh-v1.5(本地)或阿里 text-embedding-v3(API)
2. **记忆写入(异步)**:
   - 实现 `memory_extractor`:
     - 触发时机:主对话返回答案后,异步触发
     - 用轻量模型(DeepSeek-Lite)提取 fact / preference / goal / context
     - 向量化后写入 `user_memories`
   - Prompt 模板见附录 C
3. **记忆召回**:
   - 实现 `memory_service.retrieve_memories(user_id, query, top_k=5)`
   - 召回逻辑:`score = importance × 0.3 + similarity × 0.7`
   - 更新 `last_accessed_at` 和 `access_count`
4. **集成到主对话**:
   - 在 `build_context` 中召回记忆
   - 在 `build_system_prompt` 中拼接记忆段

### 验收标准

- [ ] 用户提"我老板叫张总",后续对话 Bot 能自然引用
- [ ] 记忆写入是异步的,不影响主对话响应速度
- [ ] 记忆召回质量可接受(可主观评估,无需严格指标)
- [ ] 任一异步 Agent 挂掉,主对话仍正常工作(降级测试)

---

## 阶段 5:画像更新 Agent + 推荐生成(Day 8-9)

**目标**:让画像自动演化,让推荐"懂你"。

### 任务

1. **画像更新 Agent(异步)**:
   - 实现 `profile_updater`
   - 触发时机:主对话返回答案后,异步触发
   - 用轻量模型推断画像字段更新,**遵循置信度累积规则**
   - Prompt 模板见附录 D
2. **推荐生成 Agent(异步)**:
   - 实现 `suggestion_generator`
   - 触发时机:主对话返回答案后,异步触发
   - 生成 3 条推荐,包含混合类型:
     - 至少 1 条是"问题"(下一步可能问什么)
     - 至少 1 条是"Skill"(下一步可能想做什么操作)
   - 写入 `user_suggestions` 表
   - Prompt 模板见附录 E
3. **前端**:
   - 主对话回答下方展示"💡 你可能还想..." 区块
   - 区分类型:问题点击直接发送;Skill 点击打开对应 Skill 的输入面板

### 验收标准

- [ ] 画像随对话自然演化(可在档案页观察)
- [ ] 推荐内容明显比通用聊天 Bot 的"还有什么想问"更具体
- [ ] 推荐里有 Skill 类型的项,点击能跳转到 Skill 面板

---

## 阶段 6:个人档案页 + 数据看板(Day 10)

**目标**:闭环用户信任感 + 自己能看到产品数据。

### 任务

1. **个人档案页(用户可见)**:
   - 展示当前 profile
   - 用户可手动修改(修改后置信度直接变 1.0)
   - 展示部分长期记忆(用户可删除)
   - 这是建立"AI 懂我"信任感的关键页面
2. **内部数据看板(给你自己看)**:
   - 用户数、活跃用户数
   - 每个 Skill 的使用次数
   - 推荐的点击率
   - 平均对话轮次
   - 异步 Agent 的成功率
   - 简单实现即可,可以是一个简单的管理页或定期日志

### 验收标准

- [ ] 用户能看到/改自己的画像
- [ ] 有基础数据看板,你能持续追踪小白鼠的使用情况

---

## 阶段 7:小白鼠测试准备(Day 11+)

**目标**:把产品交付到 5-10 个研发助理手里。

### 任务

1. **添加更多 Skills**(根据分享会反馈,从研发助理高频痛点里挑 3-5 个补全):
   - bug_tracker(bug 状态汇总)
   - meeting_coordinator(协调跨部门会议)
   - requirement_classifier(需求池分类)
   - okr_review(月度 OKR 复盘)
   - 等等
2. **埋点完善**:确保关键行为都有记录
3. **使用引导文档**:写一份简单的"如何用好这个工具"给小白鼠
4. **反馈渠道**:建一个反馈入口(简单的 form 或群)

### 验收标准

- [ ] 5+ Skills 可用
- [ ] 关键路径埋点完整
- [ ] 用户能找到反馈方式

---

## 附录:Skill Prompt 模板

### 附录 A:meeting_notes prompt_template

```
你是研发助理的工作搭子,正在帮 TA 把一场需求评审会议整理成结构化纪要。

【会议内容】
{transcript}

{#if attendees}
【参会人员】
{attendees}
{/if}

{#if prd_link}
【相关 PRD】
{prd_link}
{/if}

请按以下格式输出会议纪要:

## 📌 决议项
列出本次评审通过的需求/方案。每条标注:
- 需求名称
- 责任人(从参会人员中推断)
- 预期交付时间(如会议中提及)

## ⏳ 待跟进
列出需要会后跟进的问题。每条标注:
- 待跟进事项
- 跟进负责人
- 截止时间

## ⚠️ 风险
列出会议中提到的风险/异议/争议点。

【输出要求】
- 简洁,不堆砌废话
- 不确定的信息标注"(待确认)",不要瞎编
- 用 markdown 格式
```

### 附录 B:weekly_report prompt_template

```
你是研发助理的工作搭子,正在帮 TA 起草本周研发周报。

【本周完成】
{this_week_done}

【下周计划】
{next_week_plan}

{#if risks}
【风险/问题】
{risks}
{/if}

【用户画像参考】
{profile_snippet}

【用户记忆中相关的事】
{memories_snippet}

请生成一份结构清晰的周报,遵循以下原则:
1. **数据先行**:如果有具体数字(完成多少需求、修复多少 bug),放在最前面
2. **进展具体**:用动词+对象+结果的句式,避免"推进了"、"沟通了"这种虚词
3. **计划可衡量**:下周计划写明可交付物,不要"继续推进"
4. **风险明确**:风险要写清楚影响和应对建议

【输出格式】
## 一句话总结
(2-3 句概括本周工作)

## 本周完成
- ...

## 下周计划
- ...

## 风险与建议
- ...
```

### 附录 C:memory_extractor prompt

```
从下面的对话中,提取出值得长期记住的事实。

【用户】{user_input}
【助手】{answer}

【提取规则】
1. 只提取关于用户本人的具体事实,不提取一般性知识
2. 每条事实独立成句,简洁
3. 标注类别:
   - fact: 客观事实(用户的老板叫张总)
   - preference: 偏好(用户喜欢简洁回答)
   - goal: 短期目标(用户下周要做项目复盘)
   - context: 工作背景(用户的团队用 Jira)
4. 标注重要性 1-10:
   - 9-10: 长期身份信息(行业/岗位)
   - 7-8: 重要关系/项目
   - 4-6: 偏好/习惯
   - 1-3: 临时信息
5. 没有值得记的就返回空数组

【输出格式】严格的 JSON 数组,不要任何其他文字:
[{"content": "...", "category": "...", "importance": N}]
```

### 附录 D:profile_updater prompt

```
基于用户的提问,推断或更新用户画像。

【当前画像】
{current_profile_json}

【用户刚刚问】
{user_input}

【更新规则】
1. 只更新有新信号的字段,其他字段保持不变
2. 每个字段带 confidence(0-1),累积式更新:
   - 首次推断:confidence=0.4
   - 再次确认:在原值上 +0.2,封顶 1.0
   - 矛盾信息:confidence 降到 0.3
3. 不确定就别更新

【输出】更新后的完整 profile JSON,严格 JSON 格式。
```

### 附录 E:suggestion_generator prompt

```
你是用户的工作搭子,刚回答完一个问题。
基于用户的身份和这轮对话,生成 3 条用户可能下一步想做的事。

【用户画像】
- 行业:{industry}
- 岗位:{role}
- 痛点:{pain_points}

【这轮对话】
问:{user_input}
答:{answer_summary}

【可用的 Skills】
{available_skills_list}

【输出要求】
3 条建议,满足:
- 至少 1 条 type="question"(继续问的问题)
- 至少 1 条 type="skill"(用某个 Skill 干活)
- 三条要有梯度:深入 / 横向扩展 / 引申到工作流层面
- 用用户的口吻表达,不要"还想了解什么"这种废话

【输出格式】严格 JSON:
[
  {"type": "question", "text": "...", "skill_key": null},
  {"type": "skill", "text": "...", "skill_key": "weekly_report"}
]
```

---

## 完成记录

### 阶段 0 完成于 2026-05-15

**完成内容**:
- 扫描整个项目代码库（后端 ~40 个 Python 文件，前端 ~14 个 TS 文件，测试 16 个）
- 生成 `docs/CURRENT_STATE.md`：技术栈、目录结构、DB 表结构、调用链路、命名规范
- 生成 `docs/IMPLEMENTATION_PLAN.md`：分阶段改造计划、新增/修改文件清单、风险点

**新增文件**:
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTATION_PLAN.md`

**遗留 TODO**:
- 无代码改动

**用户需注意**:
进入阶段 1 前，请在 `IMPLEMENTATION_PLAN.md` 开头确认两个决策：
1. **数据库**：迁移 PostgreSQL / 保留 SQLite+sqlite-vec / 暂不上向量（推荐选 A 或 C）
2. **用户身份**：单用户模式 / 匿名持久化（推荐 B） / 简单登录

---

### 阶段 1 完成于 2026-05-15

**完成内容**:
- 新增 5 个 ORM 模型：UserModel / UserMemoryModel / IndustrySkillModel / UserSuggestionModel / SkillExecutionModel
- 切换数据库从 SQLite 到 PostgreSQL + pgvector
- `init_database()` 自动启用 vector 扩展 + 创建 IVFFlat 向量索引
- 新增 auth 相关配置项（secret_key、token 过期时间）
- 安装新依赖：asyncpg、pgvector、bcrypt、python-jose

**新增文件**:
- `docs/SETUP.md` — 本地 PostgreSQL + pgvector 环境搭建指南

**修改文件**:
- `backend/memory/models.py` — 追加 5 个新 ORM 模型
- `backend/memory/database.py` — 加 pgvector 扩展初始化 + IVFFlat 索引创建
- `backend/config.py` — 切换 database_url 默认值，新增 secret_key 配置
- `pyproject.toml` — 新增 asyncpg / pgvector / bcrypt / python-jose 依赖
- `.env.example` — 新增 AURA_DATABASE_URL / AURA_SECRET_KEY 示例

**遗留 TODO**:
- 现有测试（test_memory_repo.py 等）使用 SQLite，切换 PostgreSQL 后会失败，阶段后期统一处理
- IVFFlat 索引在数据量 < 100 时效果差，生产前需 VACUUM ANALYZE

**用户需注意**:
- 需要本地启动 PostgreSQL（推荐 Docker：`docker run -d --name aura-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=aura -p 5432:5432 pgvector/pgvector:pg16`）
- 在 `.env` 中设置 `AURA_DATABASE_URL` 和 `AURA_SECRET_KEY`
- 启动后端后，`init_database()` 会自动建表，无需手动执行 SQL

---

### 阶段 2 完成于 2026-05-15

**完成内容**:
- 实现完整 JWT 登录/注册（bcrypt 密码哈希 + python-jose Token）
- 新增 `/api/auth/register`、`/api/auth/login`、`/api/auth/me` 接口
- 新增 `/api/onboarding` 接口（3问画像写入 users.profile）
- 新增 `/api/profile` GET/PATCH 接口
- `build_system_prompt(profile)` 函数：画像注入到主对话 system prompt
- `MemoryManager.build_context()` 扩展：登录用户自动注入画像 system message
- `conversations` 和 `chat` 接口加 auth 保护，对话关联 user_id
- 前端：LoginPage（登录/注册）、OnboardingModal（3步引导）、useAuth hook
- conversations 列表按 user_id 过滤

**新增文件**:
- `backend/core/auth.py` — JWT 工具 + FastAPI 依赖
- `backend/services/profile_service.py` — 画像 CRUD
- `backend/services/prompt_builder.py` — build_system_prompt
- `backend/api/auth.py` — 认证接口
- `backend/api/onboarding.py` — Onboarding 接口
- `backend/api/profile.py` — 画像接口
- `frontend/src/hooks/useAuth.ts` — 前端 Auth 状态
- `frontend/src/components/LoginPage.tsx` — 登录/注册页
- `frontend/src/components/OnboardingModal.tsx` — 3步引导弹窗

**修改文件**:
- `backend/memory/models.py` — ConversationModel 加 nullable user_id FK
- `backend/memory/repo.py` — create/list_conversations 支持 user_id
- `backend/memory/manager.py` — build_context 注入画像 system prompt
- `backend/memory/database.py` — init_database 加 ALTER TABLE 补 user_id 列
- `backend/api/chat.py` — 加 auth 依赖，传 user_id
- `backend/api/conversations.py` — 加 auth 依赖，按 user_id 过滤
- `backend/api/router.py` — 注册新路由
- `frontend/src/App.tsx` — 接入 auth 流程
- `frontend/src/services/api.ts` — 加 token 管理和新 API 调用
- `frontend/src/types/index.ts` — 加 User 类型
- `frontend/src/styles/globals.css` — 加登录页和 Onboarding 样式

**遗留 TODO**:
- 已有 user_facts（跨对话）和新 user_memories 并存，Phase 4 统一

**用户需注意**:
- 现有对话已在 DB 里，但没有 user_id（NULL），不会显示在侧边栏（已过滤）
- 前端需要 rebuild（`npm run build` 或 `npm run dev`）
- 体感测试：注册后完成 Onboarding，再问「帮我写个周报」，观察回答是否有行业感


### 阶段 3 完成于 2026-05-15

**完成内容**:
- 后端：新增 `backend/services/skill_registry.py`（内存缓存 + 关键词匹配）
- 后端：新增 `backend/services/skill_executor.py`（模板渲染 + SSE 流式执行）
- 后端：新增 `backend/api/skills.py`（GET /skills、POST /skills/{key}/execute）
- 后端：`backend/api/chat.py` 加入技能意图识别，匹配时返回 `skill_match` 事件提前短路
- 后端：`backend/main.py` 启动时 seed + load skills
- 前端：新增 `SkillCards.tsx`、`SkillPanel.tsx` 组件
- 前端：`useChat.ts` 新增 `pendingSkillKey`、`executeSkill`、`setPendingSkillKey`
- 前端：`App.tsx` 集成技能卡片和技能面板（chat 区上方）
- 前端：`globals.css` 补充 `.skill-cards`、`.skill-card`、`.skill-panel` 等样式

**新增文件**:
- `backend/services/skill_registry.py`
- `backend/services/skill_executor.py`
- `backend/api/skills.py`
- `frontend/src/components/SkillCards.tsx`
- `frontend/src/components/SkillPanel.tsx`

**修改文件**:
- `backend/api/chat.py`（技能意图检测）
- `backend/main.py`（seed/load skills）
- `backend/agent/schemas.py`（SKILL_MATCH 事件类型）
- `frontend/src/services/api.ts`（fetchSkills、executeSkillSSE）
- `frontend/src/hooks/useChat.ts`（pendingSkillKey、executeSkill）
- `frontend/src/App.tsx`（SkillCards/SkillPanel 集成）
- `frontend/src/styles/globals.css`（skill 样式）

**遗留 TODO**:
- 技能触发关键词目前是简单字符串匹配，可后续升级为向量相似度匹配

**用户需注意**:
- 启动后端时 `seed_default_skills` 会自动写入两条默认技能（会议纪要、周报）
- 在聊天框输入「周报」或「会议纪要」等关键词会自动弹出技能面板
- 也可点击底部技能卡片主动触发
- TypeScript 编译无报错（tsc --noEmit 通过）

### 阶段 4 完成于 2026-05-16

**完成内容**:
- `backend/services/embedder.py`：LiteLLM embedding 封装，graceful 降级（无 embedding_model 时跳过，仍保存文字记忆）
- `backend/services/memory_extractor.py`：LLM 异步提取对话中的用户事实/偏好/目标/背景，写入 user_memories
- `backend/services/memory_service.py`：pgvector 余弦相似度召回（`score = importance×0.3 + similarity×0.7`），降级为按重要度/时间排序
- `backend/api/memories.py`：GET /memories（列表）、DELETE /memories/{id}（删除）
- `backend/memory/manager.py`：build_context 集成记忆召回，注入 build_system_prompt
- `backend/api/chat.py`：后台任务新增 extract_and_save_memories
- config.py：新增 `embedding_model`（默认空 = 跳过）和 `lite_model` 配置项

**新增文件**:
- `backend/services/embedder.py`
- `backend/services/memory_extractor.py`
- `backend/services/memory_service.py`
- `backend/api/memories.py`

**用户需注意**:
- 要启用向量召回，在 .env 设 `AURA_EMBEDDING_MODEL=openai/doubao-embedding-xxx`
- 不设置也能正常工作，召回退化为按重要度排序

---

### 阶段 5 完成于 2026-05-16

**完成内容**:
- `backend/services/profile_updater.py`：异步从对话推断画像更新（confidence 累积式，confidence=0.4 起步）
- `backend/services/suggestion_generator.py`：异步生成 3 条建议（≥1 question + ≥1 skill），写入 user_suggestions
- `backend/api/suggestions.py`：GET /suggestions/latest
- `backend/api/chat.py`：后台任务新增 profile 更新 + 建议生成
- 前端：`SuggestionsBar.tsx`（轮询最新建议，question 点击直接发送，skill 点击打开面板）
- 前端：api.ts 新增 fetchLatestSuggestions

**新增文件**:
- `backend/services/profile_updater.py`
- `backend/services/suggestion_generator.py`
- `backend/api/suggestions.py`
- `frontend/src/components/SuggestionsBar.tsx`

**用户需注意**:
- 建议约 1-3 秒后异步到达，SuggestionsBar 最多轮询 4 次（间隔 1.5s）
- 建议仅在有消息且流式结束后显示

---

### 阶段 6 完成于 2026-05-16

**完成内容**:
- `backend/api/stats.py`：扩展 GET /stats/dashboard（用户数、对话数、技能使用、建议点击率）
- 前端：`ProfilePage.tsx`（画像 tab + 记忆 tab，字段可编辑，记忆可删除）
- 前端：header 加"用户名"按钮打开档案页、"退出"按钮
- 前端：api.ts 新增 patchProfile / fetchMemories / deleteMemory
- CSS：profile-overlay / profile-modal / memory-item 等全套样式

**新增文件**:
- `frontend/src/components/ProfilePage.tsx`

**用户需注意**:
- 档案页手动修改字段后置信度自动变 100%
- 记忆删除立即生效，刷新后不再召回

---

### 阶段 7 完成于 2026-05-16

**完成内容**:
- skill_registry.py 新增 3 个 Skills（bug_tracker / requirement_classifier / okr_review），共 5 个
- `backend/api/feedback.py`：POST /feedback（rating + comment，记录到 trace 日志）
- 前端：`FeedbackButton.tsx`（右下角悬浮按钮，星级 + 文字反馈，提交后 1.5s 自动关闭）
- 前端：CSS 补充 feedback-fab / feedback-modal 等样式

**新增文件**:
- `backend/api/feedback.py`
- `frontend/src/components/FeedbackButton.tsx`

**用户需注意**:
- 5 个 Skills 首次启动时自动 seed，无需手动操作
- 反馈数据目前写入日志（trace），后续可接数据库或飞书表单
- 全阶段 TypeScript 编译无报错（tsc --noEmit 通过）

---

### SQL 迁移完成于 2026-05-16

**完成内容**:
- 执行 `docs/sql/migrations/001_schema_update.sql`：
  - industry_skills 表新增字段：tagline / display_metadata / is_universal / layer / version / experiment_group
  - industry/role 两列改为可 NULL（已废弃，由 skill_role_mapping 代替）
  - created_at / updated_at 设置 DEFAULT NOW()
  - 新建：skill_role_mapping（多对多映射）/ skill_signals（行为埋点）/ skill_metrics_daily（聚合指标）/ user_skill_affinity（偏好评分）表
  - 创建触发器：skill_executions 完成后自动写 skill_signals + 更新 user_skill_affinity
- 执行 `docs/sql/migrations/002_seed_skills.sql`（用修改版，去掉 BEGIN/COMMIT，ON_ERROR_STOP=off）：
  - 插入 23 个新 Skill（weekly_report 因已存在跳过）
  - 写入 155 条 skill_role_mapping，覆盖 9 个行业、20 个角色
- 禁用老的 4 个占位 Skill（meeting_notes / bug_tracker / requirement_classifier / okr_review）
- 更新 weekly_report 以匹配 002 种子数据（scenario_name / tagline / input_schema 等）

**修改文件**:
- `backend/memory/models.py`：
  - IndustrySkillModel：industry/role 改可 NULL，新增 tagline/is_universal/layer 等字段，添加 role_mappings relationship
  - 新增 SkillRoleMappingModel（映射 skill_role_mapping 表）
- `backend/services/skill_registry.py`：
  - 删除 seed_default_skills 及全部 _DEFAULT_SKILLS 常量
  - load_skills 同时加载 skill_role_mapping，构建 _role_index 缓存
  - list_skills 按 priority（essential→recommended→optional）排序，无匹配退化到全量
  - _to_dict 新增 tagline / is_universal / layer 字段
- `backend/main.py`：移除 seed_default_skills 调用

**数据库现状**:
- 24 个 enabled Skill（4 个老 Skill 已 disabled）
- 155 条 skill_role_mapping

**用户需注意**:
- 002.sql 使用去掉事务的修改版执行，原始文件未改动
- 后端重启后自动加载新 Skills，无需手动操作
- 有 industry+role 的用户将看到按优先级排序的 Skills，无画像用户看到全量列表

---

## 阶段 8：计费系统

> 设计已确认（2026-05-16），分 A / B / C 三个子阶段实现。
> 详细设计见 `docs/BILLING.md`。

### 阶段 8A — 核心计费（后端 + 基础前端提示）

**目标**：上线额度检查，Free 用户用完后无法继续发送，看到升级 Banner。

**后端**：
- SQL migration `docs/sql/migrations/003_billing.sql`：新建 `user_quotas` 表
- `backend/services/quota_service.py`：额度检查、自动重置、+1 逻辑
- `POST /chat` 和 `POST /skills/:key/execute` 接入 quota 检查，超额返回 402
- 新增 `GET /api/quota` 接口

**前端**：
- 全局 quota 状态（登录后拉取，存入 context 或简单 state）
- 输入框上方：剩余 ≤ 5 次时显示灰色提示行
- 输入框替换为升级 Banner（当次数 = 0 或收到 402 时）

---

### 阶段 8B — 报价页 + 用户菜单档位

**目标**：用户能看到完整定价对比，能从 Banner / 菜单进入报价页。

- `GET /api/pricing` 接口（返回静态价格配置）
- `PricingModal` 组件：三栏对比（Free / Pro / Max），Pro 列高亮推荐
- MVP 升级入口：点击后显示微信二维码 / 联系客服
- 用户菜单底部显示当前计划标签 + "升级"入口
- `GET /api/conversations` 对 Free 用户加 30 天时间过滤

---

### 阶段 8C — 真实支付（独立迭代，暂不排期）

- 支付宝 / 微信支付接入
- 支付 Webhook → plan 自动升级
- 到期续费 / 降级处理
- 收据邮件

---

**定价速查**：

| | Free | Pro | Max |
|---|---|---|---|
| 价格 | ¥0 | ¥39/月 | ¥99/月 |
| 限额 | 20 次/天 | 1000 次/月 | 无限制 |
| 历史对话 | 近 30 天 | 永久 | 永久 |

---

### 阶段 8B 完成于 2026-05-16

**完成内容**：
- `GET /api/pricing` 静态接口，返回三档定价配置
- `PricingModal` 三栏对比组件，Free/Pro/Max，Pro 列高亮+推荐标签，MVP 升级点击后显示联系信息
- `QuotaBanner` 接入 `onUpgrade` prop，升级按钮打开 PricingModal
- Sidebar 用户菜单底部新增计划行：彩色圆点 + 计划名称 + Free 用户"升级 →"链接
- `GET /api/conversations` 对 Free 用户加 30 天过滤（`repo.list_conversations` 支持 `since` 参数）

**新增文件**：
- `backend/api/pricing.py`
- `frontend/src/components/PricingModal.tsx`

**修改文件**：
- `backend/api/router.py` — 注册 pricing_router
- `backend/api/conversations.py` — Free 用户 30 天历史过滤
- `backend/memory/repo.py` — `list_conversations` 新增 `since` 参数（Protocol + 实现）
- `frontend/src/components/QuotaBanner.tsx` — 加 `onUpgrade` prop
- `frontend/src/components/Sidebar.tsx` — 加 `plan`/`onUpgrade` prop，用户菜单计划行
- `frontend/src/App.tsx` — 加 `showPricing` 状态，接入 PricingModal
- `frontend/src/styles/globals.css` — PricingModal 样式 + 用户菜单计划行样式

**遗留 TODO**：
- 阶段 8C：真实支付接入（支付宝/微信），自动升级 plan
- PricingModal 联系方式（`hi@useaura.ai`）需替换为实际邮箱或微信二维码图片

---

## 阶段 9：Skill Marketplace（技能市场）

> 详细设计见 `docs/SKILL_MARKETPLACE.md`

**目标**：用户能主动管理自己的技能库，Chatbox 技能卡片由「用户 pin + 系统推荐」混合填充。

### 核心规则

- Chatbox 固定展示 6 个 skill
- 用户 pin 上限 4 个（设置面板管理）
- 剩余位置由系统推荐填充（临时，不持久化到用户技能库）
- 设置面板只展示用户主动添加的 skill，推荐不出现在这里

### Phase A 任务（待实现）

**后端**

- [ ] DB migration `004_user_skills.sql`：新增 `user_skills` 表
- [ ] `GET /api/skills/my` — 用户已添加的 skill 列表
- [ ] `GET /api/skills/market` — 技能市场全量列表（含 is_added 状态）
- [ ] `POST /api/skills/{key}/add` — 添加到我的技能
- [ ] `DELETE /api/skills/{key}/remove` — 从我的技能移除
- [ ] `PATCH /api/skills/{key}/pin` — 切换 pin 状态（超 4 个返回 400）
- [ ] 改造 `GET /api/skills` — 返回 pin 的 + 补足推荐到 6 个

**前端**

- [ ] 更多面板改造 → 「我的技能」+「技能市场」两个 tab
- [ ] 技能市场 grid（24 个 skill，含已添加状态标记）
- [ ] 技能详情 Modal（描述、字段预览、添加/移除按钮）
- [ ] 我的技能列表（pin/unpin/移除操作）
- [ ] Chatbox 卡片按新规则渲染（pin 优先 + 推荐补位）

### 阶段 9 Phase A 完成于 2026-05-16

**完成内容**：
- DB migration `004_user_skills.sql`，`user_skills` 表上线（含唯一约束、索引）
- `UserSkillModel` ORM 模型
- `GET /api/skills` 改造：pin 的先展示，剩余槽位由 profile 推荐填充，固定返回 6 个
- `GET /api/skills/market` — 24 个 skill + is_added 状态
- `GET /api/skills/my` — 用户已添加的 skill（含 is_pinned、use_count）
- `POST /api/skills/{key}/add` — 添加到技能库
- `DELETE /api/skills/{key}/remove` — 移除
- `PATCH /api/skills/{key}/pin` — 切换固定，超 4 个返回 400
- 前端：更多面板 Skill 区域改为双 tab（我的技能 + 技能市场）
- 前端：技能市场 grid（24 张卡，已添加绿色 badge）
- 前端：技能详情 Modal（描述、字段预览、添加/移除 toggle）
- 前端：我的技能列表（pin/unpin/移除操作）
- `api.ts` 新增 `SkillDef` / `MarketSkill` / `MySkill` 类型 + 5 个 API 函数

**新增文件**：
- `docs/sql/migrations/004_user_skills.sql`
- `frontend/src/components/SkillDetailModal.tsx`

**修改文件**：
- `backend/memory/models.py` — UserSkillModel
- `backend/services/skill_registry.py` — get_skill_by_id / all_skills
- `backend/api/skills.py` — 全面重写，新增 5 个端点
- `frontend/src/components/MoreView.tsx` — 双 tab 技能面板
- `frontend/src/services/api.ts` — 新类型和 API 函数

### Phase B 任务（后续迭代）

- [ ] skill 执行成功后写回 use_count / last_used_at
- [ ] 推荐逻辑升级：热度 + 对话上下文实时置换
- [ ] 我的技能拖拽排序

---

## 阶段 10：行业 & 岗位升级

**目标**：针对律师、医生、公司法务、学生四个垂直行业，新增 21 个专属 Skill，并实现行业→岗位联动选择体验。

### 任务清单

**后端**：
- [x] `docs/sql/migrations/005_new_industry_skills.sql` — 21 个新 Skill 的完整 INSERT + skill_role_mapping
- [x] 修复 JSON 格式问题（中文引号）→ `005_fix_json.sql`

**前端**：
- [x] `frontend/src/config/industries.ts` — 行业→岗位→痛点 统一配置文件
- [x] `OnboardingModal.tsx` — 行业改为图标卡片（4 列网格），岗位根据行业动态更新，痛点随行业变化
- [x] `ProfilePage.tsx` — 行业/岗位/AI 熟练度改为 chip 选择器
- [x] `globals.css` — 新增 `.industry-cards`、`.industry-card`、`.profile-chip-selector` 等样式

### 阶段 10 完成于 2026-05-17

**完成内容**：
- 新增 21 个行业专属 Skill（法律 5 个 / 医疗 5 个 / 公司法务 5 个 / 学生 6 个）
- 每个 Skill 包含完整 prompt_template、input_schema、trigger_keywords、tagline
- skill_role_mapping 覆盖 4 行业 × 4 岗位，含 essential/recommended/optional 优先级
- Onboarding 行业选择改为带 emoji 的图标卡片（7 个行业），选行业后动态显示该行业专属岗位
- ProfilePage 行业/岗位/AI熟练度 编辑改为 chip 选择器（行业选择器含 emoji）
- Modal 宽度调整为 520px，支持 overflow-y: auto

**新增文件**：
- `docs/sql/migrations/005_new_industry_skills.sql`
- `docs/sql/migrations/005_fix_json.sql`
- `frontend/src/config/industries.ts`

**修改文件**：
- `frontend/src/components/OnboardingModal.tsx`
- `frontend/src/components/ProfilePage.tsx`
- `frontend/src/styles/globals.css`

**遗留 TODO**：
- 阶段 9 Phase B：use_count 写回、推荐升级、拖拽排序
- 阶段 8C：真实支付集成
- 可考虑：将 005_fix_json.sql 内容并入 005_new_industry_skills.sql（合并为一个干净的迁移文件）
