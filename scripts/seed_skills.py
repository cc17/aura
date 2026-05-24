"""Idempotent skill seed script.

Upserts every skill in SKILLS into industry_skills and deletes any row
whose skill_key is not in this list. Safe to run multiple times.

Usage:
    uv run python scripts/seed_skills.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from backend.memory.database import get_session_factory
from backend.memory.models import IndustrySkillModel

SKILLS: list[dict] = [
    dict(
        skill_key="cover_letter",
        scenario_name="求职信生成",
        description="根据你的简历和目标职位描述，生成针对性求职信",
        trigger_keywords=["求职信", "自荐信", "cover letter", "申请信"],
        prompt_template=(
            "请根据以下信息为我生成一封求职信。\n\n"
            "【我的简历】\n{resume}\n\n"
            "【目标职位 JD】\n{jd}\n\n"
            "{#if company}【目标公司】\n{company}\n{/if}"
            "【风格要求】{tone}\n\n"
            "要求：\n"
            "- 开头点出与该岗位的核心契合点（从 JD 提取关键词）\n"
            "- 中段用简历中 1-2 个具体成就支撑，要有数字\n"
            "- 结尾表达加入意愿，简洁有力\n"
            "- 控制在 300 字以内，不写废话"
        ),
        input_schema={"fields": [
            {"name": "resume", "type": "textarea", "label": "你的简历（粘贴文字版）", "required": True, "placeholder": "粘贴简历内容…"},
            {"name": "jd", "type": "textarea", "label": "目标职位 JD", "required": True, "placeholder": "粘贴职位描述…"},
            {"name": "company", "type": "text", "label": "公司名称", "required": False, "placeholder": "例：字节跳动"},
            {"name": "tone", "type": "select", "label": "风格", "default": "专业正式", "options": ["专业正式", "积极热情", "简洁干练"], "required": False},
        ]},
        enabled=True, display_order=10,
        tagline="简历 + JD → 一封有说服力的求职信",
        display_metadata={}, is_universal=True, layer=1, version="1.0.0",
    ),
    dict(
        skill_key="study_abroad_essay",
        scenario_name="留学文书润色",
        description="对留学申请文书（PS / SOP / 推荐信等）进行结构优化和语言润色",
        trigger_keywords=["留学文书", "personal statement", "PS", "SOP", "推荐信", "留学申请", "文书润色"],
        prompt_template=(
            "请帮我润色这份{doc_type}。\n\n"
            "【文书草稿】\n{essay}\n\n"
            "{#if target}【目标项目】\n{target}\n{/if}"
            "{#if focus}【重点改进方向】\n{focus}\n{/if}"
            "润色要求：\n"
            "- 保留原有的核心故事和真实声音，不要替换成套话\n"
            "- 强化开头钩子，让招生官第一段就有继续读的欲望\n"
            "- 确保每段有清晰的论点，段落间过渡自然\n"
            "- 具体细节 > 抽象描述\n"
            "- 结尾有力，呼应开头或展望未来\n"
            "- 语言流畅自然，避免用词过于华丽或冗长\n\n"
            "请先给出润色后的完整版本，再用 2-3 条说明主要改动了什么。"
        ),
        input_schema={"fields": [
            {"name": "essay", "type": "textarea", "label": "你的文书草稿", "required": True, "placeholder": "粘贴文书内容…"},
            {"name": "doc_type", "type": "select", "label": "文书类型", "default": "个人陈述 (PS)", "options": ["个人陈述 (PS)", "留学目的陈述 (SOP)", "推荐信", "奖学金申请", "其他"], "required": True},
            {"name": "target", "type": "text", "label": "目标项目 / 院校", "required": False, "placeholder": "例：哥大新闻学院 MA"},
            {"name": "focus", "type": "text", "label": "希望重点改进的方面", "required": False, "placeholder": "例：逻辑不清晰、开头太平、语言太口语"},
        ]},
        enabled=True, display_order=20,
        tagline="把你的故事打磨成打动招生官的文书",
        display_metadata={}, is_universal=True, layer=1, version="1.0.0",
    ),
    dict(
        skill_key="thesis_outline",
        scenario_name="论文大纲生成",
        description="根据论文题目和要求，生成层次清晰、论点充分的论文大纲",
        trigger_keywords=["论文大纲", "论文结构", "毕业论文", "学术论文", "开题报告", "论文框架"],
        prompt_template=(
            "请为以下论文生成详细大纲。\n\n"
            "【题目】{topic}\n"
            "【类型】{paper_type}\n"
            "{#if word_count}【字数】{word_count}\n{/if}"
            "{#if requirements}【要求】\n{requirements}\n{/if}"
            "大纲要求：\n"
            "- 列出章节编号（一、二、三…）和各小节（1.1、1.2…）\n"
            "- 每节标注核心论点（1句话），不只是标题\n"
            "- 标注哪些章节需要实证数据/问卷/案例分析\n"
            "- 最后给出3-5条参考文献方向\n"
            "- 整体结构符合学术规范（引言→文献综述→研究方法→结果分析→结论）"
        ),
        input_schema={"fields": [
            {"name": "topic", "type": "text", "label": "论文题目", "required": True, "placeholder": "例：社交媒体对Z世代消费决策的影响研究"},
            {"name": "paper_type", "type": "select", "label": "论文类型", "default": "本科毕业论文", "options": ["本科毕业论文", "硕士学位论文", "课程论文", "学术期刊投稿"], "required": True},
            {"name": "word_count", "type": "text", "label": "字数要求", "required": False, "placeholder": "例：8000-10000字"},
            {"name": "requirements", "type": "textarea", "label": "导师要求 / 其他说明", "required": False, "placeholder": "例：需要包含问卷调查、要有文献综述章节"},
        ]},
        enabled=True, display_order=30,
        tagline="给定题目 → 生成可执行的论文结构",
        display_metadata={}, is_universal=True, layer=1, version="1.0.0",
    ),
]

CANONICAL_KEYS = {s["skill_key"] for s in SKILLS}

UPSERT_COLS = [
    "scenario_name", "description", "trigger_keywords", "prompt_template",
    "input_schema", "enabled", "display_order", "tagline", "display_metadata",
    "is_universal", "layer", "version",
]


async def main() -> None:
    sf = get_session_factory()

    async with sf() as session:
        # 1. Delete any skill_key not in canonical list (CASCADE handles FK deps)
        existing = await session.execute(select(IndustrySkillModel.skill_key))
        stale_keys = {row[0] for row in existing} - CANONICAL_KEYS
        if stale_keys:
            await session.execute(
                delete(IndustrySkillModel).where(IndustrySkillModel.skill_key.in_(stale_keys))
            )
            print(f"Deleted {len(stale_keys)} stale skill(s): {stale_keys}")

        # 2. Upsert each canonical skill
        for sk in SKILLS:
            result = await session.execute(
                select(IndustrySkillModel).where(IndustrySkillModel.skill_key == sk["skill_key"])
            )
            row = result.scalar_one_or_none()
            if row is None:
                session.add(IndustrySkillModel(**sk))
                print(f"  INSERT {sk['skill_key']}")
            else:
                for col in UPSERT_COLS:
                    setattr(row, col, sk[col])
                print(f"  UPDATE {sk['skill_key']}")

        await session.commit()

    # 3. Verify
    async with sf() as session:
        result = await session.execute(
            select(IndustrySkillModel.skill_key, IndustrySkillModel.scenario_name)
            .order_by(IndustrySkillModel.display_order)
        )
        rows = result.all()
        print(f"\nFinal: {len(rows)} skill(s) in DB")
        for r in rows:
            print(f"  {r[0]:30s} {r[1]}")


if __name__ == "__main__":
    asyncio.run(main())
