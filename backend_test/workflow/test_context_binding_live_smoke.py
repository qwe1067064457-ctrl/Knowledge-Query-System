from __future__ import annotations

from pathlib import Path

import pytest

from config import get_settings
from llm.model_factory import build_chat_model
from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryHead
from memory_system.session_working_memory.writer import SessionWorkingMemoryWriter
from workflow.powers.context_binding_power import ContextBindingPower


def stringify_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content or "")


def _has_live_llm_key() -> bool:
    settings = get_settings()
    return bool(settings.llm_api_key)


def _live_llm_call(prompt: str) -> str:
    response = build_chat_model().invoke([{"role": "user", "content": prompt}])
    return stringify_content(getattr(response, "content", "")).strip()


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "backend"


def _memory_from_entries(entries):
    return SessionWorkingMemory(
        entries=list(entries),
        head=WorkingMemoryHead(active_entry_ids=[entry.entry_id for entry in entries]),
    )


pytestmark = pytest.mark.skipif(
    not _has_live_llm_key(),
    reason="live llm smoke test requires configured LLM_API_KEY/ZHIPU_API_KEY",
)


def test_live_llm_context_binding_followup_with_working_memory_writer() -> None:
    writer = SessionWorkingMemoryWriter()
    previous_turn_entries = writer.build_entries_from_turn(
        turn_id="turn_prev",
        user_query="现在总结一下 context binding 的剩余问题。",
        answer_text=(
            "第一点：当前结论是 ChallengePower 还没完全统一进 Context Binding V2 contract。"
            "第二点：当前结论是 working memory writer 仍然偏粗。"
            "第三点：当前结论是 multi_target 规则对都仍然偏敏感。"
        ),
        current_goal="梳理 context binding 当前剩余问题",
        review_result={"status": "active", "summary": "当前仍需观察 challenge evidence coverage。"},
    )
    memory = _memory_from_entries(previous_turn_entries)
    power = ContextBindingPower()

    result = power.bind(
        "为什么说 context binding 这条线还没完全收住？",
        [],
        working_memory=memory,
        recent_messages=[
            {"role": "user", "content": "现在总结一下 context binding 的剩余问题。"},
            {
                "role": "assistant",
                "content": (
                    "第一点：当前结论是 ChallengePower 还没完全统一进 Context Binding V2 contract。"
                    "第二点：当前结论是 working memory writer 仍然偏粗。"
                    "第三点：当前结论是 multi_target 规则对都仍然偏敏感。"
                ),
            },
        ],
        llm_call=_live_llm_call,
        base_dir=_backend_dir(),
        rewrite_query=True,
    )

    assert result.binding_snapshot["candidate_pool_size"] >= 1
    assert result.binding_snapshot["relevant_set_size"] >= 2
    assert result.matched_by in {"llm_resolution", "fallback"}
    if result.matched_by == "llm_resolution":
        assert result.resolved_target_ids
        assert result.rewritten_query
        assert result.fallback_type is None
    else:
        assert result.fallback_type == "needs_clarification"
        assert isinstance(result.reason, str)
        assert result.reason


def test_live_llm_context_binding_challenge_with_working_memory_writer() -> None:
    writer = SessionWorkingMemoryWriter()
    previous_turn_entries = writer.build_entries_from_turn(
        turn_id="turn_prev",
        user_query="先回顾 challenge 这条线。",
        answer_text=(
            "第一点：当前结论是 ChallengePower 还没完全统一进 Context Binding V2 contract。"
            "第二点：当前结论是更大的不确定性在 evidence coverage。"
            "第三点：当前结论是 relevant set 仍然更偏规则第一版。"
        ),
        current_goal="回顾 challenge 线的状态",
        review_result={"status": "active", "summary": "evidence coverage 仍需继续观察。"},
    )
    memory = _memory_from_entries(previous_turn_entries)
    power = ContextBindingPower()

    result = power.bind(
        "为什么说 challenge 这条线现在更大的不确定性在 evidence coverage？",
        [],
        working_memory=memory,
        recent_messages=[
            {"role": "user", "content": "先回顾 challenge 这条线。"},
            {
                "role": "assistant",
                "content": (
                    "第一点：当前结论是 ChallengePower 还没完全统一进 Context Binding V2 contract。"
                    "第二点：当前结论是更大的不确定性在 evidence coverage。"
                    "第三点：当前结论是 relevant set 仍然更偏规则第一版。"
                ),
            },
        ],
        llm_call=_live_llm_call,
        base_dir=_backend_dir(),
        rewrite_query=True,
    )

    assert result.binding_snapshot["candidate_pool_size"] >= 1
    assert result.binding_snapshot["relevant_set_size"] >= 2
    assert result.matched_by in {"llm_resolution", "fallback"}
    if result.matched_by == "llm_resolution":
        assert result.resolved_target_ids
    else:
        assert result.fallback_type == "needs_clarification"
        assert isinstance(result.reason, str)
        assert result.reason
