from __future__ import annotations

import asyncio

from helpers import make_context_manager, make_entry, make_session_manager


def test_normalize_transcript_discards_invalid_leading_non_user_messages(workspace) -> None:
    context = make_context_manager(workspace)

    normalized = context._normalize_transcript(
        [
            {"role": "assistant", "content": "orphan answer"},
            {"role": "tool", "content": "orphan tool"},
            {"role": "system", "content": "keep me"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
    )

    assert [item["role"] for item in normalized] == ["system", "user", "assistant"]
    assert normalized[0]["content"] == "keep me"


def test_limit_history_turns_keeps_complete_recent_turns(workspace) -> None:
    context = make_context_manager(workspace)
    context.config.max_turns = 2

    limited = context._limit_history_turns(
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "tool", "content": "t1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
        ]
    )

    assert [item["content"] for item in limited] == ["system", "q2", "a2", "q3", "a3"]


def test_limit_history_turns_does_not_leave_orphan_assistant_message(workspace) -> None:
    context = make_context_manager(workspace)
    context.config.max_turns = 1

    limited = context._limit_history_turns(
        [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "new question"},
            {"role": "assistant", "content": "new answer"},
            {"role": "tool", "content": "new tool result"},
        ]
    )

    assert [item["role"] for item in limited] == ["user", "assistant", "tool"]
    assert limited[0]["content"] == "new question"


def test_prepare_preserves_compaction_boundary_and_recent_history(workspace) -> None:
    async def run() -> None:
        sessions = make_session_manager(workspace)
        context = make_context_manager(workspace, sessions=sessions)

        session = sessions.create_session("law", "default", "u1")
        sessions.append_entry("law", "default", make_entry(session.id, "law", "user", "very old question"))
        sessions.append_entry(
            "law",
            "default",
            make_entry(session.id, "law", "system", "older summary", entry_type="compaction"),
        )
        sessions.append_entry("law", "default", make_entry(session.id, "law", "assistant", "fresh answer"))

        prepared = await context.prepare(
            "law",
            "default",
            session.id,
            extra_messages=[{"role": "user", "content": "continue"}],
            allow_compaction=False,
        )
        joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
        assert "older summary" in joined
        assert "very old question" not in joined
        assert "continue" in joined

    asyncio.run(run())
