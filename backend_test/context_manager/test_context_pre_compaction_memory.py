from __future__ import annotations

import asyncio

from context.assembly.context_manager import _PRE_COMPACTION_EXTRACTOR_VERSION, _PRE_COMPACTION_STATE_KEY
from helpers import make_context_manager, make_entry, make_memory_system, make_session_manager


def test_prepare_injects_core_and_retrieved_memories_as_separate_blocks(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)

        session = sessions.create_session("law", "default", "u1")
        memory.write_core_memory(
            user_id="u1",
            group_id=None,
            scope="user_global",
            content="ALWAYS answer in Chinese.",
        )
        memory.write_daily_log(
            "law",
            "default",
            "Recent log: discuss breach liability with damages.",
            user_id="u1",
        )
        memory.write_domain_case(
            group_id="law",
            user_id="u1",
            title="Breach case",
            content="A breach case ties liability to damages.",
        )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            extra_messages=[{"role": "user", "content": "Continue the breach discussion."}],
            query="breach damages",
            allow_compaction=False,
        )

        system_messages = [item for item in prepared["messages"] if item.get("role") == "system"]
        assert len(system_messages) >= 2
        assert system_messages[0]["content"].startswith("[Core memory]")
        assert "ALWAYS answer in Chinese." in system_messages[0]["content"]
        assert system_messages[1]["content"].startswith("[Memory context]")
        assert "Recent log" in system_messages[1]["content"]
        assert "Breach case" in system_messages[1]["content"]
        assert "ALWAYS answer in Chinese." not in system_messages[1]["content"]

    asyncio.run(run())


def test_prepare_messages_without_compaction_does_not_flush_long_term_memory(workspace) -> None:
    async def run() -> None:
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, memory=memory)

        prepared = await context.prepare_messages(
            "law",
            "default",
            [
                {"role": "user", "content": "ALWAYS answer in Chinese."},
                {"role": "assistant", "content": "Very long context body " * 60},
            ],
            query="Chinese output",
            user_id="u1",
            soft_threshold_tokens=10,
        )

        assert prepared["needs_compaction"] is True
        assert memory.get_recent_memories("law", "default", days=1, user_id="u1") == []
        assert memory.get_core_memories(user_id="u1", group_id="law") == []

    asyncio.run(run())


def test_prepare_compaction_flushes_raw_slice_before_summary_without_runtime_memory_pollution(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)
        context.set_llm_call(lambda prompt: "Compaction summary")

        session = sessions.create_session("law", "default", "u1")
        memory.write_daily_log(
            "law",
            "default",
            "INJECTED_MEMORY_ONLY should never appear in a new compaction checkpoint.",
            user_id="u1",
        )

        entries = [
            make_entry(
                session.id,
                "law",
                "user",
                "RAW_SLICE_ONLY: archived sessions still accept writes.",
                token_count=120,
            ),
            make_entry(
                session.id,
                "law",
                "assistant",
                "This answer is intentionally long. " * 40,
                token_count=120,
            ),
            make_entry(
                session.id,
                "law",
                "user",
                "Recent turn should stay in the live window.",
                token_count=120,
            ),
            make_entry(
                session.id,
                "law",
                "assistant",
                "Most recent assistant turn should not be summarized away.",
                token_count=120,
            ),
        ]
        for entry in entries:
            sessions.append_entry("law", "default", entry)

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            query="INJECTED_MEMORY_ONLY archived sessions",
            soft_threshold_tokens=10,
            keep_recent_tokens=200,
            max_turns=20,
            allow_compaction=True,
        )

        logs = [
            item
            for item in memory.get_recent_memories("law", "default", days=1, user_id="u1")
            if item.source_session_id == session.id
        ]
        assert logs
        assert any("RAW_SLICE_ONLY" in item.content for item in logs)
        assert all("INJECTED_MEMORY_ONLY" not in item.content for item in logs)
        assert all("[Memory context]" not in item.content for item in logs)
        transcript = sessions.get_transcript("law", "default", session.id)
        assert any(item.entry_type == "compaction" for item in transcript)
        assert "compaction" in prepared

    asyncio.run(run())


def test_prepare_compaction_skips_duplicate_slice_extraction_via_session_metadata(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)
        context.set_llm_call(lambda prompt: "Compaction summary")

        session = sessions.create_session("law", "default", "u1")
        entries = [
            make_entry(session.id, "law", "user", "ALWAYS answer in Chinese.", token_count=120),
            make_entry(session.id, "law", "assistant", "Long answer body " * 40, token_count=120),
            make_entry(session.id, "law", "user", "Keep this latest user turn.", token_count=120),
        ]
        for entry in entries:
            sessions.append_entry("law", "default", entry)

        extraction_key = ":".join(
            (
                session.id,
                entries[0].id,
                entries[1].id,
                _PRE_COMPACTION_EXTRACTOR_VERSION,
            )
        )
        sessions.update_session_metadata(
            session.id,
            "law",
            "default",
            {
                _PRE_COMPACTION_STATE_KEY: {
                    extraction_key: {
                        "slice_start_entry_id": entries[0].id,
                        "slice_end_entry_id": entries[1].id,
                        "extractor_version": _PRE_COMPACTION_EXTRACTOR_VERSION,
                        "status": "success",
                        "processed_at": "2026-06-03T00:00:00",
                    }
                }
            },
        )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            soft_threshold_tokens=10,
            keep_recent_tokens=150,
            max_turns=20,
            allow_compaction=True,
        )

        assert memory.get_recent_memories("law", "default", days=1, user_id="u1") == []
        assert memory.get_core_memories(user_id="u1", group_id="law") == []
        transcript = sessions.get_transcript("law", "default", session.id)
        assert any(item.entry_type == "compaction" for item in transcript)
        assert "compaction" in prepared

    asyncio.run(run())


def test_prepare_compaction_failure_keeps_original_context_when_extraction_raises(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)
        context.set_llm_call(lambda prompt: "Compaction summary")

        async def failing_flush(*args, **kwargs):
            raise RuntimeError("flush boom")

        memory.flush_from_context = failing_flush

        session = sessions.create_session("law", "default", "u1")
        for index in range(4):
            sessions.append_entry(
                "law",
                "default",
                make_entry(
                    session.id,
                    "law",
                    "user" if index % 2 == 0 else "assistant",
                    "Very long context body " * 40,
                    token_count=120,
                ),
            )

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            soft_threshold_tokens=10,
            keep_recent_tokens=150,
            max_turns=20,
            allow_compaction=True,
        )

        transcript = sessions.get_transcript("law", "default", session.id)
        assert not any(item.entry_type == "compaction" for item in transcript)
        assert prepared["compaction"]["success"] is False
        assert "memory flush failed" in prepared["compaction"]["reason"]

    asyncio.run(run())
