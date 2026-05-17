# Skill Marketplace 设计文档

> 状态：设计已确认，待实现（阶段 9）

---

## 一、核心概念

### 两个表面，各司其职

| 表面 | 内容来源 | 用户能管理吗 | 推荐会出现吗 |
|---|---|---|---|
| **设置面板（我的技能）** | 用户主动添加 | ✓ pin/unpin/删除 | ✗ 不会 |
| **Chatbox 技能卡片** | 用户 pin + 系统智能填充 | ✗（推荐不在这管）| ✓ 补位 |

**设计原则**：用户永远不会在设置里看到"我没加过的东西"，设置面板保持干净；Chatbox 卡片聪明但不打扰。

---

## 二、Chatbox 展示规则

**总数固定 6 个，Pin 上限 4 个（硬限制）。**

| 用户 pin 数 | Chatbox 展示 |
|---|---|
| 0 个（新用户）| 6 个全是系统推荐 |
| 2 个 | 2 pin + 4 推荐 |
| 4 个 | 4 pin + 2 推荐 |

### 推荐优先级（填充剩余位置）

1. **最近使用过的 skill**（7 天内，按 use_count 降序）
2. **当前对话上下文命中**（关键词匹配，后端已有 `find_by_keywords`）
3. **Profile 匹配**（industry/role 的 skill_role_mapping 优先级）

推荐是**临时的、不持久的**，不写入用户的"我的技能"。

---

## 三、数据模型

### 新表：`user_skills`

```sql
CREATE TABLE user_skills (
  id           BIGSERIAL PRIMARY KEY,
  user_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill_id     INT NOT NULL REFERENCES industry_skills(id) ON DELETE CASCADE,
  is_pinned    BOOLEAN NOT NULL DEFAULT FALSE,
  use_count    INT NOT NULL DEFAULT 0,
  last_used_at TIMESTAMP,
  added_at     TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, skill_id)
);

CREATE INDEX idx_user_skills_user ON user_skills(user_id);
```

### Pin 约束

- `is_pinned = TRUE` 的记录数上限：4 条（应用层校验）
- Pin 顺序由 `added_at` 决定（先 pin 的优先展示）

---

## 四、API 设计

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/skills` | 已改造：返回 pin 的 + 补足 6 个推荐（Chatbox 用） |
| `GET` | `/api/skills/my` | 用户所有已添加的 skill（设置面板用） |
| `GET` | `/api/skills/market` | 技能市场全量列表（含用户是否已添加的状态） |
| `POST` | `/api/skills/{key}/add` | 添加到我的技能 |
| `DELETE` | `/api/skills/{key}/remove` | 从我的技能移除（同时取消 pin） |
| `PATCH` | `/api/skills/{key}/pin` | 切换 pin 状态（body: `{pinned: true/false}`，超过 4 个 pin 返回 400） |

---

## 五、前端 UI

### 5.1 更多面板（改造）

```
更多面板
├── [我的技能] tab（默认）
│   ├── 空状态：「还没有技能，去市场逛逛 →」
│   ├── 已固定（≤4）：带 📌 标记，可拖拽排序
│   └── 其他已添加：列表，可 pin / 移除
└── [技能市场] tab
    ├── 分类筛选（全部 / 按行业）
    ├── skill 卡片 grid（24 个）
    │   └── 已添加的显示「已添加」状态
    └── 点击某 skill → 详情 Modal
```

### 5.2 技能详情 Modal

```
┌──────────────────────────────────────┐
│  [技能名称]              [✕ 关闭]   │
│  标签：行业标签                      │
│                                      │
│  描述                                │
│  ──────────────────────────────────  │
│  需要填写的信息：                     │
│  • 字段1（类型）                     │
│  • 字段2（类型）                     │
│                                      │
│  适用场景：...                       │
│                                      │
│  [添加到我的技能]  /  [已添加 ✓]    │
└──────────────────────────────────────┘
```

### 5.3 Chatbox 卡片视觉区分

- 用户 pin 的 skill：正常样式
- 系统推荐的 skill：右上角显示一个极小的「推荐」角标（可选，不要太显眼）

---

## 六、实现阶段

### Phase A — 核心（本期实现）

- [ ] DB migration：`user_skills` 表 + 索引
- [ ] `POST /api/skills/{key}/add`
- [ ] `DELETE /api/skills/{key}/remove`
- [ ] `PATCH /api/skills/{key}/pin`（含 4 个上限校验）
- [ ] `GET /api/skills/my`
- [ ] `GET /api/skills/market`（含 is_added 状态）
- [ ] 改造 `GET /api/skills`：pin 的 + 补足 6 个推荐
- [ ] 前端：更多面板 → 两 tab（我的技能 + 技能市场）
- [ ] 前端：技能市场 grid + 已添加状态
- [ ] 前端：技能详情 Modal（描述 + 字段预览 + 添加按钮）
- [ ] 前端：我的技能列表（pin/unpin/移除）
- [ ] 前端：Chatbox 6 张卡片按新规则渲染

### Phase B — 体验提升（后续迭代）

- [ ] skill 执行成功后写回 `use_count + 1` / `last_used_at`
- [ ] 推荐逻辑升级：use_count 热度 + 对话上下文实时置换
- [ ] 我的技能支持拖拽排序（调整 pin 顺序）
- [ ] 推荐卡片的「推荐」角标（可选）

---

## 七、关键决策记录

| 决策 | 选择 | 原因 |
|---|---|---|
| Pin 上限 | 4 个 | 留 2 个位置给推荐，保证系统能持续帮用户发现新技能 |
| 推荐不持久化 | 不写入 user_skills | 设置面板保持干净，用户不会困惑 |
| 添加语义 | 加入技能库（非解锁权限）| 所有用户已有全部 24 个技能的使用权 |
| 新用户 fallback | 6 个全推荐 | 避免空状态，开箱即用体验更好 |
