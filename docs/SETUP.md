# SETUP.md

> 本地开发环境搭建指南。

---

## 1. 依赖

- Python 3.11+
- Node 18+ (前端)
- **PostgreSQL 14+（必须）**
- **pgvector 扩展（必须）**

---

## 2. PostgreSQL 安装

### macOS (Homebrew)

```bash
brew install postgresql@16
brew services start postgresql@16

# 安装 pgvector
brew install pgvector
```

### Docker（推荐，最简单）

```bash
docker run -d \
  --name aura-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=aura \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

> Docker 镜像 `pgvector/pgvector` 已内置 pgvector 扩展，无需额外安装。

---

## 3. 创建数据库

```bash
# 连接 PostgreSQL
psql -U postgres

# 创建数据库（如果不用 Docker 默认创建的话）
CREATE DATABASE aura;

# 退出
\q
```

pgvector 扩展会在应用启动时由 `init_database()` 自动启用，无需手动执行。

---

## 4. 配置环境变量

复制 `.env.example` 并修改：

```bash
cp .env.example .env
```

`.env` 最小配置：

```
AURA_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aura
AURA_ARK_API_KEY=你的豆包API_KEY
AURA_SECRET_KEY=一段随机字符串用于JWT签名
```

---

## 5. 启动后端

```bash
uv run uvicorn backend.main:app --reload
```

首次启动时 `init_database()` 会自动：
1. 启用 `vector` 扩展
2. 创建所有表
3. 创建 IVFFlat 向量索引

---

## 6. 启动前端

```bash
cd frontend
npm install
npm run dev
```

---

## 7. 向量维度说明

`user_memories.embedding` 列当前维度为 **1536**（适用于 OpenAI text-embedding-3 或 text-embedding-v3）。

若使用 **bge-large-zh-v1.5**（维度 1024），需修改 `backend/memory/models.py` 中的 `_EMBEDDING_DIM = 1024`，并重新建表。
