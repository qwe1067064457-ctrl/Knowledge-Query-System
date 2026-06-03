from __future__ import annotations

import asyncio

from observability.emitters.context_emitter import ContextEmitter
from observability.langsmith.client import LangSmithClient
from observability.runtime.run_factory import create_trace_context
from observability.runtime.trace_context_store import activate_trace_context

from conftest import make_context_manager, make_entry, make_memory_system, make_session_manager


def test_context_manager_emits_core_and_retrieved_memory_block_facts(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)
        context.set_observability_emitter(ContextEmitter(LangSmithClient(enabled=False)))

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
        trace_context = create_trace_context(
            session_id=session.id,
            group_id="law",
            user_id="u1",
        )

        with activate_trace_context(trace_context):
            await context.prepare(
                "law",
                "default",
                session.id,
                extra_messages=[{"role": "user", "content": "Continue the breach discussion."}],
                query="breach damages",
                allow_compaction=False,
            )

        assembly_events = [item for item in trace_context.events if item.event_type == "context_assembly_run"]
        assert len(assembly_events) == 1
        assert assembly_events[0].output_summary["core_block_present"] is True
        assert assembly_events[0].output_summary["retrieved_memories_present"] is True

    asyncio.run(run())


def test_context_manager_emits_pre_compaction_extraction_and_compaction_events(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, sessions=sessions, memory=memory)
        context.set_observability_emitter(ContextEmitter(LangSmithClient(enabled=False)))
        context.set_llm_call(lambda prompt: "Compaction summary")

        session = sessions.create_session("law", "default", "u1")
        for entry in (
            make_entry(session.id, "law", "user", "RAW_SLICE_ONLY: archived sessions still accept writes.", token_count=120),
            make_entry(session.id, "law", "assistant", "This answer is intentionally long. " * 40, token_count=120),
            make_entry(session.id, "law", "user", "Recent turn should stay in the live window.", token_count=120),
            make_entry(session.id, "law", "assistant", "Most recent assistant turn should not be summarized away.", token_count=120),
        ):
            sessions.append_entry("law", "default", entry)

        trace_context = create_trace_context(
            session_id=session.id,
            group_id="law",
            user_id="u1",
        )
        with activate_trace_context(trace_context):
            await context.prepare(
                "law",
                "default",
                session.id,
                query="archived sessions",
                soft_threshold_tokens=10,
                keep_recent_tokens=200,
                max_turns=20,
                allow_compaction=True,
            )

        extraction_events = [item for item in trace_context.events if item.event_type == "pre_compaction_extraction_run"]
        compaction_events = [item for item in trace_context.events if item.event_type == "compaction_run"]
        assert len(extraction_events) == 1
        assert extraction_events[0].status == "success"
        assert extraction_events[0].output_summary["extraction_key"]
        assert len(compaction_events) == 1
        assert compaction_events[0].status == "success"
        assert compaction_events[0].output_summary["summary_generated"] is True

    asyncio.run(run())


def test_prepare_messages_without_compaction_does_not_emit_pre_compaction_extraction(workspace) -> None:
    async def run() -> None:
        memory = make_memory_system(workspace)
        context = make_context_manager(workspace, memory=memory)
        context.set_observability_emitter(ContextEmitter(LangSmithClient(enabled=False)))
        trace_context = create_trace_context(
            session_id="ad_hoc",
            group_id="law",
            user_id="u1",
        )

        with activate_trace_context(trace_context):
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
        assert [item for item in trace_context.events if item.event_type == "pre_compaction_extraction_run"] == []

    asyncio.run(run())
