"""Pricing API — static plan configuration."""

from fastapi import APIRouter

router = APIRouter(prefix="/pricing")

_PLANS = [
    {
        "key": "free",
        "name": "Free",
        "price_label": "¥0",
        "period": "",
        "features": [
            "20 次 AI 对话 / 天",
            "近 30 天历史记录",
            "标准模型（Doubao）",
            "全部 24 个技能",
            "记忆功能",
        ],
        "cta": "当前计划",
        "recommended": False,
    },
    {
        "key": "pro",
        "name": "Pro",
        "price_label": "¥39",
        "period": "/ 月",
        "features": [
            "1000 次 AI 对话 / 月",
            "永久历史记录",
            "标准 + 高级模型",
            "全部 24 个技能",
            "记忆功能",
        ],
        "cta": "立即升级",
        "recommended": True,
    },
    {
        "key": "max",
        "name": "Max",
        "price_label": "¥99",
        "period": "/ 月",
        "features": [
            "无限次 AI 对话",
            "永久历史记录",
            "全部模型含最新版",
            "全部 24 个技能",
            "记忆功能",
        ],
        "cta": "升级 Max",
        "recommended": False,
    },
]


@router.get("")
async def get_pricing():
    return {"plans": _PLANS}
