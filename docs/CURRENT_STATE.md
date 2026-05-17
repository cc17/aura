# CURRENT_STATE.md

> 阶段 0 勘查产出。描述项目现状，供改造前对齐。

---

## 1. 技术栈

| 层 | 技术 |
|---|---|
| 语言 | Python 3.11+（后端）、TypeScript（前端） |
| Web 框架 | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.x（async） |
| **数据库** | **SQLite**（文件 `aura.db`，通过 aiosqlite） |
| Agent 框架 | LangGraph 0.4+ |
| LLM 调用 | LiteLLM + LangChain（langchain-bridge 封装） |
| **当前 LLM** | **豆包 doubao-1-5-pro-32k-250115**（字节跳动 Ark API） |
| Token 计数 | tiktoken |
| 前端构建 | Vite + React 18 + TypeScript |
| 前端 UI | 纯自定义 CSS，无额外 UI 框架 |
| 测试 | pytest + pytest-asyncio |
| Lint | ruff（line-length=100） |
| 包管理 | uv |

---

## 2. 目录结构与职责

```
aura/
├── backend/
│   ├── agent/
│   │   ├── core.py          # AgentCore：LangGraph → SSE 事件桥接，含 reflection 输出门控
│   │   ├── intent.py        # 意图分类：关键词正则（阶段1）+ LLM兜底（阶段2）
│   │   └── schemas.py       # Message/Role/StreamEvent 等核心数据类型
│   ├── api/
│   │   ├── chat.py          # POST /api/chat：主对话入口，SSE 流式返回
│   │   ├── conversations.py # CRUD 会话列表/详情/归档
│   │   ├── files.py         # 文件上传/下载
│   │   ├── models.py        # GET /api/models：可用模型列表
│   │   ├── router.py        # 汇总所有路由，挂 /api 前缀
│   │   ├── stats.py         # 统计数据接口
│   │   └── tools.py         # 工具列表接口
│   ├── config.py            # Settings（pydantic-settings，AURA_ 前缀环境变量）
│   ├── data/gaokao/         # 高考静态数据（省份模型、分数段、院校数据）
│   ├── graph/
│   │   ├── supervisor.py    # LangGraph 图定义：supervisor + 5 worker + reflection
│   │   ├── state.py         # AuraState TypedDict
│   │   └── agents/          # 各 worker 的 create_xxx_agent() 工厂函数
│   ├── llm/
│   │   ├── kv_cache.py      # KV 缓存（supervisor 5min TTL，reflection 10min TTL）
│   │   ├── langchain_bridge.py # create_chat_model() 封装
│   │   ├── models.py        # 模型别名映射
│   │   └── provider.py      # LiteLLMProvider（litellm.acompletion 封装）
│   ├── memory/
│   │   ├── database.py      # 引擎创建、session factory、init_database()
│   │   ├── fact_extractor.py # 异步：从对话提取用户事实（LLM调用）
│   │   ├── manager.py       # MemoryManager：build_context / maybe_summarize / extract_and_save_facts
│   │   ├── models.py        # ORM 模型（Conversation/Message/Summary/UserFact）
│   │   ├── repo.py          # SQLAlchemyConversationRepo 数据访问层
│   │   ├── summarizer.py    # 对话摘要（LLM调用）
│   │   └── token_counter.py # tiktoken 封装
│   ├── observability/
│   │   └── tracer.py        # trace() / trace_span()，输出到 aura_trace.log（JSON lines）
│   ├── storage/
│   │   ├── cache_store.py   # 内存 KV 缓存（LRU + TTL）
│   │   ├── file_store.py    # 文件持久化
│   │   └── memory.py        # 内存存储抽象
│   ├── tools/               # Tool 注册表 + 11 个工具实现
│   └── utils/               # docx_builder, file_parsers
├── frontend/
│   └── src/
│       ├── App.tsx           # 根组件：Sidebar + 主面板布局
│       ├── components/       # ChatWindow, ChatInput, Sidebar, AgentIndicator,
│       │                     # ToolIndicator, ModelSelector, MessageBubble
│       ├── hooks/            # useChat（SSE 状态管理）, useModels
│       ├── services/api.ts   # 所有 HTTP/SSE 调用封装
│       └── types/index.ts    # 前端类型定义
├── tests/                   # 16 个测试文件，覆盖核心模块
├── docs/                    # ARCHITECTURE.md, PRODUCT_VISION.md, ROADMAP.md
├── pyproject.toml           # 依赖定义
└── .env                     # 本地配置（不入库）
```

---

## 3. 当前数据库表结构

数据库用 `Base.metadata.create_all` 初始化（**无 Alembic**，无迁移脚本）。

### conversations
| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(32) PK | UUID hex |
| title | String(200) | 自动从首条消息截取前50字 |
| summary | Text | LLM 生成的对话摘要 |
| summary_through_idx | Integer | 摘要覆盖到第几条消息 |
| message_count | Integer | 消息总数 |
| created_at / updated_at / archived_at | DateTime(TZ) | 时间戳 |

### messages
| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(32) PK | |
| conversation_id | FK→conversations | |
| idx | Integer | 会话内顺序索引 |
| role | String(20) | user/assistant/system |
| content | Text | 消息正文 |
| tool_calls | JSON | 工具调用（可选） |
| tool_result | JSON | 工具结果（可选） |
| token_count | Integer | |
| is_pinned | Boolean | 首条/含文件的消息固定 |

### conversation_summaries
摘要审计日志，每次更新时追加一条记录。

### user_facts
| 字段 | 类型 | 说明 |
|---|---|---|
| id | String(32) PK | |
| category | String(50) | demographic/education/career/preferences/... |
| content | Text | 一句话事实 |
| source_conversation_id | String(32) | 来源会话 |

> **关键点**：`user_facts` 是全局的（无 user_id），不支持向量搜索，用 LLM 全量替换更新。

### ⚠️ 没有 users 表，没有认证系统

---

## 4. 核心调用关系

```
前端 POST /api/chat (multipart: message, model?, conversation_id?, file?)
  └─▶ api/chat.py
        ├─ 创建/加载 conversation（SQLite）
        ├─ 保存 user message
        ├─ MemoryManager.build_context(conv_id)
        │    ├─ 拉取 user_facts → 注入为 system message
        │    ├─ 拉取 conversation.summary → 注入为 system message
        │    └─ 滑动窗口装载 messages（token budget 25k）
        ├─ AgentCore.run(history)
        │    └─ LangGraph graph.astream_events()
        │         ├─ supervisor node（关键词匹配 or LLM routing）
        │         ├─ worker agent（general/resume/gaokao/ppt/research）
        │         └─ reflection node（质量评分，max 3 轮）
        ├─ SSE 流式返回（text_delta / thinking / tool_call / done / error）
        ├─ 保存 assistant message
        └─ asyncio.create_task(_background_memory_tasks)
              ├─ MemoryManager.maybe_summarize()  [超30条触发]
              └─ MemoryManager.extract_and_save_facts()  [LLM提取，全量替换]
```

---

## 5. LLM 调用现状

- **唯一模型**：豆包 doubao-1-5-pro-32k-250115，通过字节跳动 Ark API
- **调用方式**：LiteLLM → `litellm.acompletion(model="openai/...", api_base=..., api_key=...)`
- **LangChain 桥接**：`create_chat_model()` 返回 ChatOpenAI 兼容对象（`api_base` + `api_key` 注入）
- **KV 缓存**：supervisor 路由调用缓存 5 min，reflection 评分缓存 10 min
- **无辅助/轻量模型**：所有 LLM 调用（对话、摘要、事实提取、reflection）全用同一个模型

---

## 6. 对话历史存储方式

1. 每条消息存 `messages` 表，带 `idx` 顺序号
2. 超过 30 条未摘要消息时，LLM 生成摘要，摘要存 `conversations.summary`
3. 请求时：摘要 + 近期消息组装 context，token budget 25k
4. 用户事实（跨会话）：`user_facts` 全局表，每次对话结束后 LLM 重新提取并全量替换
5. **没有向量化**，没有语义检索

---

## 7. 现有命名规范与代码风格

- **Python**：snake_case 函数/变量，PascalCase 类，`_` 前缀私有
- **文件名**：snake_case
- **TypeScript**：PascalCase 组件，camelCase 变量/函数
- **异步**：全面使用 `async/await`，SQLAlchemy async session
- **session 管理**：`async with session_factory() as session`，每个请求独立 session
- **日志**：`logging.getLogger(__name__)`，关键路径用 `trace()` 写 JSON 行
- **注释**：极简，只标注非显而易见的逻辑
- **行宽**：100

---

## 8. 现有工具清单（Tools）

| 工具 key | 功能 |
|---|---|
| web_search | Serper API 网页搜索 |
| url_scraper | BeautifulSoup 网页抓取 |
| search_jobs | 职位搜索 |
| resume_advisor | 简历分析建议 |
| ppt_builder | python-pptx 生成 PPT |
| find_schools | 高考院校查询 |
| score_to_rank | 分数换算位次 |
| career_outlook | 就业前景分析 |
| export_docx | python-docx 导出文档 |
| interest_assessment | 兴趣测评 |
| check_requirements | 需求核查 |

---

## 9. 与目标架构的关键差距

| 目标能力 | 现状 | 差距等级 |
|---|---|---|
| users 表 + 用户画像 | **不存在** | 🔴 全新建设 |
| Onboarding 流程 | **不存在** | 🔴 全新建设 |
| 数据库 PostgreSQL | **使用 SQLite** | 🔴 基础设施决策 |
| 向量记忆（pgvector） | **不存在**，现有 user_facts 纯文本 | 🔴 全新建设 |
| Skills 框架（DB驱动） | **不存在**，现有是硬编码 agent 路由 | 🔴 全新建设 |
| 推荐生成（猜你想问） | **不存在** | 🟡 新增 |
| 辅助/轻量 LLM | **不存在**，全用主模型 | 🟡 配置扩展 |
| 个人档案页 | **不存在** | 🟡 新增前端页面 |
| 画像自动演化 Agent | **不存在** | 🟡 新增异步任务 |
| 对话摘要（已有） | ✅ 已实现 | — |
| 事实提取（简版已有） | ✅ 已实现（user_facts，无向量） | 需升级 |
| 意图路由（已有） | ✅ 已实现（5 个 agent 路由） | 需扩展支持 Skills |
| SSE 流式返回（已有） | ✅ 已实现 | — |
| 反射循环（已有） | ✅ 已实现 | — |
