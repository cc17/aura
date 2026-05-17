"""Check-requirements tool — Step 5 of Zhang Xuefeng's 5-step method.

Checks special admission requirements (vision, subject score, language,
gender, physical exam, subject selection) for a list of schools.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.data.gaokao.requirement_data import get_requirements
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)


class CheckRequirementsTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="check_requirements",
            description=(
                "检查目标院校的特殊录取要求（视力、单科、语种、选科、体检、性别等），"
                "避免退档风险。这是张雪峰五步法的第 5 步。"
            ),
            parameters=[
                ToolParameter(
                    name="schools_json",
                    type="string",
                    description=(
                        'JSON 数组，每个元素包含 university 和 major 字段，'
                        '如 [{"university":"复旦大学","major":"计算机科学与技术"}]'
                    ),
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        schools_json = kwargs.get("schools_json", "")
        if not schools_json:
            return "Error: schools_json is required."

        try:
            schools = json.loads(schools_json)
        except (json.JSONDecodeError, TypeError):
            return "Error: schools_json 格式错误，请传入有效的 JSON 数组。"

        if not isinstance(schools, list) or not schools:
            return "Error: schools_json 应为非空 JSON 数组。"

        lines = ["## 第 5 步：检查特殊要求（避退档）\n"]

        for item in schools:
            uni = item.get("university", "")
            major = item.get("major")
            if not uni:
                continue

            reqs = get_requirements(uni, major)

            if reqs:
                lines.append(f"### {uni} — {major or '全部专业'}")
                for req in reqs:
                    lines.append(f"- ⚠️ **{req.description}**（{req.requirement_type}）：{req.details}")
                lines.append("")
            else:
                lines.append(f"- ✅ **{uni}**（{major or '全部专业'}）：无特殊要求\n")

        lines.append(
            "💡 **提醒**：以上为已知的特殊要求，建议在填报前仔细阅读各校招生章程。"
        )
        return "\n".join(lines)
