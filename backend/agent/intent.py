"""Intent recognition — two-stage classifier.

Stage 1 (fast, zero-cost): keyword pattern matching, covers ~80 % of traffic.
Stage 2 (LLM fallback):    supervisor LLM call for ambiguous / mixed intents.

Intents:
  resume   — resume writing, critique, ATS optimisation
  ppt      — slide deck creation, presentation, PowerPoint
  research — information gathering, market research, news collection
  gaokao   — college entrance exam, university selection, 志愿填报
  general  — everything else
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Keyword tables
# ---------------------------------------------------------------------------

_RESUME_KW = re.compile(
    r"简历|resume|cv\b|求职信|cover letter|工作经历|自我介绍|职业目标|"
    r"ats|竞争力|投简历|改简历|润色简历|简历修改|简历优化|简历点评",
    re.IGNORECASE,
)

_PPT_KW = re.compile(
    r"ppt|powerpoint|幻灯片|演示文稿|slide|keynote|汇报材料|做个ppt|"
    r"制作幻灯|pptx|报告制作|演讲稿|制作演示",
    re.IGNORECASE,
)

_RESEARCH_KW = re.compile(
    r"调研|搜集资料|收集信息|资料整理|市场分析|行业报告|信息收集|"
    r"帮我找|查一下|调查|research|gather|collect\s+info|search\s+for|"
    r"give me info|最新资讯|新闻资讯|背景调查",
    re.IGNORECASE,
)

_GAOKAO_KW = re.compile(
    r"高考|志愿|录取分数线|报考|选专业|就业前景|gaokao|高校|大学排名|"
    r"填志愿|选学校|考研|专业推荐|院校推荐",
    re.IGNORECASE,
)

_INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("resume", _RESUME_KW),
    ("ppt", _PPT_KW),
    ("research", _RESEARCH_KW),
    ("gaokao", _GAOKAO_KW),
]


@dataclass
class IntentResult:
    intent: str          # one of: resume | ppt | research | gaokao | general
    confidence: float    # 0.0–1.0
    matched_by: str      # "keyword" | "llm" | "default"


def has_routing_keywords(text: str) -> bool:
    """Return True if any non-general routing keyword is present."""
    return any(pattern.search(text) for _, pattern in _INTENT_PATTERNS)


def fast_classify(text: str) -> IntentResult | None:
    """Return IntentResult if a single intent dominates, else None (ambiguous)."""
    hits: dict[str, int] = {}
    for name, pattern in _INTENT_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            hits[name] = len(matches)

    if not hits:
        return None  # let LLM decide between 'general' and others

    # If one intent has clearly more hits, pick it
    ranked = sorted(hits.items(), key=lambda x: x[1], reverse=True)
    top_intent, top_count = ranked[0]
    second_count = ranked[1][1] if len(ranked) > 1 else 0

    # Unambiguous when the top count is strictly larger or single match
    if top_count > second_count or len(ranked) == 1:
        confidence = min(0.95, 0.6 + top_count * 0.1)
        return IntentResult(intent=top_intent, confidence=confidence, matched_by="keyword")

    return None  # tie — caller should use LLM


def map_llm_decision(decision: str) -> str:
    """Map a raw LLM routing token to a canonical intent name."""
    d = decision.strip().lower()
    if "resume" in d or "简历" in d:
        return "resume"
    if "ppt" in d or "幻灯" in d or "slide" in d:
        return "ppt"
    if "research" in d or "调研" in d or "资料" in d:
        return "research"
    if any(kw in d for kw in ("gaokao", "高考", "志愿", "录取", "报考")):
        return "gaokao"
    return "general"
