# Aura

**An AI work assistant that gets smarter the more you use it.**

Unlike generic AI chatbots, Aura remembers your context across sessions, understands your industry and role, proactively suggests the right tool for what you're doing, and improves its recommendations over time based on your behavior.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/cc17/aura/pulls)

<!-- SCREENSHOT: home screen showing skill cards + a conversation with in-context skill suggestion -->

---

## Why Aura

Most AI tools treat every session as a blank slate. Aura is built around the opposite idea.

| Generic AI chat | Aura |
|----------------|------|
| Starts from scratch every session | Remembers your colleagues, projects, and preferences across sessions |
| One-size-fits-all responses | Adapts to your industry and role (law, medicine, tech, student, ...) |
| You have to know what to ask | Detects your intent mid-conversation and surfaces the right Skill |
| Recommendations never change | Learns from your behavior — what you click, complete, and copy |

---

## Core Features

### 🧠 Long-term Memory
Extracts facts, preferences, and goals from every conversation and stores them in a vector database (pgvector). Recalls the most relevant memories before each response — so Aura remembers your manager's name, your project deadline, and that you prefer bullet-point answers.

### 🎯 Industry Skills (24+ built-in)
Structured task workflows optimized for specific professions:
- **Legal**: contract review, case summary, legal research memo
- **Medical**: clinical note, patient education sheet, differential checklist
- **Product / Dev**: meeting notes, weekly report, bug triage, OKR review
- **Students**: essay outline, exam prep, literature summary

Each Skill has a curated prompt template, typed input fields, and example outputs — no prompt engineering required.

### 📊 Recommendation Pipeline (Home Screen)
A 5-stage RecSys pipeline surfaces the right Skills before you even type:

```
Context (profile: industry / role / pain-points)
  → Recall       skill_role_mapping priority + universal skills
  → Coarse Rank  max 2 per category (diversity control)
  → Fine Rank    profile_match×0.40 + CTR×0.25 + affinity×0.25 + recency×0.10
  → Re-rank      pinned skills injection + cool-down filter
```

Impression and click events are tracked in `skill_signals`, so the rankings improve as usage data accumulates.

### 🔍 In-conversation Intent Detection (System 2)
While you type, Aura runs a parallel pipeline to detect whether you need a Skill:

```
Message
  → Hard rules    explicit keyword match → instant trigger
  → Embedding recall   cosine similarity against all skill embeddings (top-5)
  → Fine rank     semantic_sim×0.40 + profile×0.20 + quality×0.25 + affinity×0.15
  → Confidence threshold (< 0.55 → no trigger, no interruption)
```

Skill embeddings are pre-computed at startup and cached in memory, so latency impact per message is a single embedding call.

### 🔄 Evolving User Profile
A lightweight background agent infers and updates your profile (industry, role, pain points) from each conversation with confidence accumulation. The profile feeds every ranking and personalization layer.

### 💡 Contextual Suggestions
After each response, a background agent generates 3 follow-up suggestions — at least one follow-up question and one Skill action — tailored to the current conversation.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  FastAPI Backend                                     │
│                                                     │
│  POST /chat                                          │
│    ├─ Intent detection  (embedding recall, System 2) │
│    ├─ Context builder   (profile + memory recall)    │
│    ├─ LLM call          (DeepSeek / Claude via       │
│    │                     LiteLLM, streaming SSE)     │
│    └─ Background tasks:                              │
│         memory extraction → pgvector                 │
│         profile update                               │
│         suggestion generation                        │
│                                                     │
│  GET /api/recommendations   (System 1 pipeline)     │
│  POST /api/recommendations/events  (signal tracking) │
└─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  PostgreSQL + pgvector                               │
│  users · conversations · messages                   │
│  user_memories (vector)                              │
│  industry_skills · skill_role_mapping               │
│  skill_signals · user_skill_affinity                │
│  user_skills · user_suggestions · skill_executions  │
└─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  React + TypeScript frontend                         │
│  SSE streaming · Skill cards · Skill panel          │
│  Profile page · Suggestion bar                       │
└─────────────────────────────────────────────────────┘
```

**LLM support**: any model accessible via LiteLLM (Doubao, DeepSeek, Claude, GPT-4, etc.)

---

## Quick Start

**Prerequisites**: Python 3.11+, Node.js 18+, PostgreSQL 15+ with pgvector, [uv](https://docs.astral.sh/uv/)

```bash
# 1. Clone
git clone https://github.com/cc17/aura.git && cd aura

# 2. Configure
cp .env.example .env
# Edit .env: set AURA_ARK_API_KEY, AURA_DATABASE_URL, AURA_SECRET_KEY

# 3. Install & migrate
uv venv --python 3.12 && uv pip install -e ".[dev]"
cd frontend && npm install && cd ..

# 4. Run
uv run uvicorn backend.main:app --reload   # http://localhost:8000
cd frontend && npm run dev                  # http://localhost:5173
```

See [docs/SETUP.md](docs/SETUP.md) for database setup with Docker.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy 2 async, Pydantic |
| LLM | LiteLLM (Doubao / DeepSeek / Claude / any OpenAI-compatible) |
| Database | PostgreSQL 16 + pgvector |
| Auth | JWT (python-jose + bcrypt) |
| Frontend | React 18, TypeScript, Vite |
| Embeddings | Configurable via `AURA_EMBEDDING_MODEL` (optional) |

---

## Changelog

### v0.5 — Recommendation Pipeline (2026-05-20)
- **System 1**: 5-stage home screen recommendation (recall → coarse rank → fine rank → re-rank)
- **System 2**: In-conversation intent detection via embedding recall, replacing brittle keyword matching
- Impression/click tracking with `skill_signals`; quality signals (completion, adoption, abandonment) feed fine ranking
- `SkillSignalModel` + `UserSkillAffinityModel` ORM; `GET /api/recommendations` + `POST /api/recommendations/events`

### v0.4 — Skill Marketplace & Industry Expansion (2026-05-17)
- 24+ Skills across 7 industries (legal, medical, corporate law, tech, student, etc.)
- Skill Marketplace UI: browse, add, pin, and manage your Skill library
- Industry × role onboarding with dynamic chip selectors
- `skill_role_mapping`: many-to-many priority mapping (essential / recommended / optional)

### v0.3 — Billing & Quota System (2026-05-16)
- Free / Pro / Max tiers with daily/monthly quota enforcement
- Quota banner, upgrade flow, pricing modal
- Conversation history limited to 30 days on Free tier

### v0.2 — Memory, Profile & Suggestions (2026-05-16)
- Long-term memory extraction → pgvector storage → similarity recall
- Async profile updater with confidence accumulation
- Post-response suggestion bar (questions + Skill shortcuts)
- Personal profile page: view and edit profile fields, delete memories

### v0.1 — Foundation (2026-05-15)
- JWT auth (register / login), user onboarding (3-question flow)
- Industry Skills framework: `industry_skills` table, Skill executor (SSE streaming)
- Profile injected into system prompt for contextual responses
- PostgreSQL migration from SQLite, pgvector extension

---

## Roadmap

- [ ] **Phase 11B** — Daily cron to aggregate `skill_metrics_daily` (pre-computed CTR / completion / adoption rates)
- [ ] **Phase 11C/D** — Affinity score update from conversation signals; recommendation cool-down logic
- [ ] **Phase 13** — Admin dashboard: skill performance metrics, user funnel, A/B experiment support
- [ ] **Phase 14** — Collaborative filtering recall (users-like-you)
- [ ] **Phase 15** — Payment integration (Alipay / WeChat Pay)

---

## Contributing

Pull requests are welcome. For large changes, please open an issue first to discuss the direction.

```bash
uv run pytest tests/ -v   # run tests
```

---

## License

MIT
