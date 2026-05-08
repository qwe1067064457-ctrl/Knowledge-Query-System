from __future__ import annotations

import pytest


def test_append_entry_persists_message_fields_and_order(
    session_manager,
    make_entry,
) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    first = make_entry(
        session_id=session.id,
        group_id="law",
        role="user",
        content="违约责任",
        token_count=5,
    )
    second = make_entry(
        session_id=session.id,
        group_id="law",
        role="assistant",
        content="请补充合同约定",
        token_count=7,
    )

    session_manager.append_entry("law", "agent_a", first)
    session_manager.append_entry("law", "agent_a", second)

    transcript = session_manager.get_transcript("law", "agent_a", session.id)

    assert [item.id for item in transcript] == [first.id, second.id]
    assert transcript[0].role == "user"
    assert transcript[0].content == "违约责任"
    assert transcript[0].token_count == 5
    assert transcript[0].group_id == "law"
    assert transcript[0].session_id == session.id
    assert transcript[1].role == "assistant"
    assert transcript[1].content == "请补充合同约定"


def test_append_entry_rejects_group_mismatch_and_missing_transcript_is_empty(
    session_manager,
    make_entry,
) -> None:
    session = session_manager.create_session("law", "agent_a", "u")

    wrong_group_entry = make_entry(
        session_id=session.id,
        group_id="medical",
        role="user",
        content="错误组",
        token_count=2,
    )

    with pytest.raises(ValueError):
        session_manager.append_entry("law", "agent_a", wrong_group_entry)

    assert session_manager.get_transcript("law", "agent_a", "missing-session") == []


def test_turn_count_and_total_tokens_follow_user_messages_only(
    session_manager,
    make_entry,
) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    entries = [
        make_entry(
            session_id=session.id,
            group_id="law",
            role="user",
            content="问题一",
            token_count=5,
        ),
        make_entry(
            session_id=session.id,
            group_id="law",
            role="assistant",
            content="回答一",
            token_count=7,
        ),
        make_entry(
            session_id=session.id,
            group_id="law",
            role="tool",
            content="检索结果",
            token_count=11,
        ),
        make_entry(
            session_id=session.id,
            group_id="law",
            role="user",
            content="问题二",
            token_count=13,
        ),
        make_entry(
            session_id=session.id,
            group_id="law",
            role="system",
            content="系统提示",
            token_count=17,
        ),
    ]

    for entry in entries:
        session_manager.append_entry("law", "agent_a", entry)

    stored = session_manager.get_session(session.id, "law", "agent_a")
    assert stored is not None
    assert stored.turn_count == 2
    assert stored.total_tokens == 53


def test_non_user_messages_do_not_increment_turn_count_and_none_tokens_do_not_add(
    session_manager,
    make_entry,
) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    session_manager.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=session.id,
            group_id="law",
            role="assistant",
            content="仅助手回复",
            token_count=9,
        ),
    )
    session_manager.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=session.id,
            group_id="law",
            role="tool",
            content="仅工具输出",
            token_count=None,
        ),
    )

    stored = session_manager.get_session(session.id, "law", "agent_a")
    assert stored is not None
    assert stored.turn_count == 0
    assert stored.total_tokens == 9
