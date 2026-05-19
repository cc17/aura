"""Supervisor graph: intent routing + reflection loop (max 3 iterations).

Graph topology
──────────────
                    ┌──────────┐
     start ──────► │supervisor│
                    └────┬─────┘
                         │ route_decision
              ┌──────────┼──────────────────────┐
              ▼          ▼         ▼             ▼       ▼
        general_agent  resume   gaokao_agent  ppt_agent  research_agent
              └──────────┴──────────┘──────────┘──────────┘
                                   │  all workers → reflection
                              ┌────▼─────┐
                              │reflection│
                              └────┬─────┘
                     loop_count<3  │  quality OK or loop>=3
                  ┌────────────────┤
                  ▼                ▼
           back to worker         END

KV cache
────────
• Supervisor routing call    cached via supervisor_cache (5-min TTL)
• Reflection scoring call    cached via reflection_cache (10-min TTL)
• All worker LLM streaming   NOT cached (content is unique per conversation)
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from backend.agent.intent import IntentResult, fast_classify, has_routing_keywords, map_llm_decision
from backend.config import settings
from backend.observability import trace
from backend.graph.agents.gaokao import create_gaokao_agent
from backend.graph.agents.general import create_general_agent
from backend.graph.agents.job_search import create_job_search_agent
from backend.graph.agents.ppt import create_ppt_agent
from backend.graph.agents.research import create_research_agent
from backend.graph.agents.resume import create_resume_agent
from backend.graph.state import AuraState
from backend.llm.kv_cache import reflection_cache, supervisor_cache
from backend.llm.langchain_bridge import create_chat_model

logger = logging.getLogger(__name__)

_MAX_LOOPS = 3

# ─── Supervisor prompt ────────────────────────────────────────────────────────

SUPERVISOR_PROMPT = (
    "You are a routing supervisor. Your ONLY job is to decide which specialist agent "
    "should handle the user's request. Reply with EXACTLY one word — the agent name.\n\n"
    "Available agents:\n"
    "- resume_agent   : Resumes — writing, critique, ATS optimisation, career advice.\n"
    "- ppt_agent      : Presentations — create PowerPoint/slide decks on any topic.\n"
    "- research_agent : Research — gather information, news, market analysis, reports.\n"
    "- gaokao_agent   : Chinese college entrance exam (高考) — scores, majors, universities.\n"
    "  Keywords: 高考、志愿填报、录取分数线、报考、选专业、就业前景。\n"
    "- job_search_agent: Job hunting — searching open positions, JD analysis, career positioning, "
    "which companies are hiring, market intelligence for job seekers.\n"
    "  Keywords: 找工作、求职、招聘、岗位、跳槽、转行、职业规划、JD分析、哪些公司在招\n"
    "- general_agent  : Everything else — chat, coding, Q&A, math, writing, etc.\n\n"
    "Reply with ONLY the agent name. No other text."
)

# ─── Reflection prompt ────────────────────────────────────────────────────────

REFLECTION_PROMPT = (
    "You are a quality evaluator reviewing an AI agent's response.\n"
    "Score the response on these criteria (each 0–10):\n"
    "  - Completeness : Does it fully answer the user's request?\n"
    "  - Quality      : Is it well-structured, specific, and actionable?\n"
    "  - Tool usage   : Did the agent use available tools when appropriate?\n\n"
    "Reply in EXACTLY this format (no other text):\n"
    "SCORE:<integer 0-10>\n"
    "CRITIQUE:<one concise sentence of the most important thing to improve, "
    "or 'none' if score>=7>\n\n"
    "Examples:\n"
    "SCORE:9\nCRITIQUE:none\n\n"
    "SCORE:5\nCRITIQUE:The resume was shown twice; remove the duplicate and add ATS keywords.\n"
)

# ─── Module-level compiled graph ─────────────────────────────────────────────

_compiled_graph = None

WORKER_AGENTS = frozenset(
    ("general_agent", "resume_agent", "gaokao_agent", "ppt_agent", "research_agent", "job_search_agent")
)


def _parse_reflection(text: str) -> tuple[int, str]:
    """Parse 'SCORE:n\nCRITIQUE:...' into (score, critique)."""
    score = 0
    critique = ""
    for line in text.strip().splitlines():
        if line.upper().startswith("SCORE:"):
            try:
                score = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.upper().startswith("CRITIQUE:"):
            critique = line.split(":", 1)[1].strip()
    return score, critique


def _build_graph(model: str | None = None):
    supervisor_model = model or settings.supervisor_model
    llm_supervisor = create_chat_model(supervisor_model)
    llm_reflection = create_chat_model(supervisor_model)

    # Worker nodes
    general_node = create_general_agent(model=settings.default_model)
    resume_node = create_resume_agent(model=settings.default_model)
    gaokao_node = create_gaokao_agent(model=settings.default_model)
    ppt_node = create_ppt_agent(model=settings.default_model)
    research_node = create_research_agent(model=settings.default_model)
    job_search_node = create_job_search_agent(model=settings.default_model)

    # ── Supervisor node ───────────────────────────────────────────────────────
    async def supervisor_node(state: AuraState) -> dict[str, Any]:
        messages = state["messages"]
        if not messages:
            return {"route_decision": "general_agent"}

        # Stage 1: keyword fast-path (zero LLM cost)
        last_user_text = ""
        for m in reversed(messages):
            if hasattr(m, "type") and m.type == "human":
                last_user_text = m.content if isinstance(m.content, str) else ""
                break

        fast: IntentResult | None = fast_classify(last_user_text)
        if fast is not None:
            route = f"{fast.intent}_agent"
            logger.info(
                "Supervisor fast-path → %s (conf=%.2f, kw=%r)",
                route, fast.confidence, last_user_text[:60],
            )
            trace(
                "intent_classify",
                path="fast_path",
                route=route,
                confidence=fast.confidence,
                query_preview=last_user_text[:60],
            )
            return {"route_decision": route}

        # No routing keywords at all → definitely general, skip LLM
        if not has_routing_keywords(last_user_text):
            logger.info("Supervisor no-keyword path → general_agent")
            trace(
                "intent_classify",
                path="no_keyword_path",
                route="general_agent",
                query_preview=last_user_text[:60],
            )
            return {"route_decision": "general_agent"}

        # Stage 2: LLM routing with KV cache (only for true keyword ties)
        llm_messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(messages)
        response = await supervisor_cache.ainvoke(llm_supervisor, llm_messages)
        intent = map_llm_decision(response.content)
        route = f"{intent}_agent"
        logger.info("Supervisor LLM → %s (raw=%r)", route, response.content[:40])
        trace(
            "intent_classify",
            path="llm_path",
            route=route,
            raw=response.content[:40],
            query_preview=last_user_text[:60],
        )
        return {"route_decision": route}

    def route_after_supervisor(state: AuraState) -> str:
        return state.get("route_decision", "general_agent")

    # ── Reflection node ───────────────────────────────────────────────────────
    async def reflection_node(state: AuraState) -> dict[str, Any]:
        loop_count: int = state.get("loop_count", 0)
        active_agent: str = state.get("active_agent", "general_agent")

        # general_agent handles open-ended chat — skip quality scoring
        if active_agent == "general_agent":
            trace("reflection_done", agent=active_agent, loop=loop_count, score=-1, approved=True, critique="")
            return {"reflection_done": True, "critique": ""}

        # Always exit after max loops
        if loop_count >= _MAX_LOOPS:
            logger.info("Reflection: max loops (%d) reached for %s", _MAX_LOOPS, active_agent)
            return {"reflection_done": True, "critique": ""}

        # Find the last assistant response to evaluate
        messages = state["messages"]
        last_ai_content = ""
        for m in reversed(messages):
            if hasattr(m, "type") and m.type == "ai" and isinstance(m.content, str):
                last_ai_content = m.content
                break

        if not last_ai_content:
            return {"reflection_done": True, "critique": ""}

        # Use the LAST human message as the original question — the first one
        # may belong to a previous conversation turn loaded from history.
        original_question = ""
        for m in reversed(messages):
            if hasattr(m, "type") and m.type == "human" and isinstance(m.content, str):
                original_question = m.content
                break

        eval_messages = [
            SystemMessage(content=REFLECTION_PROMPT),
            HumanMessage(
                content=(
                    f"User question: {original_question[:500]}\n\n"
                    f"Agent response:\n{last_ai_content[:2000]}"
                )
            ),
        ]

        response = await reflection_cache.ainvoke(llm_reflection, eval_messages)
        score, critique = _parse_reflection(response.content)

        logger.info(
            "Reflection score=%d loop=%d agent=%s critique=%r",
            score, loop_count, active_agent, critique[:80],
        )

        approved = score >= 7 or critique.lower() == "none"
        trace(
            "reflection_done",
            agent=active_agent,
            loop=loop_count,
            score=score,
            approved=approved,
            critique=critique[:80] if not approved else "",
        )

        if approved:
            return {"reflection_done": True, "critique": ""}

        # Needs improvement: increment counter and inject critique
        return {
            "reflection_done": False,
            "loop_count": loop_count + 1,
            "critique": critique,
        }

    def route_after_reflection(state: AuraState) -> str:
        if state.get("reflection_done", True):
            return END
        # Route back to the same worker that produced the response
        active = state.get("active_agent", "general_agent")
        if active not in WORKER_AGENTS:
            return END
        return active

    # ── Build StateGraph ──────────────────────────────────────────────────────
    graph = StateGraph(AuraState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("general_agent", general_node)
    graph.add_node("resume_agent", resume_node)
    graph.add_node("gaokao_agent", gaokao_node)
    graph.add_node("ppt_agent", ppt_node)
    graph.add_node("research_agent", research_node)
    graph.add_node("job_search_agent", job_search_node)
    graph.add_node("reflection", reflection_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "general_agent":    "general_agent",
            "resume_agent":     "resume_agent",
            "gaokao_agent":     "gaokao_agent",
            "ppt_agent":        "ppt_agent",
            "research_agent":   "research_agent",
            "job_search_agent": "job_search_agent",
        },
    )

    # All workers feed into reflection
    for agent in WORKER_AGENTS:
        graph.add_edge(agent, "reflection")

    graph.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {
            "general_agent":    "general_agent",
            "resume_agent":     "resume_agent",
            "gaokao_agent":     "gaokao_agent",
            "ppt_agent":        "ppt_agent",
            "research_agent":   "research_agent",
            "job_search_agent": "job_search_agent",
            END:                END,
        },
    )

    return graph.compile()


def init_graph(model: str | None = None) -> None:
    global _compiled_graph
    _compiled_graph = _build_graph(model)
    logger.info("Multi-agent graph initialised (workers=%s, max_loops=%d)", WORKER_AGENTS, _MAX_LOOPS)


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        init_graph()
    return _compiled_graph
