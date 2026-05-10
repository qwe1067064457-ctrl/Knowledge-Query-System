from __future__ import annotations

from context.context_manager import ContextManager
from context.context_policy import ContextPolicyLoader
from graph.prompt_builder import build_system_prompt

from helpers import (
    make_context_manager,
    make_memory_system,
    make_session_manager,
    write_context_policy,
    write_system_prompt,
)


def test_context_policy_loader_falls_back_to_default_values(workspace) -> None:
    loader = ContextPolicyLoader(workspace / "context" / "context_policy.json")
    policy = loader.load_policy()

    assert policy["history"]["max_recent_turns"] == 8
    assert policy["budget"]["total_tokens"] == 6000
    assert policy["compaction"]["enabled"] is True
    assert policy["prompt"]["system_prompt_path"] == "prompts/system_prompt.md"


def test_context_policy_loader_applies_local_overrides(workspace) -> None:
    write_context_policy(
        workspace,
        {
            "history": {"max_recent_turns": 3},
            "budget": {"tool_results": {"max_chars_per_message": 1200}},
            "prompt": {"system_prompt_path": "prompts/custom.md"},
        },
    )
    loader = ContextPolicyLoader(workspace / "context" / "context_policy.json")
    policy = loader.load_policy()

    assert policy["history"]["max_recent_turns"] == 3
    assert policy["budget"]["total_tokens"] == 6000
    assert policy["budget"]["tool_results"]["max_chars_per_message"] == 1200
    assert policy["prompt"]["system_prompt_path"] == "prompts/custom.md"


def test_context_manager_reload_policy_updates_runtime_config(workspace) -> None:
    sessions = make_session_manager(workspace)
    memory = make_memory_system(workspace)
    context = ContextManager(sessions, memory)

    assert context.config.max_turns == 8

    write_context_policy(
        workspace,
        {
            "history": {"max_recent_turns": 5},
            "memory": {"top_k": 2},
            "compaction": {"keep_recent_tokens": 777},
        },
    )
    context.reload_policy()

    assert context.config.max_turns == 5
    assert context.config.memory_top_k == 2
    assert context.config.keep_recent_tokens == 777


def test_build_system_prompt_reads_configured_prompt_file(workspace) -> None:
    write_context_policy(
        workspace,
        {
            "prompt": {"system_prompt_path": "prompts/custom_system.md"},
        },
    )
    write_system_prompt(workspace, "Custom system prompt body.", "prompts/custom_system.md")

    prompt = build_system_prompt(workspace, rag_mode=False)

    assert "Custom system prompt body." in prompt
    assert "Runtime Override" in prompt


def test_build_system_prompt_falls_back_when_prompt_missing(workspace) -> None:
    write_context_policy(
        workspace,
        {
            "prompt": {"system_prompt_path": "prompts/missing.md"},
        },
    )

    prompt = build_system_prompt(workspace, rag_mode=False)

    assert "核心问答助手" in prompt
    assert "不要编造事实" in prompt
