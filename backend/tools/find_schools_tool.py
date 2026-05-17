"""Find-schools tool — Steps 3-4 of Zhang Xuefeng's 5-step method.

Given a rank, find matching universities and classify them into
冲 (reach) / 稳 (match) / 保 (safety) / 底 (floor) tiers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.data.gaokao.province_models import get_gaokao_model, infer_subject_type
from backend.data.gaokao.score_rank_table import (
    CURRENT_YEAR,
    REFERENCE_YEARS,
    SUPPORTED_PROVINCES,
    get_score_for_rank,
)
from backend.data.gaokao.university_data import find_schools_by_score_range
from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

# Tier classification thresholds (delta = school_min_score - equiv_score)
_TIER_RANGES = {
    "冲": (5, 20),      # Reach: school is 5-20 points above you
    "稳": (-5, 5),      # Match: within ±5
    "保": (-10, -5),    # Safety: school is 5-10 points below you
    "底": (-30, -10),   # Floor: school is 10-30 points below you
}


def _classify_tier(delta: int) -> str | None:
    """Classify a school into 冲/稳/保/底 based on score delta."""
    for tier_name, (low, high) in _TIER_RANGES.items():
        if low <= delta <= high:
            return tier_name
    return None


class FindSchoolsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="find_schools",
            description=(
                "根据位次筛选可报考的大学，并按冲/稳/保/底四档分类。"
                "这是张雪峰五步法的第 3-4 步。"
            ),
            parameters=[
                ToolParameter(
                    name="rank",
                    type="integer",
                    description="考生省排名（位次），由 score_to_rank 工具获得",
                ),
                ToolParameter(
                    name="province",
                    type="string",
                    description="省份，如 '上海'",
                ),
                ToolParameter(
                    name="subject_type",
                    type="string",
                    description=(
                        "科类。3+3 省份（上海等）自动为'综合'，无需传；"
                        "3+1+2 省份传'物理类'或'历史类'；传统省份传'理科'或'文科'"
                    ),
                    enum=["理科", "文科", "综合", "物理类", "历史类"],
                    required=False,
                ),
                ToolParameter(
                    name="city_preference",
                    type="string",
                    description="城市偏好，如 '上海'、'北京'",
                    required=False,
                ),
                ToolParameter(
                    name="tier_preference",
                    type="string",
                    description="院校层次偏好",
                    enum=["985", "211", "一本", "二本"],
                    required=False,
                ),
                ToolParameter(
                    name="major_keyword",
                    type="string",
                    description="专业关键词，如 '计算机'、'医学'",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        rank = kwargs.get("rank")
        province = kwargs.get("province", "")
        subject_type = kwargs.get("subject_type", "")

        if rank is None or not province:
            return "Error: rank and province are required."

        # Auto-detect subject_type from province gaokao model
        subject_type = infer_subject_type(province, subject_type or None) or ""
        if not subject_type:
            model = get_gaokao_model(province)
            if model:
                options = "、".join(model.subject_types)
                return (
                    f"请提供科类（subject_type）。"
                    f"{province}采用 **{model.name}** 模式，"
                    f"可选值：{options}"
                )
            return "Error: rank, province, subject_type are required."

        if province not in SUPPORTED_PROVINCES:
            return f"Error: 暂不支持「{province}」，目前支持的省份：{'、'.join(SUPPORTED_PROVINCES)}"

        city_pref = kwargs.get("city_preference")
        tier_pref = kwargs.get("tier_preference")
        major_kw = kwargs.get("major_keyword")

        cache_key = cache_store.make_key(
            "find_schools",
            str(rank), province, subject_type,
            str(city_pref or ""), str(tier_pref or ""), str(major_kw or ""),
        )
        cached = cache_store.get(cache_key)
        if cached is not None:
            logger.info("find_schools cache hit for key=%s", cache_key)
            return cached

        # Convert rank → equivalent score in current year
        equiv_score = get_score_for_rank(province, CURRENT_YEAR, subject_type, rank)
        if equiv_score is None:
            return f"Error: 无法将位次 {rank} 转换为等位分，请检查位次是否合理。"

        # Search range: equiv_score - 30 to equiv_score + 20
        search_min = equiv_score - 30
        search_max = equiv_score + 20

        records = find_schools_by_score_range(
            province, subject_type, search_min, search_max,
            year=CURRENT_YEAR,
            city=city_pref,
            tier=tier_pref,
            major_keyword=major_kw,
        )

        if not records:
            return "未找到符合条件的院校，请尝试调整筛选条件（如放宽城市或层次偏好）。"

        # Classify into tiers
        tiered: dict[str, list] = {"冲": [], "稳": [], "保": [], "底": []}
        for rec in records:
            delta = rec.min_score - equiv_score
            tier_name = _classify_tier(delta)
            if tier_name:
                tiered[tier_name].append((rec, delta))

        # Format output
        tier_labels = {
            "冲": "冲刺 (Reach)",
            "稳": "稳妥 (Match)",
            "保": "保底 (Safety)",
            "底": "垫底 (Floor)",
        }

        lines = [
            f"## 第 3-4 步：筛选院校 & 梯度排序",
            f"等位分：**{equiv_score} 分**（位次 {rank}）",
            f"搜索范围：{search_min}–{search_max} 分\n",
        ]

        school_list: list[dict] = []
        for tier_name in ["冲", "稳", "保", "底"]:
            items = tiered[tier_name]
            label = tier_labels[tier_name]
            lines.append(f"### {label}（{len(items)} 所）")
            if not items:
                lines.append("- （无）\n")
                continue
            for rec, delta in items:
                sign = "+" if delta >= 0 else ""
                lines.append(
                    f"- **{rec.university}** — {rec.major}｜"
                    f"{rec.tier}｜最低分 {rec.min_score}（{sign}{delta}）"
                )
                school_list.append({
                    "university": rec.university,
                    "major": rec.major,
                    "tier": tier_name,
                    "school_tier": rec.tier,
                    "min_score": rec.min_score,
                    "delta": delta,
                })
            lines.append("")

        # Machine-readable data for check_requirements
        data = {
            "equiv_score": equiv_score,
            "rank": rank,
            "schools": school_list,
        }
        lines.append(f"<data>{json.dumps(data, ensure_ascii=False)}</data>")

        result = "\n".join(lines)
        cache_store.set(cache_key, result)
        return result
