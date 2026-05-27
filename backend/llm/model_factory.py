"""
Create chat model instances for different providers.

This module centralizes provider-specific model construction so orchestration
code does not own provider branching logic.
"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from config import get_settings

try:
    from langchain_deepseek import ChatDeepSeek
except ImportError:  # pragma: no cover - optional dependency at runtime
    ChatDeepSeek = None


OPENAI_COMPATIBLE_PROVIDERS = {"openai", "zhipu", "bailian", "minimax"}


def build_chat_model():
    settings = get_settings()

    if settings.llm_provider == "deepseek":
        if ChatDeepSeek is None:
            raise RuntimeError("langchain-deepseek is not installed")
        if not settings.llm_api_key:
            raise RuntimeError("Missing API key for provider deepseek")
        return ChatDeepSeek(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0,
        )

    if settings.llm_provider not in OPENAI_COMPATIBLE_PROVIDERS:
        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

    if not settings.llm_api_key:
        raise RuntimeError(f"Missing API key for provider {settings.llm_provider}")

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0,
    )
