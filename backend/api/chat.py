from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sse_starlette.sse import EventSourceResponse

from backend.agent.core import AgentCore
from backend.agent.schemas import Message, Role, StreamEventType
from backend.core.auth import get_current_user
from backend.memory.database import get_session_factory
from backend.memory.models import UserModel
from backend.memory.repo import SQLAlchemyConversationRepo
from backend.observability import trace, trace_span
from backend.services.quota_service import check_and_increment
from backend.utils.file_parsers import extract_text

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(
    request: Request,
    message: str = Form(...),
    model: str | None = Form(None),
    conversation_id: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: UserModel = Depends(get_current_user),
):
    session_factory = get_session_factory()
    user_id = current_user.id

    # Quota check — raises 402 if user has exhausted their daily/monthly limit
    async with session_factory() as session:
        await check_and_increment(user_id, session)
        await session.commit()

    async with session_factory() as session:
        repo = SQLAlchemyConversationRepo(session)

        conv = None
        if conversation_id:
            conv = await repo.get_conversation(conversation_id)
        if not conv:
            conv = await repo.create_conversation(user_id=user_id)
            await session.commit()

        conv_id = conv.id

        user_content = message
        has_file = False
        if file and file.filename:
            has_file = True
            try:
                data = await file.read()
                file_text = extract_text(file.filename, data)
                user_content = (
                    f"[Attached file: {file.filename}]\n"
                    f"<file_content>\n{file_text}\n</file_content>\n\n"
                    f"{message}"
                )
            except ValueError as e:
                async def error_stream():
                    yield {"event": "error", "data": json.dumps({"message": str(e)})}
                return EventSourceResponse(error_stream())

        user_msg = Message(role=Role.USER, content=user_content)
        is_first = conv.message_count == 0
        await repo.add_message(conv_id, user_msg, is_pinned=(is_first or has_file))
        await session.commit()

    trace(
        "request_start",
        conv_id=conv_id,
        msg_len=len(message),
        has_file=has_file,
        model=model,
        is_new_conv=is_first,
    )

    agent = AgentCore()
    t_start = time.perf_counter()

    async def event_stream():
        yield {"event": "conversation_id", "data": json.dumps({"conversation_id": conv_id})}

        # Skill intent detection — embedding recall + fine rank (System 2 pipeline)
        from backend.services.skill_intent_matcher import match_intent
        async with session_factory() as intent_session:
            matched_skill = await match_intent(
                message=message,
                user_id=user_id,
                profile=current_user.profile or {},
                session=intent_session,
            )
        if matched_skill:
            trace("skill_match", skill_key=matched_skill["skill_key"], query_preview=message[:60])
            yield {
                "event": "skill_match",
                "data": json.dumps({
                    "skill_key": matched_skill["skill_key"],
                    "scenario_name": matched_skill["scenario_name"],
                }),
            }
            yield {"event": "done", "data": json.dumps({})}
            return

        full_response = ""
        stream_completed = False
        token_count = 0
        assistant_message_id = str(__import__("uuid").uuid4().hex)

        async with session_factory() as ctx_session:
            ctx_repo = SQLAlchemyConversationRepo(ctx_session)
            from backend.memory.manager import MemoryManager
            memory = MemoryManager(ctx_repo)
            async with trace_span("memory.build_context", conv_id=conv_id) as span:
                history = await memory.build_context(conv_id, user_id=user_id)
                span["history_msgs"] = len(history)

        try:
            async for event in agent.run(history=history, model=model):
                if event.event == StreamEventType.TEXT_DELTA:
                    chunk = event.data.get("text", "")
                    full_response += chunk
                    token_count += len(chunk.split())
                if event.event == StreamEventType.DONE:
                    stream_completed = True

                yield {"event": event.event.value, "data": json.dumps(event.data)}

        except asyncio.CancelledError:
            elapsed = round((time.perf_counter() - t_start) * 1000, 1)
            trace("request_cancel", conv_id=conv_id, elapsed_ms=elapsed)
            logger.info("chat stream cancelled (client disconnect) conv=%s", conv_id)
            return
        except Exception:
            logger.exception("Error in chat stream")
            yield {"event": "error", "data": json.dumps({"message": "Internal server error"})}
            return

        if not stream_completed or not full_response:
            logger.debug("Skipping save: stream_completed=%s len=%d", stream_completed, len(full_response))
            return

        elapsed = round((time.perf_counter() - t_start) * 1000, 1)
        trace(
            "request_done",
            conv_id=conv_id,
            elapsed_ms=elapsed,
            response_tokens=token_count,
            response_chars=len(full_response),
        )

        async with session_factory() as save_session:
            save_repo = SQLAlchemyConversationRepo(save_session)
            await save_repo.add_message(
                conv_id,
                Message(role=Role.ASSISTANT, content=full_response),
            )
            await save_session.commit()

        async def _background_memory_tasks():
            try:
                async with session_factory() as bg_session:
                    bg_repo = SQLAlchemyConversationRepo(bg_session)
                    from backend.memory.manager import MemoryManager
                    mgr = MemoryManager(bg_repo)
                    async with trace_span("memory.summarize", conv_id=conv_id):
                        await mgr.maybe_summarize(conv_id)
                    async with trace_span("memory.extract_facts", conv_id=conv_id):
                        await mgr.extract_and_save_facts(conv_id)
                    await bg_session.commit()

                # Phase 4: extract long-term memories into user_memories table
                async with session_factory() as mem_session:
                    from backend.services.memory_extractor import extract_and_save_memories
                    async with trace_span("memory.extract_memories", conv_id=conv_id):
                        await extract_and_save_memories(
                            user_id=user_id,
                            user_input=message,
                            answer=full_response,
                            session=mem_session,
                        )
                    await mem_session.commit()

                # Phase 5: update profile and generate suggestions
                async with session_factory() as p5_session:
                    from backend.services.profile_updater import maybe_update_profile
                    from backend.services.suggestion_generator import generate_and_save_suggestions
                    async with trace_span("profile.update", conv_id=conv_id):
                        await maybe_update_profile(
                            user_id=user_id,
                            user_input=message,
                            session=p5_session,
                        )
                    async with trace_span("suggestions.generate", conv_id=conv_id):
                        await generate_and_save_suggestions(
                            user_id=user_id,
                            message_id=assistant_message_id,
                            user_input=message,
                            answer=full_response,
                            session=p5_session,
                        )
                    await p5_session.commit()

            except Exception:
                logger.exception("Background memory tasks failed")

        asyncio.create_task(_background_memory_tasks())

    return EventSourceResponse(event_stream())
