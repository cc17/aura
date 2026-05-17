"""Score-to-rank tool — Steps 1-2 of Zhang Xuefeng's 5-step method.

Converts a gaokao score to provincial rank, then reverse-maps to equivalent
scores in reference years.
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
    get_rank_for_score,
    get_score_for_rank,
)
from backend.storage.cache_store import cache_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)


class ScoreToRankTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="score_to_rank",
            description=(
                "根据高考分数和省份查询省排名（位次），并换算往年等位分。"
                "这是张雪峰五步法的第 1-2 步。"
            ),
            parameters=[
                ToolParameter(
                    name="score",
                    type="integer",
                    description="高考分数",
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
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        score = kwargs.get("score")
        province = kwargs.get("province", "")
        subject_type = kwargs.get("subject_type", "")

        if score is None or not province:
            return "Error: score and province are required."

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
            return "Error: score, province, subject_type are required."

        if province not in SUPPORTED_PROVINCES:
            return f"Error: 暂不支持「{province}」，目前支持的省份：{'、'.join(SUPPORTED_PROVINCES)}"

        cache_key = cache_store.make_key(
            "score_to_rank", str(score), province, subject_type
        )
        cached = cache_store.get(cache_key)
        if cached is not None:
            logger.info("score_to_rank cache hit for key=%s", cache_key)
            return cached

        # Step 1: Score → Rank (current year)
        rank = get_rank_for_score(province, CURRENT_YEAR, subject_type, score)
        if rank is None:
            return f"Error: 无法查到 {province} {CURRENT_YEAR} 年 {subject_type} {score} 分的位次，请检查分数是否在合理范围内。"

        # Step 2: Rank → Equivalent scores in reference years
        equiv_scores: dict[int, int | None] = {}
        for ref_year in REFERENCE_YEARS:
            equiv_scores[ref_year] = get_score_for_rank(
                province, ref_year, subject_type, rank
            )

        # Format human-readable output
        lines = [
            f"## 第 1 步：查位次",
            f"- **{CURRENT_YEAR} 年 {province} {subject_type} {score} 分** → 省排名约 **第 {rank} 名**",
            "",
            f"## 第 2 步：换算等位分",
        ]
        for ref_year in REFERENCE_YEARS:
            eq = equiv_scores[ref_year]
            if eq is not None:
                lines.append(f"- {ref_year} 年等位分：**{eq} 分**")
            else:
                lines.append(f"- {ref_year} 年等位分：数据不足")
        lines.append("")

        # Machine-readable data block for downstream tools
        data = {
            "score": score,
            "province": province,
            "subject_type": subject_type,
            "year": CURRENT_YEAR,
            "rank": rank,
            "equivalent_scores": {str(y): s for y, s in equiv_scores.items()},
        }
        lines.append(f"<data>{json.dumps(data, ensure_ascii=False)}</data>")

        result = "\n".join(lines)
        cache_store.set(cache_key, result)
        return result
