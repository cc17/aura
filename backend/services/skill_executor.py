"""Skill executor — renders prompt template and calls the main LLM."""

from __future__ import annotations

import logging
import re
import time
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.langchain_bridge import create_chat_model
from backend.memory.models import IndustrySkillModel, SkillExecutionModel
from backend.services.prompt_builder import _profile_snippet
from backend.services.skill_registry import get_skill

logger = logging.getLogger(__name__)


def render_template(template: str, data: dict) -> str:
    """Render a skill prompt template.

    Supports:
    - {variable} — replaced with data[variable] (empty string if missing/falsy)
    - {#if variable}...{/if} — block included only if data[variable] is truthy
    """
    def replace_if(m: re.Match) -> str:
        cond, body = m.group(1), m.group(2)
        return body if data.get(cond) else ""

    result = re.sub(
        r"\{#if (\w+)\}(.*?)\{/if\}",
        replace_if,
        template,
        flags=re.DOTALL,
    )
    for key, value in data.items():
        result = result.replace(f"{{{key}}}", str(value) if value else "")

    # Clean up blank lines left by removed {#if} blocks
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


async def execute_skill_stream(
    skill_key: str,
    input_data: dict,
    user_id: int,
    session: AsyncSession,
    profile: dict | None = None,
) -> AsyncIterator[str]:
    """Execute a skill and yield text chunks.

    Records the execution in skill_executions table.
    """
    skill = get_skill(skill_key)
    if skill is None:
        yield "[Skill not found]"
        return

    # Inject profile snippet for templates that reference it
    render_data = dict(input_data)
    if profile:
        render_data["profile_snippet"] = _profile_snippet(profile)
    else:
        render_data["profile_snippet"] = ""

    prompt = render_template(skill["prompt_template"], render_data)

    # Record execution start
    execution = SkillExecutionModel(
        user_id=user_id,
        skill_id=skill["id"],
        input_data=input_data,
        status="pending",
    )
    session.add(execution)
    await session.flush()
    exec_id = execution.id

    t_start = time.perf_counter()
    full_output = []
    status = "success"

    try:
        llm = create_chat_model()
        from langchain_core.messages import HumanMessage

        async for chunk in llm.astream([HumanMessage(content=prompt)]):
            text = chunk.content if hasattr(chunk, "content") else ""
            if text:
                full_output.append(text)
                yield text

    except Exception:
        logger.exception("Skill execution failed: %s", skill_key)
        status = "failed"
        yield "\n\n[技能执行出错，请重试]"

    finally:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000)
        execution.output_text = "".join(full_output)
        execution.status = status
        execution.duration_ms = elapsed_ms
        await session.flush()
        logger.info(
            "Skill %s executed: status=%s duration=%dms",
            skill_key, status, elapsed_ms,
        )
