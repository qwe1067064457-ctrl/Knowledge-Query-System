from __future__ import annotations

import asyncio

from helpers import make_context_manager, make_memory_system, make_session_manager


def test_prepare_exposes_memory_retrieval_summary(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)

        session = sessions.create_session("law", "default", "u1")
        memory.write_core_memory(
            user_id="u1",
            group_id=None,
            scope="user_global",
            content="Always answer in Chinese.",
        )
        memory.write_daily_log(
            "law",
            "default",
            "Recent log: discuss breach liability with damages.",
            user_id="u1",
        )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            extra_messages=[{"role": "user", "content": "Continue the breach discussion."}],
            query="breach damages",
            allow_compaction=False,
        )

        summary = prepared["memory_retrieval"]
        assert summary["performed"] is True
        assert summary["owner"] == "context"
        assert summary["core_block_present"] is True
        assert summary["retrieved_memories_present"] is True
        assert summary["retrieved_memory_count"] >= 1

    asyncio.run(run())


def test_prepare_messages_without_query_returns_empty_memory_retrieval_summary(workspace) -> None:
    async def run() -> None:
        context = make_context_manager(workspace)

        prepared = await context.prepare_messages(
            "law",
            "default",
            [{"role": "assistant", "content": "no user query yet"}],
            query=None,
            user_id="u1",
        )

        summary = prepared["memory_retrieval"]
        assert summary["performed"] is False
        assert summary["retrieved_memory_count"] == 0
        assert summary["results"] == []

    asyncio.run(run())
