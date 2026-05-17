"""Build the system prompt from user profile, memories, and optional skill context."""

from __future__ import annotations


def _field_value(profile: dict, key: str) -> str:
    """Extract the string value from a confidence-wrapped profile field."""
    field = profile.get(key)
    if isinstance(field, dict):
        return field.get("value", "")
    return str(field) if field else ""


def build_system_prompt(
    profile: dict | None,
    memories: list[str] | None = None,
    skill: str | None = None,
) -> str:
    """Return the system prompt to prepend before every main LLM call.

    Phase 2: only profile injection.
    Phase 4 will add memories; Phase 3 will handle skill override.

    Returns empty string if profile is None/empty (graceful degradation).
    """
    if skill:
        # Skill场景：prompt_template 已经包含完整指令，这里只追加画像片段
        return _profile_snippet(profile) if profile else ""

    if not profile:
        return ""

    lines = [
        "你是用户的工作搭子，不是通用 AI 助手。",
        "",
        "【关于这位用户】",
    ]

    industry = _field_value(profile, "industry")
    role = _field_value(profile, "role")
    ai_prof = _field_value(profile, "ai_proficiency")
    pain_points = profile.get("pain_points", [])
    style = profile.get("style_preference", {})

    if industry:
        lines.append(f"- 行业：{industry}")
    if role:
        lines.append(f"- 岗位：{role}")
    if pain_points:
        lines.append(f"- 主要痛点：{'、'.join(pain_points)}")
    if ai_prof:
        lines.append(f"- AI 熟练度：{ai_prof}")
    if style:
        style_desc = []
        if style.get("length"):
            style_desc.append(f"回答{style['length']}")
        if style.get("tone"):
            style_desc.append(style["tone"])
        if style_desc:
            lines.append(f"- 偏好风格：{'、'.join(style_desc)}")

    if memories:
        lines.append("")
        lines.append("【你记得的事】")
        for m in memories:
            lines.append(f"- {m}")

    lines += [
        "",
        "【你的行为准则】",
        "1. 回答紧扣这个用户的行业和岗位，不说放之四海皆准的废话",
        "2. 主动用「你们行业」「你这个岗位」这类表述，体现懂他",
        "3. 答完一个问题，自然带出下一步建议",
    ]

    if isinstance(style, dict) and style.get("length") == "简洁":
        lines.append("4. 回答简洁，不堆砌废话")

    return "\n".join(lines)


def _profile_snippet(profile: dict) -> str:
    """Short profile block appended to skill prompts."""
    industry = _field_value(profile, "industry")
    role = _field_value(profile, "role")
    if not industry and not role:
        return ""
    parts = []
    if industry:
        parts.append(f"行业：{industry}")
    if role:
        parts.append(f"岗位：{role}")
    return "【用户画像参考】\n" + "\n".join(f"- {p}" for p in parts)
