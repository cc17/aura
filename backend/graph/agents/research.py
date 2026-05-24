"""Research agent — Python-controlled 5-stage pipeline.

Replaces the open-ended ReAct loop, which breaks on Doubao models that return
an empty AIMessage after processing many tool results.

Pipeline:
  0. Topic detection   — Python regex, no LLM
  1. Query generation  — string templates, no LLM
  2. Web searches      — parallel, LangChain tool wrappers (emits thinking events)
  3. URL scraping      — parallel, LangChain tool wrappers (emits thinking events)
  4. Synthesis         — 1 LLM call, no tools bound, tokens stream to user
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool

from backend.graph.state import AuraState
from backend.llm.langchain_bridge import create_chat_model
from backend.tools.adapter import aura_tool_to_langchain
from backend.tools.registry import registry

logger = logging.getLogger(__name__)

# ─── Stage 0: Topic detection (pure Python) ──────────────────────────────────

_VAGUE = frozenset(["话题", "内容", "什么", "东西", "课题", "任务", "一些", "某个话题"])

_STRIP_PREFIX = re.compile(
    r"^(?:帮我?|请你?|你能?|能不能|可以|麻烦你?|能给我?|我想要?|我要|给我|帮忙)?\s*"
    r"(?:调研|研究|分析|调查|搜索|查找|查一查|了解|做个?|写个?|做一个?|写一个?|出个?|整理个?)?\s*"
    r"(?:一?下|一?个|一些|某个|一份)?\s*"
    r"(?:调研报告|综合报告|研究报告|调研|研究|分析|报告|综述)?",
    re.IGNORECASE,
)


def _topic_missing(msg: str) -> bool:
    remaining = _STRIP_PREFIX.sub("", msg.strip(), count=1).strip()
    remaining = remaining.rstrip("吧啊呢哦呀？?！!")
    return len(remaining) < 2 or remaining in _VAGUE


# ─── Stage 1: Query generation (templates, no LLM) ───────────────────────────

def _make_queries(topic: str) -> list[str]:
    return [
        topic,
        f"{topic} 最新进展 现状",
        f"{topic} 市场分析 政策 趋势",
    ]


# ─── URL extraction helper ────────────────────────────────────────────────────

_URL_RE = re.compile(r"URL:\s*(https?://[^\s\)]+)")


def _extract_urls(results: list[str], max_urls: int = 3) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for r in results:
        for url in _URL_RE.findall(r):
            url = url.rstrip(".,;)")
            if url not in seen:
                seen.add(url)
                urls.append(url)
            if len(urls) >= max_urls:
                return urls
    return urls


# ─── Synthesis prompt ─────────────────────────────────────────────────────────

_SYNTHESIS_SYS = """\
你是一位资深行业研究分析师，擅长产出结构严谨、数据支撑、观点鲜明的研究报告。
用户给你一个主题，你产出一份专业报告。直接输出报告正文，不要说"接下来我将…"之类的过渡语。

【硬性规则 — 决定专业感的关键】
1. 标题必须带观点，不能是中性描述
   ✓ "AI重塑K12：从工具辅助到范式变革"
   ✗ "AI在K12中的影响"
2. 每个数据/论断后必须标注来源依据
   - 有公开数据 → 标注来源（如搜索结果中的URL或机构名）
   - 无公开数据 → 标注"基于公开信息推算"或"行业访谈估计"
   - 绝不编造精确数字伪装权威
3. 涉及数据对比的地方用 Markdown 表格，表格标题是结论句
   ✓ "渗透率三年翻倍，K12进入AI普及拐点"
   ✗ "K12 AI渗透率数据"
4. 每章结尾必须有"> 小结：…"一句话
5. 全文围绕一个核心判断展开，所有章节都在论证它

【固定结构 — 严格遵守】

# [带观点的标题]
> 副标题 | {今日日期} | Aura Research 出品

## 核心摘要
- **核心判断**：[一句话，鲜明有争议]
- **关键发现**：[3条，每条带一个数据点或来源]
- **核心建议**：[1条行动建议]

## 一、现状与背景
[市场规模/现象规模 + 发展阶段判断，引用搜索数据]
[用渗透率曲线或发展阶段模型描述所处位置]
> 小结：...

## 二、核心影响分析（主体）
按 3-4 个维度展开（如：学生／教师／家长／机构）
每维度：现象 → 数据 → 案例 → 判断
> 小结：...

## 三、关键玩家与案例
[谁在做、做得如何，用 Markdown 表格对比主要玩家]
> 小结：...

## 四、趋势与展望
[3个趋势预判，每个：依据 + 时间线 + 影响]
> 小结：...

## 结论与建议
[回扣核心判断 + 给不同角色的行动建议（投资者／从业者／用户）]

---
*数据说明：本报告部分数据基于搜索结果整理与推算，仅供参考*

【输出要求】
- 全文 Markdown，标题层级清晰
- 全文 2000-4000 字
- 宁可观点鲜明有争议，不要四平八稳无记忆点
- 若搜索结果质量差，坦诚注明并补充知识库背景（标注"来自知识库"）\
"""

_FOLLOWUP_SYS = """\
你是 Aura 的调研专家。请基于对话历史中的调研报告，简洁回答用户的追问（中文，不超过500字）。
直接聚焦新问题，不重复已有内容。\
"""


# ─── Main node factory ────────────────────────────────────────────────────────

def create_research_agent(model: str | None = None):
    llm = create_chat_model(model)

    # Build tool wrappers once (tools registered before graph is built)
    _search_lc: StructuredTool | None = None
    _scrape_lc: StructuredTool | None = None
    _t = registry.get("web_search")
    if _t:
        _search_lc = aura_tool_to_langchain(_t)
    _t = registry.get("url_scraper")
    if _t:
        _scrape_lc = aura_tool_to_langchain(_t)

    async def _search(query: str) -> str:
        if not _search_lc:
            return "Error: web_search unavailable"
        try:
            return str(await _search_lc.ainvoke(
                {"query": query, "num_results": 8, "language": "zh-cn"}
            ))
        except Exception as exc:
            logger.warning("web_search failed for %r: %s", query[:60], exc)
            return f"Search failed: {exc}"

    async def _scrape(url: str) -> str:
        if not _scrape_lc:
            return "Error: url_scraper unavailable"
        try:
            return str(await asyncio.wait_for(_scrape_lc.ainvoke({"url": url}), timeout=15))
        except Exception as exc:
            logger.warning("url_scraper failed for %r: %s", url[:80], exc)
            return f"Error reading {url}: {exc}"

    async def _synthesize(topic: str, searches: list[str], pages: list[str]) -> str:
        parts = [f"**调研话题**：{topic}\n"]
        for i, sr in enumerate(searches, 1):
            if not sr.startswith(("Error", "Search failed")):
                parts.append(f"---\n**搜索结果 {i}**\n{sr[:2000]}")
        for pc in pages:
            if isinstance(pc, str) and len(pc) > 80 and not pc.startswith("Error"):
                parts.append(f"---\n**网页内容**\n{pc[:3000]}")

        context = "\n\n".join(parts)
        try:
            resp = await llm.ainvoke([
                SystemMessage(content=_SYNTHESIS_SYS),
                HumanMessage(content=context),
            ])
            content = resp.content if isinstance(resp.content, str) else ""
            if content.strip():
                return content
        except Exception:
            logger.exception("Research synthesis LLM call failed")

        # Fallback: return raw search snippets with apology
        fallback = [f"### 调研报告：{topic}\n\n⚠️ 报告自动生成失败，以下为原始搜索结果供参考：\n"]
        for sr in searches:
            if not sr.startswith(("Error", "Search failed")):
                fallback.append(sr[:1200])
        return "\n\n".join(fallback)

    async def node(state: AuraState) -> dict[str, Any]:
        messages = list(state.get("messages", []))

        # Extract last user message
        user_msg = ""
        for m in reversed(messages):
            if hasattr(m, "type") and m.type == "human":
                user_msg = m.content if isinstance(m.content, str) else ""
                break

        # Follow-up detection: only if a prior message IS a research report (not just any long reply)
        _research_markers = ("调研报告", "执行摘要", "Research Report", "**主要发现**")
        prior_ai = [
            m for m in messages
            if hasattr(m, "type") and m.type == "ai"
            and any(marker in (m.content or "") for marker in _research_markers)
        ]
        if prior_ai:
            try:
                resp = await llm.ainvoke([
                    SystemMessage(content=_FOLLOWUP_SYS),
                    *messages,
                ])
                content = resp.content if isinstance(resp.content, str) else "抱歉，无法回答这个问题。"
            except Exception as exc:
                logger.exception("Follow-up answer failed")
                content = f"抱歉，回答追问时出现问题：{exc}"
            return {
                "messages": [AIMessage(content=content)],
                "active_agent": "research_agent",
                "pending_agent": "",
                "critique": "",
            }

        # Stage 0: topic check — ask user for topic, lock pending_agent
        if _topic_missing(user_msg):
            return {
                "messages": [AIMessage(content=(
                    "请告诉我你想调研的具体话题是什么？\n\n"
                    "例如：某行业的市场规模、某城市的某类资源分布、"
                    "某技术的发展趋势、某公司的竞争格局……"
                ))],
                "active_agent": "research_agent",
                "pending_agent": "research_agent",
                "critique": "",
            }

        # Stage 1: queries
        queries = _make_queries(user_msg)
        logger.info("research_agent: queries=%r", queries)

        # Stage 2: parallel web searches
        raw_searches = await asyncio.gather(*[_search(q) for q in queries], return_exceptions=True)
        search_results = [str(r) for r in raw_searches]

        # Stage 3: extract & scrape top URLs
        urls = _extract_urls(search_results, max_urls=3)
        logger.info("research_agent: scraping urls=%r", urls)
        page_contents: list[str] = []
        if urls:
            raw_pages = await asyncio.gather(*[_scrape(u) for u in urls], return_exceptions=True)
            page_contents = [str(r) for r in raw_pages]

        # Stage 4: synthesis (1 LLM call, no tools)
        report = await _synthesize(user_msg, search_results, page_contents)

        return {
            "messages": [AIMessage(content=report)],
            "active_agent": "research_agent",
            "pending_agent": "",
            "critique": "",
        }

    return node
