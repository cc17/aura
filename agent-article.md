# 我是怎么一步步把 Agent 做到工业级的

*一个真实项目的拆解*

---

## 一、大多数人搭的 Agent，其实是个玩具

把用户输入丢给 LLM，再把输出打印出来——这叫 Agent 吗？

勉强算。但一旦到生产环境，你会发现它脆得很：

- 回答质量忽高忽低，没有自我校验
- 每次都要调用 LLM，成本高、延迟大
- 工具调用多了，用户盯着空白屏不知道发生了什么
- 多用户同时使用时，请求会"串"——A 的回答跑到 B 那里去了

这篇文章讲的，是我在做 Aura（一个多技能 AI 助手）时，把这些问题一个个解决掉的思路。

---

## 二、第一个决策：多智能体 vs 单一 Agent

很多人上来就把所有技能塞进一个大 prompt，让一个 LLM 啥都干。

问题显而易见：prompt 越来越长，模型注意力分散，专业能力被平均化。

我的选择是**多智能体 + Supervisor 路由**：

```
用户输入
    ↓
Supervisor（意图识别）
    ↓ 路由
┌──────────────────────────────────────┐
│  General  Resume  PPT  Research  高考 │
└──────────────────────────────────────┘
    ↓
Reflection（质量评估）
    ↓ 通过 → 输出给用户
    ↓ 不通过 → 回到对应 Worker 重试（最多 3 次）
```

每个 Worker 是独立的：有自己的 system prompt、自己的工具集、自己的专注领域。Supervisor 只做一件事——判断这个问题该谁接。

这个拓扑用 LangGraph 的 `StateGraph` 实现，几十行就能建出来，但架构思路是最重要的。

---

## 三、意图识别：两阶段，先快后准

Supervisor 路由是整个系统的入口，它的速度和准确性直接影响用户体验。

我用了**两阶段策略**：

**第一阶段：关键词快速通道（零 LLM 成本）**

```python
GAOKAO_PATTERNS = [r"高考", r"志愿填报", r"录取分数线", r"选专业"]
PPT_PATTERNS    = [r"做.{0,6}ppt", r"制作.{0,6}幻灯片", r"演示文稿"]
```

对于明确包含领域关键词的请求，直接路由，不调 LLM。实测命中率约 60-70%，这部分请求几乎零延迟。

**第二阶段：LLM 分类（带 KV 缓存）**

剩下的模糊意图，才交给 LLM 判断。Supervisor prompt 极度精简：

> 你是路由器。只能回复一个词：agent 名称。

不让模型解释、不让模型思考，就要一个词。这样既快，分类结果又稳定，方便后续 parse。

---

## 四、KV 缓存：省钱的正确姿势

LLM 调用最贵的是什么？重复问题重复付费。

Supervisor 的路由判断、Reflection 的质量评分，同样的问题模型给出的结果是稳定的。我实现了一个应用层 KV 缓存：

```python
key = sha256(model_name + json(messages))
if key in cache:
    return cache[key]          # 直接返回，不调 LLM
response = await llm.ainvoke(messages)
cache.set(key, response, ttl=300)  # 缓存 5 分钟
```

Supervisor 缓存 5 分钟，Reflection 缓存 10 分钟。Worker 的流式输出不缓存——因为每次对话内容都不同，缓存没有意义。

这个设计让整体 LLM 调用次数在测试中降低了约 40%。

---

## 五、Reflection Loop：让 Agent 自我审查

这是整个系统里我最在意的设计。

传统 Agent 的问题：生成即输出，质量完全依赖第一次生成。

我加了一个 Reflection 节点，每次 Worker 回答完，先过这道门：

```python
REFLECTION_PROMPT = """
评分标准（各 0-10 分）：
- 完整性：是否完整回答了用户问题？
- 质量：结构清晰、具体可操作？
- 工具使用：该用工具时用了吗？

回复格式（严格）：
SCORE:<整数>
CRITIQUE:<一句话改进建议，或 none>
"""
```

分数 ≥ 7，放行；否则把 critique 注入回 Worker，让它重来。最多循环 3 次，防止无限重试。

**关键细节**：反思时取的是**最后一条**人类消息作为"原始问题"，而不是第一条——因为历史对话里第一条消息可能是上一轮的内容，评错对象会导致乱判断。

```python
for m in reversed(messages):      # 倒序找，拿最新的
    if m.type == "human":
        original_question = m.content
        break
```

这个 bug 我在实际运行中踩过，Reflection 在评估"上海大学"的问题时，却把"特朗普"那轮的回答给判了——就是因为正序取消息取错了。

---

## 六、输出门控：中间过程不该污染最终答案

这是个很容易被忽视的设计点。

Loop 最多 3 次，但用户只应该看到**最终那次**的回答。中间被 Reflection 否掉的草稿，不应该出现在答案区域。

实现方式：**先缓冲，后冲洗**。

```python
_iter_buffer = []   # 当前迭代的所有事件

# Worker 输出的文字/工具调用 → 全部放进 buffer，不发给前端
_iter_buffer.append(StreamEvent(TEXT_DELTA, text=chunk))

# Reflection 通过时 → 一次性 flush
if reflection_done:
    for event in _iter_buffer:
        yield event          # 现在才真正发送给用户
        if event.type == TEXT_DELTA:
            await asyncio.sleep(0.012)  # 打字效果

# Reflection 否决时 → buffer 内容转成"思考"，不发给用户
else:
    draft = "".join(e.data["text"] for e in buffer if e.type == TEXT_DELTA)
    yield thinking_event(f"📝 第{loop}轮草稿：{draft[:300]}…")
    yield thinking_event(f"💭 评估：{critique}")
    _iter_buffer = []   # 清空，重新开始
```

`asyncio.sleep(0.012)` 是个小技巧：Reflection 通过后，所有 token 是同时 flush 的，没有流式效果。加 12ms 的人工延迟，就还原出了打字机效果——约 83 token/秒，和真实流式体验一致。

---

## 七、Thinking Panel：让用户看见 Agent 在想什么

对工具调用和中间过程，有两种处理方式：

1. 隐藏，让界面保持干净
2. 展示，让用户感知进度

我选了后者，但做了分层：**工具调用即时展示**（不等 Reflection），**中间草稿折叠展示**。

```python
# 工具调用 → 立即 yield，不进 buffer
yield thinking_event("🔍 搜索网络: 上海大学录取分数线")

# 同时也放进 buffer（最终 flush 时带上结构化数据）
_iter_buffer.append(StreamEvent(TOOL_CALL, name=..., arguments=...))
```

前端的 Thinking Panel 是个可折叠的面板，默认收起，用户想看就展开。这样既不干扰主流程，又保留了完整的过程透明度。

这个设计来自 Reflexion 论文的思路——失败的尝试本身就是有价值的信息，不应该被静默丢弃。

---

## 八、竞态条件：最容易被忽视的生产问题

用户发了 Query1，LLM 回了一半，用户按了停止，然后发了 Query2，Query2 结束后——Query1 的结果突然出现了，追加在了 Query2 后面。

这是 SSE 长连接下的经典竞态问题，两层都要修。

**后端**：区分"正常完成"和"客户端中断"

```python
stream_completed = False
try:
    async for event in agent.run(...):
        if event.event == DONE:
            stream_completed = True
        yield event
except asyncio.CancelledError:
    return  # 客户端断开 → 直接返回，不存库

if not stream_completed:
    return  # 非正常完成 → 也不存库
```

**前端**：每次新请求分配一个"代次号"，回调里检查自己是否已经过期

```typescript
const myGeneration = ++generationRef.current;
const isCurrentGen = () => generationRef.current === myGeneration;

// 所有 SSE 回调的第一行
if (!isCurrentGen()) return;  // 过期回调直接丢弃
```

停止时也要递增代次号，让所有在途回调立即失效：

```typescript
const stopStreaming = () => {
  generationRef.current++;   // 关键：先让回调失效
  controller.abort();        // 再断连接
};
```

---

## 九、Memory：让 Agent 记住用户

对话历史不是无限堆积的。我做了三层 Memory 设计：

1. **Pin 机制**：第一条消息和带附件的消息永久固定，不参与压缩
2. **自动摘要**：对话超过阈值时，中间段落替换成摘要（LLM 生成），减少 context 长度
3. **事实提取**：后台异步从对话里提取用户偏好、关键信息，存成结构化 facts，未来优先注入 context

这三层结合，让 Agent 在保持长期记忆的同时，不会把 context window 撑爆。

---

## 十、工具设计原则

每个工具都是独立的 Python 函数，包含三个要素：

1. **清晰的描述**（给 LLM 看，决定什么时候调用）
2. **带缓存**（搜索结果缓存 30 分钟，避免重复请求同一 query）
3. **有上限**（URL scraper 截断到 4000 字，防止超长内容撑爆 context）

```python
@tool
def web_search(query: str, num_results: int = 5) -> str:
    """搜索互联网获取最新信息。适合需要实时数据的问题。"""
    cached = search_cache.get(query)
    if cached:
        return cached
    result = _call_serper_api(query, num_results)
    search_cache.set(query, result, ttl=1800)
    return result
```

工具描述的质量直接影响 Agent 的工具选择准确性——描述越精准，幻觉越少。

---

## 总结：工业级 Agent 的核心思维

| 问题 | 方案 |
|------|------|
| 单 Agent 能力分散 | 多 Agent + Supervisor 路由 |
| 每次调 LLM 成本高 | 应用层 KV 缓存 |
| 输出质量不稳定 | Reflection Loop（最多 3 次） |
| 中间过程污染输出 | Buffer-Flush 门控 |
| 长对话 context 爆炸 | 三层 Memory（Pin + 摘要 + Facts） |
| 用户感知不到进度 | Thinking Panel + 即时工具通知 |
| 多请求竞态串结果 | 代次号 + CancelledError 处理 |
| 没有打字效果 | Flush 时加 12ms token 间隔 |

这些不是"最优解"，是在实际开发中一个 bug 一个 bug 踩出来的选择。Agent 开发和普通后端开发的最大区别是：**它的 failure mode 是概率性的，不是确定性的**，所以每一层的防御设计都很重要。

---

*代码实现基于 LangGraph + FastAPI + React，完整项目结构欢迎交流。*
