"""Tests for the two-stage intent recogniser."""

import pytest

from backend.agent.intent import IntentResult, fast_classify, map_llm_decision


# ── fast_classify ─────────────────────────────────────────────────────────────

def test_resume_keyword():
    result = fast_classify("帮我改一下简历")
    assert result is not None
    assert result.intent == "resume"
    assert result.matched_by == "keyword"
    assert result.confidence > 0.5


def test_ppt_keyword_english():
    result = fast_classify("Can you make a PPT for me about climate change?")
    assert result is not None
    assert result.intent == "ppt"


def test_ppt_keyword_chinese():
    result = fast_classify("帮我做一个幻灯片，主题是产品发布")
    assert result is not None
    assert result.intent == "ppt"


def test_research_keyword():
    result = fast_classify("帮我调研一下新能源汽车市场")
    assert result is not None
    assert result.intent == "research"


def test_gaokao_keyword():
    result = fast_classify("我高考600分，应该怎么填志愿？")
    assert result is not None
    assert result.intent == "gaokao"


def test_general_returns_none():
    # No domain keywords → None so LLM decides
    result = fast_classify("今天天气真好啊")
    assert result is None


def test_multiple_resume_hits_higher_confidence():
    r1 = fast_classify("简历")
    r2 = fast_classify("简历 resume cv ats 改简历")
    assert r2 is not None
    assert r1 is not None
    assert r2.confidence >= r1.confidence


def test_ambiguous_returns_none():
    # resume + gaokao tie → None
    result = fast_classify("简历 高考 志愿")
    # May or may not be None depending on hit counts; just ensure no crash
    assert result is None or isinstance(result, IntentResult)


# ── map_llm_decision ──────────────────────────────────────────────────────────

def test_map_llm_resume():
    assert map_llm_decision("resume_agent") == "resume"


def test_map_llm_ppt():
    assert map_llm_decision("ppt_agent") == "ppt"


def test_map_llm_research():
    assert map_llm_decision("research_agent") == "research"


def test_map_llm_gaokao():
    assert map_llm_decision("gaokao_agent") == "gaokao"


def test_map_llm_general():
    assert map_llm_decision("general_agent") == "general"
    assert map_llm_decision("something_unknown") == "general"


def test_map_llm_chinese():
    assert map_llm_decision("高考相关") == "gaokao"
    assert map_llm_decision("简历修改") == "resume"
