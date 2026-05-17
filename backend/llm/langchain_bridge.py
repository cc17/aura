"""Bridge between LiteLLM (doubao models) and LangChain's BaseChatModel interface."""

from __future__ import annotations

from typing import Any

from langchain_community.chat_models import ChatLiteLLM

from backend.config import settings


def create_chat_model(model: str | None = None, **kwargs: Any) -> ChatLiteLLM:
    """Create a ChatLiteLLM instance configured for the Ark (doubao) API.

    This wraps our existing LiteLLM setup so LangGraph agents can use it
    as a standard LangChain BaseChatModel.
    """
    return ChatLiteLLM(
        model=model or settings.default_model,
        api_key=settings.ark_api_key,
        api_base=settings.ark_api_base,
        streaming=True,
        **kwargs,
    )
