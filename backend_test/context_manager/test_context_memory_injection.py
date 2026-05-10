from __future__ import annotations

import asyncio

from helpers import make_context_manager, make_memory_system, make_session_manager


def test_prepare_injects_user_global_and_user_group_core(workspace) -> None:
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
        memory.write_core_memory(
            user_id="u1",
            group_id="law",
            scope="user_group",
            content="In law group, cite statutes first.",
        )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            extra_messages=[{"role": "user", "content": "Explain breach liability."}],
            query="breach liability",
            allow_compaction=False,
        )
        joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
        assert "Always answer in Chinese." in joined
        assert "cite statutes first" in joined

    asyncio.run(run())


def test_prepare_injects_relevant_daily_log_and_domain_case(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)

        session = sessions.create_session("law", "default", "u1")
        memory.write_daily_log(
            "law",
            "default",
            "Recent log: breach liability should be analyzed with damages.",
            user_id="u1",
        )
        memory.write_domain_case(
            group_id="law",
            title="Breach case",
            content="A breach case connects liability with foreseeability and damages.",
        )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            extra_messages=[{"role": "user", "content": "Continue the breach liability discussion."}],
            query="breach liability damages",
            allow_compaction=False,
        )
        joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
        assert "damages" in joined
        assert "Breach case" in joined

    asyncio.run(run())


def test_prepare_skips_memory_injection_when_query_missing(workspace) -> None:
    async def run() -> None:
        context = make_context_manager(workspace)

        prepared = await context.prepare_messages(
            "law",
            "default",
            [{"role": "assistant", "content": "no user query yet"}],
            query=None,
            user_id="u1",
        )

        assert all("核心记忆" not in str(item.get("content", "")) for item in prepared["messages"])
        assert all("相关记忆" not in str(item.get("content", "")) for item in prepared["messages"])

    asyncio.run(run())


def test_prepare_does_not_leak_cross_group_or_cross_user_memory(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)

        session = sessions.create_session("law", "default", "u1")
        memory.write_core_memory(
            user_id="u2",
            group_id=None,
            scope="user_global",
            content="This belongs to another user.",
        )
        memory.write_core_memory(
            user_id="u1",
            group_id="medical",
            scope="user_group",
            content="Medical-only preference.",
        )
        memory.write_daily_log("law", "default", "u2 private log", user_id="u2")
        memory.write_domain_case(
            group_id="medical",
            title="Medical case",
            content="This case belongs to medical group.",
        )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            extra_messages=[{"role": "user", "content": "What should I follow here?"}],
            query="case preference",
            allow_compaction=False,
        )
        joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
        assert "another user" not in joined
        assert "Medical-only" not in joined
        assert "u2 private log" not in joined
        assert "Medical case" not in joined

    asyncio.run(run())
