# SKILL_RANKING_DESIGN.md

> Skill 召回与排序算法设计
> 
> 这份文档把"埋点 = 召回信号"的洞察,落地成具体的算法演进路径。
> 
> 核心思想:**Skill 召回 = 工作场景下的 feed 流推荐**,
> 但比短视频推荐**用户行为更理性、信号噪声更小、转化定义更明确**,
> 理论上召回精度上限更高。

---

## 当前实现状态（2026-05-20，Phase 11）

> 本节记录截至今日的架构决策与落地情况，供对照演进路径使用。下方正文保持原样不变。

---

### 两套推荐系统的业务定义

本文原始设计只描述了一套召回系统。实际产品中，Skill/Agent 推荐有**两个完全独立的触发场景**，流水线设计有本质差异：

#### 系统 1：首页空态推荐（Home Screen Recommendation）

**触发时机**：用户新建会话，输入框为空时展示的卡片区

**业务目标**：在用户没有明确意图时，主动发现用户可能需要的 Skill，降低"不知道能干嘛"的流失

**核心特点**：
- 没有实时意图信号，完全依赖 profile + 历史行为
- 需要填满 6 个卡片槽位（必须有结果）
- 同时推荐 Skill 卡片 + Agent 卡片（career/gaokao/ppt/research）
- 用户点击成本低（就是卡片，不打断对话）

**已实现流水线**：
```
Context（profile: industry / role / pain_points）
  → Recall        skill_role_mapping + is_universal，排除已 pin
  → Coarse Rank   每 layer 最多 2 个，强制多样性
  → Fine Rank     profile_match×0.4 + CTR×0.25 + affinity×0.25 + recency×0.1
  → Re-rank       pinned 强插 + cool_down_until 过滤
```

**核心文件**：`backend/services/skill_recommender.py` / `backend/api/recommendations.py`

---

#### 系统 2：对话内意图触发（In-Conversation Intent Trigger）

**触发时机**：用户在对话中发送消息，系统识别出意图后主动弹出 Skill 建议

**业务目标**：在用户意图最明确的时刻精准推荐，CTR 远高于系统 1

**核心特点**：
- 有最强信号：用户刚发的这句话（实时意图）
- 通常只取 top-1（弹出一个 Skill 面板，不能一次弹多个）
- 推错了比不推更差——**必须有置信度门槛**，低于阈值宁可不弹
- 不需要多样性控制，不需要考虑 pin

**当前实现**（粗糙版，待升级）：
```python
# backend/services/skill_registry.py
def find_by_keywords(text: str) -> dict | None:
    # 纯关键词字符串匹配，命中第一个就返回
```

**问题**：关键词匹配漏召回率高（用户换个说法就触发不了）

**目标流水线**（Phase 12，待实现）：
```
用户消息
  → 硬规则快路径    关键词完全匹配 → 直接返回，跳过后续（高置信度保留）
  → Embedding 召回  消息文本 vs skill 描述，余弦相似度 top-N
  → Coarse Rank     profile 匹配粗过滤，剩 m 个
  → Fine Rank       见下方打分公式
  → 置信度门槛      score < 0.65 → 不触发，继续正常对话
  → 输出 top-1
```

---

### 两系统精排维度对比（重要）

| 打分维度 | 系统 1 权重 | 系统 2 权重 | 说明 |
|---------|:----------:|:----------:|------|
| **语义相似度**（消息 embedding vs skill） | ❌ 无此信号 | **0.40** | 系统 2 最核心信号，系统 1 没有 |
| **profile 匹配**（pain_points/role/industry） | 0.40 | 0.20 | 两系统都用；pain_points 权重最高（×3） |
| **质量信号 quality** | ⚠️ 未拆出 | **0.25** | 见下方 quality 公式 |
| **个人 affinity** | 0.25 | 0.15 | `user_skill_affinity.affinity_score` |
| **全局 CTR** | 0.25（含 affinity 内） | ⚠️ 权重降低 | 系统 2 更看重质量而非点击 |
| **recency**（最近 7 天用过） | 0.10 | 可选 | |
| **置信度门槛** | ❌ 不需要（必须填满） | **必须有** | 低于阈值不触发，宁缺毋滥 |

**系统 2 精排公式**（Phase 12 目标）：
```
score = semantic_sim  × 0.40
      + profile_match × 0.20
      + quality       × 0.25   ← 文档 §4 多目标融合的核心
      + affinity      × 0.15

quality = pComplete × 0.5 + pAdopt × 0.4 - pAbandon × 0.3
# pComplete = completed / started
# pAdopt    = (output_copied + output_liked + shared) / completed
# pAbandon  = abandoned / started
```

**为什么系统 2 的 quality 权重比系统 1 更高**：
系统 1 推错了用户直接忽略，成本低。系统 2 是在用户说话时主动打断，推错了直接破坏对话体验。
completion rate 和 adoption rate（复制/点赞/分享）是"这个 Skill 真的有用"最干净的信号。

---

### pain_points 在精排中的位置（系统 1 已实现）

pain_points 是 profile 匹配分的最重要组成，权重高于 role 和 industry：

```python
# skill_recommender.py: _profile_score_norm()
raw = sum(W_PAIN for kw in pain_points if kw.lower() in skill_text)  # W_PAIN=3
if role and role.lower() in text:     raw += W_ROLE      # 2
if industry and industry.lower() in text: raw += W_INDUSTRY  # 1
# 归一化到 0-1，进入 Fine Rank 的 0.40 权重
```

系统 2 复用同一函数，但权重降为 0.20（让位给语义相似度）。

---

### 现阶段所处演进位置

对应本文"阶段 2（100-1000 用户）"入口：
- 系统 1：规则召回 + 个人化打分均已上线，离线聚合任务待实现
- 系统 2：仍在"阶段 1"（关键词规则），Phase 12 升级到 embedding 召回 + 完整精排

| 本文设计 | 实际实现 | 备注 |
|---------|---------|------|
| § 2.5 affinity 公式 | 简化版：DB 触发器粗略写入 | 时间衰减 Phase 11D 补 |
| § 3 阶段 1 规则召回 | ✅ 系统 1 已实现 | |
| § 3 阶段 2 个人化排序 | ✅ 系统 1 部分实现 | 离线聚合待 Phase 11B |
| § 3 阶段 3 实时意图召回 | ⏳ 系统 2 Phase 12 | embedding 召回 |
| § 4 多目标融合 quality | ⏳ 系统 2 Phase 12 | pComplete/pAdopt/pAbandon |
| § 6.1 数据层 | ✅ 已有 | |
| § 6.2 离线聚合任务 | ⏳ Phase 11B | |
| § 6.3 推荐接口 | ✅ `GET /api/recommendations` | |
| § 6.3 信号接口 | ✅ `POST /api/recommendations/events` | |

### 下一步

- **Phase 11B**：cron 任务聚合 `skill_metrics_daily`，拆出 pComplete / pAdopt / pAbandon
- **Phase 11C**：`recommendation_cool_down_until` 自动设置
- **Phase 11D**：对话结束后用信号权重更新 `affinity_score`（§ 2.5 完整公式）
- **Phase 12**：系统 2 升级——embedding 召回 + 完整精排公式 + 置信度门槛

---

## 0. 阅读说明

这份文档不是"完美方案",而是**演进路径**:

```
阶段 1(0-100 用户)→ 规则召回(必备/推荐/可选 + 时间衰减)
阶段 2(100-1000)→ 基础排序模型(逻辑回归 + 个人化特征)
阶段 3(1000-10K)→ 多路召回 + 协同过滤
阶段 4(10K+)→ 双塔模型 / Embedding 召回 / 多目标融合
```

**别提前实现**。先把数据攒住,模型自然会到来。

---

## 1. 为什么 Skill 召回比短视频更简单

| 维度 | 短视频 feed | Skill 召回 |
|------|-----------|-----------|
| 候选池规模 | 千万级 | 几百级(24 个起步,长期 1k) |
| 用户意图明确度 | 模糊(打发时间) | 明确(完成某个任务) |
| 上下文丰富度 | 主要看历史 | 历史 + **当前对话主题** + 行业角色 |
| 转化定义 | 看完 / 点赞(noisy) | 完成 + 复制输出(clean) |
| 实时性要求 | 毫秒级 | 秒级足够 |
| 探索成本 | 看 30 秒 | 用户填表才能体验 ⚠️ |

**关键差异在最后一行**:Skill 的"试错成本"对用户更高,所以**召回精度的重要性大于多样性**。短视频可以"猜你喜欢撒大网",Skill 不行,推错了用户下次就不来了。

---

## 2. 信号体系:7 类信号 + 权重

`001_schema_update.sql` 里的 `skill_signals` 表已经记录了 13 种 signal_type。把它们按**对召回价值**重新分类:

### 2.1 强正向信号(高权重)

| signal_type | 含义 | 召回权重 | 解读 |
|-------------|------|---------|------|
| `output_copied` | 用户复制了输出 | **+1.0** | 最强信号——用户真的拿去用了 |
| `output_liked` | 用户点赞 | **+0.8** | 直接质量反馈 |
| `shared` | 分享给别人 | **+0.9** | 用户认为这个值得传播 |
| `completed` | 流程完整跑完 | **+0.5** | 至少没中途放弃 |

### 2.2 弱正向信号(中权重)

| signal_type | 含义 | 召回权重 | 解读 |
|-------------|------|---------|------|
| `started` | 开始填表 | +0.3 | 有兴趣,但还没真用 |
| `output_edited` | 编辑后才用 | +0.2 | 用了但不够好,需迭代 |
| `clicked` | 点击卡片 | +0.1 | 注意力信号 |

### 2.3 强负向信号(扣分)

| signal_type | 含义 | 召回权重 | 解读 |
|-------------|------|---------|------|
| `output_disliked` | 点踩 | **-1.0** | 直接质量反馈 |
| `abandoned` | 中途放弃 | -0.5 | 流程或体验有问题 |

### 2.4 中性信号(只用于归因)

| signal_type | 含义 | 召回权重 | 备注 |
|-------------|------|---------|------|
| `recommended` | 系统推荐 | 0 | 用于算 CTR 的分母 |
| `impressioned` | 真的渲染到屏幕 | 0 | 用于算 CTR 的分母 |
| `opened` | 打开输入面板 | 0 | 中间状态 |
| `submitted` | 提交了表单 | 0 | 中间状态 |

### 2.5 用户偏好分计算公式

对每个 (user, skill) 二元组,**用户偏好分** `affinity_score`:

```
raw_score = Σ (signal_weight × time_decay(t))
            for each signal in (user, skill, last_90_days)

time_decay(t) = 0.5 ^ (days_ago / 30)   # 30 天半衰

affinity_score = sigmoid(raw_score / 5.0)   # 归一化到 0-1
```

**实现位置**:夜间批处理任务,写入 `user_skill_affinity` 表。

**第一版可以简化**:只用最近 30 天的信号,不做时间衰减,效果损失有限,实现复杂度大幅下降。

---

## 3. 召回:阶段性演进

### 阶段 1:规则召回(MVP,0-100 用户)

**直接用 `skill_role_mapping` 表**:

```sql
-- 用户首页 Top 8 Skill
SELECT s.*
FROM skill_role_mapping m
JOIN industry_skills s ON s.id = m.skill_id
WHERE m.industry = ${user.industry} 
  AND m.role = ${user.role}
  AND s.enabled = TRUE
ORDER BY 
  CASE m.priority 
    WHEN 'essential' THEN 1 
    WHEN 'recommended' THEN 2 
    ELSE 3 
  END,
  m.display_order
LIMIT 8;
```

**优点**:
- 实现简单,无需任何模型
- 冷启动友好——新用户也能拿到合理推荐
- 可解释——行业产品经理能直接 review 推荐结果

**缺点**:
- 完全不个性化,所有"互联网/产品经理"看到的都一样
- 不会随用户行为变化

**何时升级**:当有用户开始反馈"这个 Skill 我用不上"或者"为什么不推荐 X"时,升级到阶段 2。

---

### 阶段 2:个人化排序(100-1000 用户)

**召回不变,排序加入个人偏好**:

```
final_score = 0.4 × base_score        # 来自 mapping 的 priority
            + 0.4 × affinity_score    # 来自 signals 的个人偏好
            + 0.2 × freshness_boost   # 新 Skill 探索奖励
```

**排序逻辑**:

```python
def rank_skills(user, candidates):
    scores = []
    for skill in candidates:
        # 基础分:essential=1.0, recommended=0.7, optional=0.4
        base_score = {
            'essential': 1.0, 
            'recommended': 0.7, 
            'optional': 0.4
        }[get_priority(user, skill)]
        
        # 个人偏好分(从 user_skill_affinity 查)
        affinity = get_affinity_score(user.id, skill.id)
        
        # 探索奖励:新 Skill 或 30 天没推过的 +0.1
        freshness = 0.1 if is_fresh(user, skill) else 0
        
        # 冷却:刚推过的扣分,避免疲劳
        if recently_recommended(user, skill, hours=24):
            cooldown_penalty = -0.3
        else:
            cooldown_penalty = 0
        
        final = (
            0.4 * base_score + 
            0.4 * affinity + 
            0.2 * freshness +
            cooldown_penalty
        )
        scores.append((skill, final))
    
    return sorted(scores, key=lambda x: -x[1])
```

**冷启动策略**:
- 新用户没有 affinity 数据时,affinity = 0.5(中性)
- 前 7 天,affinity 权重从 0 渐变到 0.4(给系统时间积累信号)

**这个阶段最关键的产品决策**:留多少"探索"位置?

我的建议:**8 个位置 = 5 个个人化 + 2 个新 Skill 探索 + 1 个全局热门**。
理由:工作场景容错率低,但完全不探索会让用户错过潜在好 Skill。

---

### 阶段 3:多路召回 + 协同过滤(1000-10000 用户)

到了这个量级,可以做"**和你类似的人在用什么**"的协同过滤。

**多路召回架构**:

```
                    ┌─────────────────┐
                    │  最终排序模型    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐        ┌─────▼─────┐        ┌────▼─────┐
   │ 行业映射  │        │ 协同过滤   │        │ 实时意图  │
   │ 召回 30   │        │ 召回 20    │        │ 召回 10   │
   └──────────┘        └───────────┘        └──────────┘
        │                    │                    │
   skill_role_         user_skill_         conversation
   mapping             affinity            keyword match
```

#### 路径 1:行业映射召回(已有)
继承阶段 1 的逻辑,作为兜底。

#### 路径 2:协同过滤召回(新增)

**核心思路**:找到和当前用户行为相似的其他用户,推荐他们高频使用但当前用户没用过的 Skill。

**实现简化版(ItemCF)**:

```python
# 离线:计算 skill-skill 相似度
def compute_skill_similarity():
    """
    skill_i 和 skill_j 的相似度 = 
        共同用过它们的用户数 / sqrt(用过 i 的人数 × 用过 j 的人数)
    """
    # 用 spark / pandas / 直接 SQL 都行,数据量小
    pass

# 在线:基于用户已用过的 Skill,推荐相似 Skill
def cf_recall(user, top_k=20):
    used_skills = get_user_used_skills(user.id)
    candidates = {}
    for skill in used_skills:
        similar = get_similar_skills(skill, top_k=10)
        for s, sim in similar:
            if s not in used_skills:
                candidates[s] = candidates.get(s, 0) + sim * user.affinity[skill]
    return sorted(candidates.items(), key=lambda x: -x[1])[:top_k]
```

**为什么 ItemCF 优于 UserCF**:
- Skill 数量(几百)<< 用户数量,Skill-Skill 矩阵小得多
- Skill 之间的相似度比用户之间稳定(用户口味会变,Skill 不会)

#### 路径 3:实时意图召回(关键创新)

**这是 Skill 召回相对于短视频的最大优势**——可以利用**当前对话内容**做实时召回。

```python
def realtime_intent_recall(user, current_conversation):
    """
    用户在聊天中,根据当前对话内容判断意图,
    实时弹出对应 Skill。
    """
    # 简单版:关键词匹配 trigger_keywords
    last_message = current_conversation.last_user_message
    matched_skills = []
    for skill in all_skills:
        for keyword in skill.trigger_keywords:
            if keyword in last_message:
                matched_skills.append((skill, 1.0))
    
    # 进阶版:LLM 意图分类
    intent = classify_intent_with_llm(last_message)
    # intent = {"type": "meeting_summary", "confidence": 0.85}
    # → 召回 meeting_notes_pro
    
    return matched_skills
```

**产品形态**:
> 用户:"今天开会聊了一堆,我都记不住了..."
> Buddy:"要不要用【智能会议纪要】帮你整理?把你能记起的要点告诉我就行 → [一键打开]"

**这种召回 CTR 远高于首页推荐**,因为意图明确。

---

### 阶段 4:Embedding + 双塔(10K+ 用户)

到这个阶段,可以训练真正的深度学习模型。但**别提前做**。

简要架构:

```
用户塔:[行业 onehot, 角色 onehot, 历史 affinity 向量, 当前 session 特征]
        → MLP → user_embedding (128 维)

Skill 塔:[skill 特征, 文本 embedding, 历史 CTR/CVR]
        → MLP → skill_embedding (128 维)

排序分 = cosine(user_embedding, skill_embedding)
```

**为什么这个阶段才上**:深度模型需要大量训练数据,样本不够时不如规则。

---

## 4. 多目标优化:不要只优化 CTR

这是从抖音算法演进中学到的关键教训。

### 4.1 单目标的陷阱

**只优化 CTR**(点击率)→ 标题党 Skill 横行,但用户用完发现没用,长期留存下滑。

**只优化 CVR**(完成率)→ 倾向推荐用户已用过的、轻车熟路的,新 Skill 没人用,生态萎缩。

**只优化"点赞率"**→ 用户都喜欢甜的,但工作工具需要的是有用,不是讨好。

### 4.2 多目标融合公式

```
ranking_score = w1 × pCTR        # 点击率预估
              + w2 × pStart      # 开始使用率
              + w3 × pComplete   # 完成率
              + w4 × pAdopt      # 采纳率(复制/分享)
              - w5 × pAbandon    # 放弃率惩罚
```

**权重建议**(第一版):
```
w1 = 0.2   # CTR(轻)
w2 = 0.2   # 开始率
w3 = 0.3   # 完成率
w4 = 0.4   # 采纳率(最重要)
w5 = 0.3   # 放弃率惩罚
```

**关键洞察**:**采纳率权重最高**,因为这是"用户真的觉得有用"的最干净信号。

### 4.3 长期价值监控

每周看一次这些指标,作为算法迭代的北极星:

- **D7 留存**:7 天后还在用 Skill 的用户比例
- **Skill 多样性**:每个用户平均使用过的 Skill 数量
- **Skill 健康度**:30 个 Skill 中有多少个有人持续在用(你提到 3 个月留 8 个,就是这个)
- **首次惊喜率**:用户第一次用某 Skill 时的采纳率

---

## 5. 冷启动:三类冷启动的应对

### 5.1 新用户冷启动

**问题**:新用户没有任何行为数据。

**方案**:
1. **onboarding 收集行业+角色** → 直接走 `skill_role_mapping` 规则召回
2. **首日推荐 essential Skill** → 让用户快速感受到价值
3. **首周收集偏好** → 用户每用一次,affinity 快速更新
4. **第 8 天起进入个人化召回**

**关键产品决策**:**新用户首页只展示 6 个 Skill,不要 12 个**。
理由:选择悖论。新用户被 12 个选项淹没反而无所适从,6 个更容易聚焦。

### 5.2 新 Skill 冷启动

**问题**:新发布的 Skill 没数据,模型会一直不推它。

**方案**:**强制曝光池**。
- 每个新 Skill 上线后,前 7 天保证至少 100 次曝光
- 曝光对象选择:行业-角色 mapping 匹配的用户
- 7 天后,数据足够就转入正常算法

```python
def boost_new_skills(candidates, user):
    new_skills = [s for s in all_skills 
                  if s.created_at > now() - 7_days
                  and s.matches_role(user)]
    
    for skill in new_skills:
        if skill.total_impressions < 100:
            # 强制塞入推荐位
            candidates.insert(2, skill)  # 第 3 位
    return candidates
```

### 5.3 新行业-角色冷启动

**问题**:你上线了一个新行业(比如"建筑业"),`skill_role_mapping` 还没填。

**方案**:**用相似角色迁移**。
```python
def find_similar_role_skills(industry, role):
    # 找语义相似的已有角色
    similar = find_semantically_similar(industry, role)
    # 比如新角色"建筑设计师"→ 找到"互联网/产品经理"
    # 借用对方的 mapping 作为初始模板
    return get_skills_for(similar.industry, similar.role)
```

---

## 6. 工程实现:第一版(Stage 5)交付清单

**不要一开始就做全套**。第一版只做这些:

### 6.1 数据层（已完成）
- ✅ `skill_signals` 表（含 ORM：`SkillSignalModel`）
- ✅ `user_skill_affinity` 表（含 ORM：`UserSkillAffinityModel`）
- ✅ `skill_metrics_daily` 表
- ✅ 触发器自动从 `skill_executions` 写 signals

### 6.2 离线任务（每天跑一次，cron）

- ⏳ **Phase 11B 待实现**

**Task 1：计算 user_skill_affinity**（当前由触发器粗略更新，缺时间衰减）
```python
# 每天凌晨 3 点跑
def update_affinity_scores():
    for user in active_users(last_30_days):
        for skill in industry_skills:
            score = calculate_affinity(user.id, skill.id, days=30)
            upsert_affinity(user.id, skill.id, score)
```

**Task 2：聚合 skill_metrics_daily**（当前 Fine Rank 实时查 skill_signals，量大时改为查此表）
```python
def aggregate_daily_metrics():
    # 从 skill_signals 聚合到 skill_metrics_daily
    # 计算 CTR / start_rate / completion_rate / satisfaction_rate
    pass
```

### 6.3 在线接口（已完成，Phase 11）

**Endpoint 1**：`GET /api/recommendations`（原设计为 `/api/skills/recommend?count=8`）
返回 `{pinned, agents, skills}`，走完整 5 阶段流水线。

**Endpoint 2**：`POST /api/recommendations/events`（原设计为 `/api/skills/signal`）
前端批量上报 impression / click 等事件，写入 `skill_signals`。

```typescript
// 前端实际调用（EmptyStateCards.tsx）
postSkillEvents([{
  item_type: "skill",
  item_key: "weekly_report",
  signal_type: "impressioned",
  context: { position: 0, bucket: "recommended" },
  session_id: sessionId,
}]);
```

### 6.4 监控大盘(必备)

每天看一次的核心指标:

| 指标 | 含义 | 健康阈值 |
|------|------|---------|
| 推荐 → 点击 CTR | clicked / impressioned | > 8% 优秀,< 3% 危险 |
| 点击 → 完成转化 | completed / clicked | > 40% 优秀,< 15% 危险 |
| 用户活跃 Skill 数 | 每用户 7 天内用过的 Skill 数 | > 2 健康 |
| 30 天孤儿 Skill 数 | 30 天没人用的 Skill | < 5 健康 |

**当孤儿 Skill > 10 个时,就该砍 Skill 或重写 prompt 了**(你说的"3 个月留 8 个"逻辑)。

---

## 7. 反作弊与异常检测

工作场景比短视频反作弊压力小,但仍需注意:

### 7.1 防御点踩刷量
- 同一用户对同一 Skill 30 天内最多记录 1 次 disliked
- 大量短时间点击不计入信号(超过 10 次/分钟视为异常)

### 7.2 防御开发自测污染
- 内部账号(@yourcompany.com)的 signal 默认不进入算法训练数据
- 用专门的 flag 字段区分:`signal.user_type = 'internal'`

---

## 8. 这套系统的"飞轮效应"

```
更多用户 → 更多信号 → 更准召回 → 用户更爽
   ↑                                  ↓
   └──── 用户口碑传播,带新用户 ←────┘

同时:
更多用户 → 更多 Skill 使用数据 → 发现哪些 Skill 该砍/该改
        → Skill 质量提升 → 用户更爽
```

**这就是你的"Agent 版字节"愿景的算法机制**——
不是大爆款,而是**通过无数微小的正向反馈循环,让产品对每个用户都越来越精准**。

---

## 9. 容易掉进的坑(开始写代码前先看一遍)

### 坑 1:过早上模型
**症状**:Stage 5 刚开始就想做 LightGBM 排序模型。
**后果**:训练样本不够,模型效果不如规则,白白浪费 2 周。
**正解**:**100 用户前用规则,1000 用户前用 LR/GBDT,10K+ 才考虑深度模型**。

### 坑 2:信号定义不严谨
**症状**:`completed` 信号同时包含"用户主动完成"和"系统超时关闭"。
**后果**:正负样本混淆,模型学不到东西。
**正解**:**signal_type 必须有明确语义,不能模糊**。`skill_signals.context` 字段记录详细原因。

### 坑 3:CTR 至上的诱惑
**症状**:发现某 Skill 点击率高,就疯狂推。
**后果**:用户点了发现没用,长期留存下滑。
**正解**:**永远用多目标融合,CTR 是路径不是目的**。

### 坑 4:不做 holdout
**症状**:全量上线新算法,没有对照组。
**后果**:效果好坏都说不清,根本无法迭代。
**正解**:**每次算法迭代都开 A/B 实验**。`industry_skills.experiment_group` 字段就是为这准备的。

### 坑 5:Skill 永不下线
**症状**:24 个 Skill 一直在系统里,不管有没有人用。
**后果**:用户搜索/浏览体验变差,后台维护成本飙升。
**正解**:**90 天没人用的 Skill 直接 disabled**,需要主动 reactive 才能再上。

---

## 10. 给未来的自己

如果你 3 个月后回头看这份文档,问"该升到阶段 N 了吗",回答这几个问题:

1. **当前 DAU 多少?** 100/1000/10K?
2. **每日 signal 量多少?** 1k/10k/100k?
3. **是否能跑得动一次完整离线任务?** (考虑数据规模)
4. **业务上,有没有用户在抱怨推荐不准?**

**只有当数据量 + 业务需求 + 工程余力都到位,才考虑升级**。
**别为了上模型而上模型**。

---

**完。**

这份设计文档,本质上是把你那句"埋点是召回信号"展开成了一套可执行的工程方案。
按 Stage 5/6/7 推进,3 个月内可以把数据基础打牢,
等到那时候,你心里就会有底气说出:**这个产品不只是 Skill 工具,是一个能学习的工作搭子**。
