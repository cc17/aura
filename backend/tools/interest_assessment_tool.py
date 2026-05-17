"""Interest assessment tool — RIASEC-based interest-to-major mapping."""

from __future__ import annotations

from typing import Any

from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

# Holland RIASEC model: six personality types with traits and recommended majors
RIASEC_MAP: dict[str, dict[str, Any]] = {
    "R (实际型 Realistic)": {
        "traits": "喜欢动手操作、使用工具和机械，偏好具体、实际的任务",
        "majors": [
            "机械工程",
            "土木工程",
            "电气工程",
            "农学",
            "建筑学",
            "车辆工程",
            "材料科学与工程",
        ],
    },
    "I (研究型 Investigative)": {
        "traits": "喜欢思考、分析和探索，擅长抽象推理和科学研究",
        "majors": [
            "计算机科学与技术",
            "数学与应用数学",
            "物理学",
            "化学",
            "生物科学",
            "数据科学",
            "人工智能",
        ],
    },
    "A (艺术型 Artistic)": {
        "traits": "富有创造力和想象力，喜欢自由表达、艺术创作",
        "majors": [
            "视觉传达设计",
            "环境设计",
            "动画",
            "广播电视编导",
            "音乐学",
            "数字媒体艺术",
            "产品设计",
        ],
    },
    "S (社会型 Social)": {
        "traits": "喜欢与人交往、帮助他人，擅长沟通和教育",
        "majors": [
            "临床医学",
            "护理学",
            "教育学",
            "心理学",
            "社会工作",
            "学前教育",
            "公共事业管理",
        ],
    },
    "E (企业型 Enterprising)": {
        "traits": "喜欢领导、说服他人，擅长组织管理和商业决策",
        "majors": [
            "工商管理",
            "市场营销",
            "金融学",
            "法学",
            "国际经济与贸易",
            "电子商务",
            "会计学",
        ],
    },
    "C (常规型 Conventional)": {
        "traits": "喜欢有条理、有规则的工作，擅长数据处理和细节管理",
        "majors": [
            "信息管理与信息系统",
            "统计学",
            "审计学",
            "档案学",
            "图书馆学",
            "物流管理",
            "财务管理",
        ],
    },
}


class InterestAssessmentTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="interest_assessment",
            description=(
                "根据学生的兴趣描述，提供霍兰德 RIASEC 六型参考表和推荐专业方向。"
                "返回完整映射表供 LLM 做最终匹配推荐。"
            ),
            parameters=[
                ToolParameter(
                    name="interests",
                    type="string",
                    description="学生的兴趣描述，如 '我喜欢编程和数学'",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        interests = kwargs.get("interests", "").strip()
        if not interests:
            return "Error: interests parameter is required."

        lines = [
            f"学生兴趣描述：{interests}\n",
            "以下是霍兰德 RIASEC 职业兴趣模型六大类型及推荐专业：\n",
        ]

        for type_name, info in RIASEC_MAP.items():
            lines.append(f"### {type_name}")
            lines.append(f"**特征**：{info['traits']}")
            lines.append("**推荐专业**：" + "、".join(info["majors"]))
            lines.append("")

        lines.append(
            "请根据学生的兴趣描述，匹配最相关的 1-2 个类型，"
            "并从中推荐 3-5 个最合适的专业方向。"
        )
        return "\n".join(lines)
