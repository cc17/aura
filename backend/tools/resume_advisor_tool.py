"""Resume advisor tool — structured analysis with ATS scoring.

Returns a JSON-serialised report covering:
  - ats_score      : 0–100  estimated ATS keyword match
  - section_scores : per-section quality scores
  - strengths      : list of what works well
  - improvements   : ranked list of actionable suggestions
  - keywords       : missing high-value keywords for the target role
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

# Sections we look for in a resume
_SECTION_HEADINGS = {
    "summary": re.compile(r"summary|objective|profile|about|概述|简介", re.I),
    "experience": re.compile(r"experience|work|employment|职|经历|工作", re.I),
    "education": re.compile(r"education|school|university|college|学历|教育", re.I),
    "skills": re.compile(r"skill|技能|专长|competenc", re.I),
    "projects": re.compile(r"project|项目", re.I),
}

# Strong action verbs → ATS-friendly
_ACTION_VERBS = re.compile(
    r"\b(led|built|launched|drove|designed|architected|delivered|optimized|"
    r"increased|reduced|saved|managed|developed|implemented|created|"
    r"主导|搭建|负责|优化|提升|降低|带领|实现|完成|设计|开发)\b",
    re.I,
)

# Quantification patterns
_QUANT_PATTERN = re.compile(r"\d+\s*(%|percent|x|\+|万|亿|k\b|\$|元|人|台|条|次)", re.I)


def _detect_sections(text: str) -> dict[str, bool]:
    return {name: bool(pat.search(text)) for name, pat in _SECTION_HEADINGS.items()}


def _score_section(text: str, section: str) -> int:
    """Very lightweight heuristic, 0–10."""
    if not text.strip():
        return 0
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    score = 5  # base
    verbs = len(_ACTION_VERBS.findall(text))
    quants = len(_QUANT_PATTERN.findall(text))
    score += min(3, verbs)
    score += min(2, quants)
    return min(10, score)


def _ats_score(text: str, target_role: str) -> int:
    """Estimate ATS keyword match 0–100."""
    if not target_role:
        return 50
    keywords = re.findall(r"\w+", target_role.lower())
    hits = sum(1 for kw in keywords if kw in text.lower() and len(kw) > 2)
    ratio = hits / max(len(keywords), 1)
    base = int(ratio * 60)
    # Bonus for quantification
    base += min(20, len(_QUANT_PATTERN.findall(text)) * 3)
    # Bonus for action verbs
    base += min(20, len(_ACTION_VERBS.findall(text)) * 2)
    return min(100, base)


def _missing_keywords(text: str, target_role: str) -> list[str]:
    if not target_role:
        return []
    keywords = [kw for kw in re.findall(r"\w+", target_role.lower()) if len(kw) > 3]
    return [kw for kw in keywords if kw not in text.lower()]


class ResumeAdvisorTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="resume_advisor",
            description=(
                "Analyse a resume and return a structured JSON report with ATS score, "
                "section scores, key strengths, improvement suggestions, and missing keywords."
            ),
            parameters=[
                ToolParameter(
                    name="resume_text",
                    type="string",
                    description="Full plain-text content of the resume to analyse",
                ),
                ToolParameter(
                    name="target_role",
                    type="string",
                    description="Target job title or description for ATS keyword matching",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        resume_text: str = kwargs.get("resume_text", "")
        target_role: str = kwargs.get("target_role") or ""

        if not resume_text.strip():
            return json.dumps({"error": "resume_text is required"})

        sections = _detect_sections(resume_text)
        present = [s for s, found in sections.items() if found]
        missing_sections = [s for s, found in sections.items() if not found]

        section_scores = {s: _score_section(resume_text, s) for s in present}
        avg_score = int(sum(section_scores.values()) / max(len(section_scores), 1))

        ats = _ats_score(resume_text, target_role)
        missing_kw = _missing_keywords(resume_text, target_role)

        verb_count = len(_ACTION_VERBS.findall(resume_text))
        quant_count = len(_QUANT_PATTERN.findall(resume_text))

        strengths: list[str] = []
        improvements: list[str] = []

        if verb_count >= 5:
            strengths.append(f"Strong use of action verbs ({verb_count} found)")
        else:
            improvements.append(
                f"Add more strong action verbs (currently {verb_count}); aim for 8+"
            )

        if quant_count >= 4:
            strengths.append(f"Good quantification of achievements ({quant_count} data points)")
        else:
            improvements.append(
                f"Add more metrics/numbers ({quant_count} found); quantify at least 5 bullets"
            )

        if sections.get("summary"):
            strengths.append("Professional summary/objective section present")
        else:
            improvements.append("Add a compelling 2–3 sentence professional summary at the top")

        if missing_sections:
            improvements.append(
                f"Missing sections detected: {', '.join(missing_sections)}. "
                "Add them for completeness."
            )

        if missing_kw:
            improvements.append(
                f"ATS keyword gaps for '{target_role}': {', '.join(missing_kw[:6])}. "
                "Incorporate these naturally into your experience bullets."
            )

        if ats >= 70:
            strengths.append(f"High ATS compatibility score ({ats}/100)")
        elif ats >= 50:
            improvements.append(f"ATS score is moderate ({ats}/100); add more role-specific keywords")
        else:
            improvements.append(
                f"Low ATS score ({ats}/100); resume needs significant keyword alignment with target role"
            )

        report = {
            "ats_score": ats,
            "overall_score": avg_score,
            "section_scores": section_scores,
            "sections_present": present,
            "sections_missing": missing_sections,
            "strengths": strengths,
            "improvements": improvements,
            "missing_keywords": missing_kw[:10],
            "action_verb_count": verb_count,
            "quantification_count": quant_count,
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
