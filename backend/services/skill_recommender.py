"""Recommendation pipeline: Context → Recall → Coarse Rank → Fine Rank → Re-rank."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.memory.models import (
    SkillSignalModel,
    UserSkillAffinityModel,
    UserSkillModel,
)
from backend.services.skill_registry import all_skills, get_skill_by_id, list_skills

logger = logging.getLogger(__name__)

# Pain point label → Chinese keywords for matching against Chinese skill names/taglines
_PAIN_POINT_CN: dict[str, str] = {
    # Student
    "Exam Prep": "备考 考试",
    "Thesis Writing": "论文 毕业",
    "Job Applications": "求职 简历 实习",
    "Essay Practice": "写作 申论",
    "Cover Letters": "求职信 简历",
    "Study Abroad": "留学 文书",
    # Legal
    "Contract Review": "合同 审查",
    "Legal Drafting": "法律文书 起草",
    "Case Research": "案件 调研",
    "Trial Prep": "庭审",
    "Client Communication": "客户 沟通",
    "Case Management": "案件管理",
    # Healthcare
    "Medical Records": "病历",
    "Patient Communication": "患者",
    "Literature Review": "文献",
    "Discharge Summary": "出院",
    "Case Discussion": "病例",
    # Tech
    "Weekly Reports": "周报",
    "Meeting Notes": "会议纪要",
}

MAX_TOTAL = 6
_MAX_PER_LAYER = 2  # diversity cap per skill layer in coarse rank

# Fine rank composite weights (must sum to 1.0)
_W_PROFILE = 0.40
_W_CTR = 0.25
_W_AFFINITY = 0.25
_W_RECENCY = 0.10

# Profile keyword matching weights
_W_PAIN = 3
_W_ROLE = 2
_W_INDUSTRY = 1


@dataclass(frozen=True)
class _AgentDef:
    key: str
    icon: str
    label: str
    tagline: str
    sample_message: str
    universal: bool
    pain_point_keywords: tuple[str, ...]
    role_keywords: tuple[str, ...]


_AGENTS: list[_AgentDef] = [
    _AgentDef(
        key="career",
        icon="💼",
        label="求职 / 简历",
        tagline="找工作、改简历、分析 JD",
        sample_message="帮我看看求职方向，我想了解一下适合我的岗位",
        universal=False,
        pain_point_keywords=("简历", "求职", "找工作", "投递", "offer", "跳槽", "转行", "面试", "招聘", "实习",
                             "job applications", "cover letters", "internship"),
        role_keywords=("应届", "实习生", "待业", "毕业生", "大学生",
                       "undergraduate", "graduate", "phd", "international student"),
    ),
    _AgentDef(
        key="gaokao",
        icon="🎓",
        label="高考志愿",
        tagline="分数查院校、专业就业前景",
        sample_message="帮我填高考志愿",
        universal=False,
        pain_point_keywords=("高考", "志愿", "报考", "选专业", "备考"),
        role_keywords=("高中生", "高三", "考生"),
    ),
    _AgentDef(
        key="ppt",
        icon="📊",
        label="做 PPT",
        tagline="输入主题，自动生成幻灯片",
        sample_message="帮我做一个PPT",
        universal=True,
        pain_point_keywords=("汇报", "演示", "ppt", "幻灯", "周报", "述职", "提案"),
        role_keywords=("运营", "产品", "经理", "总监", "主管"),
    ),
    _AgentDef(
        key="research",
        icon="🔍",
        label="调研分析",
        tagline="收集信息、市场分析、行业报告",
        sample_message="帮我调研一个话题",
        universal=True,
        pain_point_keywords=("调研", "分析", "报告", "资料", "信息收集", "竞品", "市场", "数据"),
        role_keywords=("分析师", "运营", "策略", "研究员"),
    ),
]


def _parse_profile(profile: dict) -> tuple[str, str, list[str]]:
    def _val(f: str) -> str:
        v = profile.get(f)
        return v.get("value", "") if isinstance(v, dict) else (v or "")

    industry = _val("industry")
    role = _val("role")
    pain_raw = profile.get("pain_points", [])
    if isinstance(pain_raw, str):
        pain_points = [p.strip() for p in pain_raw.replace("，", ",").split(",") if p.strip()]
    elif isinstance(pain_raw, list):
        pain_points = [str(p) for p in pain_raw if p]
    else:
        pain_points = []
    return industry, role, pain_points


# ── Stage 1: Recall ───────────────────────────────────────────────────────────

def _recall(industry: str, role: str, pinned_ids: set[int]) -> list[dict]:
    """Gather candidates: role-mapped first, then universal, then all skills as fallback."""
    mapped = list_skills(industry=industry or None, role=role or None)
    mapped_keys = {s["skill_key"] for s in mapped}
    universal = [s for s in all_skills() if s.get("is_universal") and s["skill_key"] not in mapped_keys]
    candidates = mapped + universal
    if not candidates:
        candidates = list(all_skills())
    return [s for s in candidates if s["id"] not in pinned_ids]


# ── Stage 2: Coarse rank (diversity by layer) ─────────────────────────────────

def _coarse_rank(candidates: list[dict]) -> list[dict]:
    """Cap per-layer count to ensure category diversity."""
    counts: dict[int, int] = {}
    result = []
    for s in candidates:
        layer = int(s.get("layer") or 1)
        if counts.get(layer, 0) < _MAX_PER_LAYER:
            result.append(s)
            counts[layer] = counts.get(layer, 0) + 1
    return result


# ── Stage 3: Fine rank (composite scoring) ────────────────────────────────────

def _profile_score_norm(skill: dict, industry: str, role: str, pain_points: list[str]) -> float:
    """Keyword match score, normalized to [0, 1]."""
    text = f"{skill['scenario_name']} {skill.get('tagline') or ''}".lower()
    # Expand English pain point labels to Chinese keywords for matching Chinese skill names
    expanded_pain: list[str] = []
    for p in pain_points:
        expanded_pain.append(p.lower())
        if p in _PAIN_POINT_CN:
            expanded_pain.extend(_PAIN_POINT_CN[p].lower().split())
    raw = float(sum(_W_PAIN for kw in expanded_pain if kw in text))
    if role and role.lower() in text:
        raw += _W_ROLE
    if industry and industry.lower() in text:
        raw += _W_INDUSTRY
    return min(raw / 15.0, 1.0)  # 15 ≈ 5 pain-point matches


async def _fine_rank(
    candidates: list[dict],
    user_id: int,
    industry: str,
    role: str,
    pain_points: list[str],
    session: AsyncSession,
) -> list[dict]:
    if not candidates:
        return []

    skill_ids = [s["id"] for s in candidates]
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Global CTR: clicked / impressioned in the last 30 days
    ctr_rows = (
        await session.execute(
            select(
                SkillSignalModel.skill_id,
                func.count()
                .filter(SkillSignalModel.signal_type == "impressioned")
                .label("imp"),
                func.count()
                .filter(SkillSignalModel.signal_type == "clicked")
                .label("clk"),
            )
            .where(
                SkillSignalModel.skill_id.in_(skill_ids),
                SkillSignalModel.created_at >= cutoff,
            )
            .group_by(SkillSignalModel.skill_id)
        )
    ).all()

    ctr_map: dict[int, float] = {}
    for row in ctr_rows:
        imp, clk = row.imp or 0, row.clk or 0
        ctr_map[row.skill_id] = clk / imp if imp > 0 else 0.0

    # Per-user affinity + cool-down check
    affinity_rows = (
        await session.execute(
            select(
                UserSkillAffinityModel.skill_id,
                UserSkillAffinityModel.affinity_score,
                UserSkillAffinityModel.last_used_at,
                UserSkillAffinityModel.recommendation_cool_down_until,
            )
            .where(
                UserSkillAffinityModel.user_id == user_id,
                UserSkillAffinityModel.skill_id.in_(skill_ids),
            )
        )
    ).all()

    now = datetime.now(timezone.utc)
    affinity_map: dict[int, tuple[float, datetime | None]] = {}
    blocked: set[int] = set()
    for row in affinity_rows:
        if row.recommendation_cool_down_until:
            cool_until = row.recommendation_cool_down_until
            if cool_until.tzinfo is None:
                cool_until = cool_until.replace(tzinfo=timezone.utc)
            if cool_until > now:
                blocked.add(row.skill_id)
        affinity_map[row.skill_id] = (float(row.affinity_score), row.last_used_at)

    scored: list[tuple[float, dict]] = []
    for skill in candidates:
        sid = skill["id"]
        if sid in blocked:
            continue
        profile_n = _profile_score_norm(skill, industry, role, pain_points)
        ctr = ctr_map.get(sid, 0.0)
        affinity, last_used = affinity_map.get(sid, (0.5, None))

        recency = 0.0
        if last_used:
            lu = last_used if last_used.tzinfo else last_used.replace(tzinfo=timezone.utc)
            recency = max(0.0, 1.0 - (now - lu).days / 7.0)

        composite = (
            profile_n * _W_PROFILE
            + ctr * _W_CTR
            + affinity * _W_AFFINITY
            + recency * _W_RECENCY
        )
        scored.append((composite, skill))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored]


# ── Agent recommendations (config-based, no DB) ───────────────────────────────

def _get_agents(role: str, pain_points: list[str]) -> list[dict]:
    """Score agents by profile signals; universal agents always qualify."""
    pain_text = " ".join(pain_points).lower()
    role_text = role.lower()
    scored: list[tuple[float, _AgentDef]] = []
    for agent in _AGENTS:
        pain_score = sum(_W_PAIN for kw in agent.pain_point_keywords if kw in pain_text)
        role_score = sum(_W_ROLE for kw in agent.role_keywords if kw in role_text)
        total = float(pain_score + role_score)
        if agent.universal or total > 0:
            scored.append((total, agent))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "key": a.key,
            "icon": a.icon,
            "label": a.label,
            "tagline": a.tagline,
            "sampleMessage": a.sample_message,
        }
        for _, a in scored
    ]


# ── Main entry point ──────────────────────────────────────────────────────────

async def get_recommendations(
    user_id: int,
    profile: dict,
    session: AsyncSession,
) -> dict:
    """Run the full pipeline and return {pinned, agents, skills} for the home screen."""
    industry, role, pain_points = _parse_profile(profile)

    pinned_rows = (
        await session.execute(
            select(UserSkillModel)
            .where(
                UserSkillModel.user_id == user_id,
                UserSkillModel.is_pinned == True,  # noqa: E712
            )
            .order_by(UserSkillModel.added_at)
        )
    ).scalars().all()

    pinned_ids = {row.skill_id for row in pinned_rows}
    pinned = [s for row in pinned_rows if (s := get_skill_by_id(row.skill_id))]

    remaining = max(0, MAX_TOTAL - len(pinned))
    if remaining == 0:
        return {"pinned": pinned, "agents": [], "skills": []}

    agents = _get_agents(role, pain_points)

    # Skill pipeline
    candidates = _recall(industry, role, pinned_ids)
    candidates = _coarse_rank(candidates)
    candidates = await _fine_rank(candidates, user_id, industry, role, pain_points, session)

    agent_slots = min(len(agents), remaining)
    skill_slots = remaining - agent_slots

    return {
        "pinned": pinned,
        "agents": agents[:agent_slots],
        "skills": candidates[:skill_slots],
    }
