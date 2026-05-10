from __future__ import annotations

import asyncio

from helpers import make_context_manager, make_entry, make_memory_system, make_session_manager


def test_prepare_does_not_compact_under_threshold(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        context = make_context_manager(workspace, sessions=sessions)

        session = sessions.create_session("law", "default", "u1")
        sessions.append_entry("law", "default", make_entry(session.id, "law", "user", "short question", token_count=5))
        sessions.append_entry("law", "default", make_entry(session.id, "law", "assistant", "short answer", token_count=5))

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            allow_compaction=True,
        )

        assert prepared["needs_compaction"] is False
        assert prepared["compaction"] is None

    asyncio.run(run())


def test_prepare_triggers_compaction_and_flush_before_summary_writeback(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)

        def fake_llm(prompt: str) -> str:
            if "提取对你主人重要的信息" in prompt:
                return "- Record: archived sessions still accept writes."
            return "Compaction summary"

        context.set_llm_call(fake_llm)
        session = sessions.create_session("law", "default", "u1")
        for index in range(6):
            role = "user" if index % 2 == 0 else "assistant"
            sessions.append_entry(
                "law",
                "default",
                make_entry(
                    session.id,
                    "law",
                    role,
                    "Very long context body " * 40,
                    token_count=120,
                ),
            )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            max_turns=20,
            soft_threshold_tokens=10,
            keep_recent_tokens=5,
            allow_compaction=True,
        )

        transcript = sessions.get_transcript("law", "default", session.id)
        compactions = [item for item in transcript if item.entry_type == "compaction"]
        recent_logs = memory.get_recent_memories("law", "default", days=1, user_id="u1")

        assert len(compactions) == 1
        assert recent_logs
        assert "archived sessions still accept writes" in recent_logs[0].content
        assert "Compaction summary" in compactions[0].content
        assert "compaction" in prepared

    asyncio.run(run())
