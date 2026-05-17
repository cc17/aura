# Aura

AI Agent，支持可插拔 Tool 系统，当前使用豆包大模型。

## 前置要求

- Python 3.11+（项目通过 uv 自动管理）
- Node.js 18+
- [uv](https://docs.astral.sh/uv/)（Python 包管理）
- 豆包 API Key

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的豆包 API Key：

```
ARK_API_KEY=你的Key
```

### 2. 安装依赖

```bash
# 后端（首次运行会自动下载 Python 3.12）
uv venv --python 3.12
uv pip install -e ".[dev]"

# 前端
cd frontend && npm install
```

### 3. 启动后端

```bash
uv run uvicorn backend.main:app --reload
```

后端运行在 http://localhost:8000

### 4. 启动前端（新开终端）

```bash
cd frontend && npm run dev
```

前端运行在 http://localhost:5173，API 请求自动代理到后端。

### 5. 打开浏览器

访问 http://localhost:5173 即可开始对话。

## 运行测试

```bash
uv run pytest tests/ -v
```

## 项目结构

```
aura/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（从 .env 读取）
│   ├── agent/
│   │   ├── core.py          # Agent 调度循环
│   │   └── schemas.py       # 数据模型
│   ├── api/                 # REST + SSE 端点
│   ├── llm/                 # LiteLLM 封装
│   ├── tools/               # 可插拔 Tool 系统
│   │   ├── base.py          # BaseTool 抽象类
│   │   ├── registry.py      # 自动发现注册
│   │   └── resume_tool.py   # 简历 Tool（接口）
│   └── storage/             # 内存会话存储
├── frontend/                # React + Vite + TypeScript
└── tests/
```

## 添加新 Tool

在 `backend/tools/` 下新建一个 `.py` 文件，继承 `BaseTool` 即可，启动时自动注册：

```python
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

class MyTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="工具描述",
            parameters=[
                ToolParameter(name="input", type="string", description="参数描述"),
            ],
        )

    async def execute(self, **kwargs) -> str:
        return "结果"
```

## API 端点

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/chat` | 发送消息（SSE 流式返回） |
| GET | `/api/models` | 获取可用模型列表 |
| GET | `/api/tools` | 获取已注册 Tools |
| POST | `/api/conversations` | 创建新会话 |
| GET | `/api/conversations` | 获取会话列表 |
| GET | `/api/conversations/{id}` | 获取会话详情 |
