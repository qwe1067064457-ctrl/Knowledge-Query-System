from __future__ import annotations

import asyncio

from helpers import make_context_manager


def test_plan_context_budget_returns_unused_tokens_to_recent_turns_first(workspace) -> None:
    context = make_context_manager(workspace)
    context.config.total_tokens = 1000
    context.config.core_reserved_tokens = 300
    context.config.core_max_tokens = 600
    context.config.retrieved_target_tokens = 300
    context.config.retrieved_max_tokens = 500
    context.config.recent_turns_target_tokens = 200
    context.config.recent_turns_max_tokens = 700
    context.config.tool_results_target_tokens = 100
    context.config.tool_results_max_tokens = 200

    plan = context._plan_context_budget(
        [
            {"role": "system", "content": "x" * 200, "_context_block": "core_memory"},
            {"role": "system", "content": "x" * 400, "_context_block": "retrieved_memory"},
            {"role": "user", "content": "x" * 1600},
            {"role": "assistant", "content": "x" * 1600},
        ]
    )

    assert plan["allocation"]["recent_turns"] > context.config.recent_turns_target_tokens
    assert plan["allocation"]["recent_turns"] >= plan["allocation"]["retrieved_memories"]
    assert plan["remaining"] >= 0


def test_assemble_context_preserves_core_under_pressure(workspace) -> None:
    context = make_context_manager(workspace)
    context.config.total_tokens = 400
    context.config.soft_threshold_tokens = 400
    context.config.core_reserved_tokens = 120
    context.config.core_max_tokens = 120
    context.config.retrieved_target_tokens = 50
    context.config.retrieved_max_tokens = 50
    context.config.recent_turns_target_tokens = 120
    context.config.recent_turns_max_tokens = 120
    context.config.tool_results_target_tokens = 20
    context.config.tool_results_max_tokens = 20

    prepared, _, budget = context._assemble_context(
        [
            {"role": "system", "content": "CORE " * 30, "_context_block": "core_memory"},
            {"role": "user", "content": "recent question " * 20},
            {"role": "assistant", "content": "recent answer " * 20},
            {"role": "tool", "content": "tool body " * 200},
        ]
    )

    joined = "\n".join(str(item.get("content", "")) for item in prepared)
    assert "CORE" in joined
    assert budget["blocks"]["core"] > 0


def test_assemble_context_trims_tool_results_before_recent_turns(workspace) -> None:
    context = make_context_manager(workspace)
    context.config.total_tokens = 350
    context.config.soft_threshold_tokens = 350
    context.config.recent_turns_target_tokens = 180
    context.config.recent_turns_max_tokens = 220
    context.config.tool_results_target_tokens = 20
    context.config.tool_results_max_tokens = 20

    prepared, _, budget = context._assemble_context(
        [
            {"role": "user", "content": "recent question " * 25},
            {"role": "assistant", "content": "recent answer " * 25},
            {"role": "tool", "content": "tool details " * 300},
        ]
    )

    roles_to_content = {item["role"]: str(item.get("content", "")) for item in prepared}
    assert "recent question" in roles_to_content["user"]
    assert roles_to_content["tool"] == "[tool result omitted due to budget]" or roles_to_content["tool"].endswith("...[truncated]")
    assert budget["blocks"]["recent_turns"] >= budget["blocks"]["tool_results"]


def test_prepare_messages_returns_budget_metadata(workspace) -> None:
    async def run() -> None:
        context = make_context_manager(workspace)
        prepared = await context.prepare_messages(
            "law",
            "default",
            [
                {"role": "user", "content": "question " * 10},
                {"role": "assistant", "content": "answer " * 10},
            ],
            query="question",
            user_id="u1",
        )

        assert "budget" in prepared
        assert prepared["budget"]["total"] > 0
        assert prepared["budget"]["used"] > 0
        assert "blocks" in prepared["budget"]

    asyncio.run(run())
