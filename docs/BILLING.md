# Aura 计费系统设计文档

> 状态：设计已确认，待实现（阶段 A + B 优先）

---

## 一、三档定价

| | Free | Pro | Max |
|---|---|---|---|
| **价格** | ¥0 | ¥39 / 月 | ¥99 / 月 |
| **AI 回复次数** | 20 次 / 天 | 1000 次 / 月 | 无限制 |
| **额度重置** | 每自然日 00:00 | 每自然月 1 日 | — |
| **Skill 执行** | 计入（×1） | 计入（×1） | 无限制 |
| **可用模型** | 标准（Doubao） | 标准 + 高级 | 全部含最新 |
| **记忆功能** | ✓ | ✓ | ✓ |
| **历史对话** | 仅显示近 30 天 | 永久 | 永久 |
| **技能库** | 全部 24 个 | 全部 | 全部 |

**计量规则**：
- 每条 AI 成功回复（含 Skill 执行）消耗 1 次额度
- 用户中途 Stop、请求出错/失败 — 不计
- Free 用户每天独立计算，Pro/Max 按整月累计

---

## 二、数据库设计

### 新表：`user_quotas`

```sql
CREATE TABLE user_quotas (
  id              BIGSERIAL PRIMARY KEY,
  user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  plan            VARCHAR(20) NOT NULL DEFAULT 'free',
  -- 'free' | 'pro' | 'max'

  -- 当前计费周期的用量
  usage_count     INT NOT NULL DEFAULT 0,

  -- 周期边界
  period_start    TIMESTAMP NOT NULL DEFAULT NOW(),
  -- Free: 当日 00:00；Pro/Max: 当月 1 日 00:00

  period_end      TIMESTAMP NOT NULL,
  -- Free: 当日 23:59:59；Pro/Max: 下月 1 日 00:00

  -- 付费用户的套餐到期时间（NULL = 永久免费）
  plan_expires_at TIMESTAMP,

  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id)
);
```

### 额度限制常量（后端 config）

```python
QUOTA_LIMITS = {
    "free": 20,    # 次/天
    "pro": 1000,   # 次/月
    "max": -1,     # 无限制
}
```

---

## 三、后端逻辑

### 3.1 quota 检查中间件

在 `POST /api/chat` 和 `POST /api/skills/:key/execute` 请求进入业务逻辑前：

```
1. 查询 user_quotas WHERE user_id = current_user.id
2. 如果不存在 → 创建 Free 记录（新用户首次触发）
3. 检查 period_end 是否已过 → 若已过，重置 usage_count = 0，更新 period_start/period_end
4. 如果 plan = 'max' → 直接放行
5. 如果 usage_count >= quota_limit → 返回 402，body:
   {
     "code": "quota_exceeded",
     "plan": "free",
     "usage_count": 20,
     "quota_limit": 20,
     "reset_at": "2026-05-17T00:00:00+08:00"
   }
6. 放行，业务完成后 usage_count += 1
```

### 3.2 新增接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/quota` | 返回当前用量、限额、计划、重置时间 |
| `GET` | `/api/pricing` | 返回三档价格配置（静态，供前端定价页使用） |
| `POST` | `/api/quota/upgrade` | （阶段 C）付费成功后由 Webhook 调用，升级 plan |

### 3.3 历史对话过滤

Free 用户调用 `GET /api/conversations` 时，查询加条件：

```python
if user_plan == "free":
    query = query.where(
        Conversation.created_at > datetime.now() - timedelta(days=30)
    )
```

- **不删除数据**，升级后自动解锁全部历史
- Pro/Max 用户无此过滤

---

## 四、前端 UX 逻辑

### 4.1 剩余次数提示（输入框上方，仅 Free 用户）

| 剩余次数 | 展示 |
|---|---|
| > 5 次 | 不提示 |
| ≤ 5 次 | 输入框上方出现灰色小字："今日剩余 N 次，Pro 可升级至 1000 次/月 →" |
| = 0 次 | 输入框被替换为升级 Banner |

### 4.2 升级 Banner（替换输入框）

```
╔──────────────────────────────────────────────────────────╗
│  🔒  今日免费额度已用完（20/20）                           │
│  明日 00:00 自动重置，或升级 Pro 享 1000 次/月             │
│                                                          │
│  [升级 Pro  ¥39/月]        [了解 Max  ¥99/月]            │
╚──────────────────────────────────────────────────────────╝
```

- 点击升级按钮 → 打开报价页 Modal
- 发送请求后端返回 402 时也触发此 Banner（兜底）

### 4.3 报价页 Modal（PricingModal）

三栏卡片布局，Pro 列高亮"推荐"标签：

```
┌──────────┬────────────────┬──────────┐
│  Free    │   Pro ⭐推荐   │  Max     │
│  ¥0      │   ¥39/月       │  ¥99/月  │
├──────────┼────────────────┼──────────┤
│ 20次/天  │ 1000次/月      │ 无限制   │
│ 30天历史 │ 永久历史       │ 永久历史 │
│ 标准模型 │ 高级模型       │ 全部模型 │
│ 全部技能 │ 全部技能       │ 全部技能 │
├──────────┼────────────────┼──────────┤
│ 当前计划 │ [立即升级]     │ [升级]   │
└──────────┴────────────────┴──────────┘
```

MVP 阶段：点击"立即升级"显示微信二维码 / 联系客服入口。  
阶段 C：接入支付宝 / 微信支付，自动升级 plan。

### 4.4 用户菜单显示档位

用户菜单底部显示当前计划标签：

```
┌─────────────────────┐
│ 我的档案            │
│ ─────────────────── │
│ 退出登录            │
│ ─────────────────── │
│ 🟢 Free 计划  升级→ │
└─────────────────────┘
```

---

## 五、实现阶段

### 阶段 A — 核心计费（后端 + 基础前端提示）

- [ ] DB: 创建 `user_quotas` 表（SQL migration `003_billing.sql`）
- [ ] 新用户注册时自动创建 Free quota 记录
- [ ] quota 检查 + 自动重置逻辑（独立 service `quota_service.py`）
- [ ] `POST /chat` 和 `POST /skills/:key/execute` 接入 quota 检查
- [ ] `GET /api/quota` 接口
- [ ] 前端：登录后加载 quota 信息（存入全局状态）
- [ ] 前端：≤5 次时输入框上方灰色提示
- [ ] 前端：0 次时替换为升级 Banner（硬编码文案，暂无跳转）

### 阶段 B — 报价页 + 用户菜单档位

- [ ] `GET /api/pricing` 接口（静态配置返回）
- [ ] `PricingModal` 组件（三栏对比 + 扫码/联系客服）
- [ ] Banner 按钮接入 PricingModal
- [ ] 用户菜单底部显示当前计划 + "升级"入口
- [ ] 历史对话 30 天过滤（Free 用户）

### 阶段 C — 真实支付（独立迭代，暂不排期）

- [ ] 支付宝 / 微信支付接入
- [ ] 支付 Webhook → `POST /api/quota/upgrade`
- [ ] plan 升级、到期续费、降级处理
- [ ] 发票 / 收据邮件

---

## 六、关键决策记录

| 决策 | 选择 | 原因 |
|---|---|---|
| 计量单位 | AI 回复次数（非 Token） | 用户心智最清晰 |
| Free 重置粒度 | 自然日 | 比月度更友好，每天都有机会体验 |
| 历史对话限制实现 | 查询时过滤，不删数据 | 实现简单；升级后自动解锁，是升级激励 |
| MVP 支付方式 | 扫码/联系客服 | 避免过早投入支付开发，先验证付费意愿 |
| Skill 计费 | 等同普通对话（×1） | 简单统一，用户不需要记两套规则 |
