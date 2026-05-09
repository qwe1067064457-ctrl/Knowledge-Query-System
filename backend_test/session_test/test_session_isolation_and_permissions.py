from __future__ import annotations

import pytest


def test_multi_domain_isolation_keeps_other_group_transcript_empty(
    session_manager,
    make_entry,
) -> None:
    user_id = "u"
    law_session = session_manager.create_session("law", "agent_a", user_id)
    medical_session = session_manager.create_session("medical", "agent_b", user_id)

    session_manager.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=law_session.id,
            group_id="law",
            role="user",
            content="违约责任",
            token_count=5,
        ),
    )

    assert len(session_manager.get_transcript("law", "agent_a", law_session.id)) == 1
    assert session_manager.get_transcript("medical", "agent_b", medical_session.id) == []


def test_cross_group_access_does_not_leak_sessions_or_messages(
    session_manager,
    make_entry,
) -> None:
    user_id = "u"
    law_session = session_manager.create_session("law", "agent_a", user_id)
    session_manager.create_session("medical", "agent_b", user_id)

    session_manager.append_entry(
        "law",
        "agent_a",
        make_entry(
            session_id=law_session.id,
            group_id="law",
            role="user",
            content="合同纠纷",
            token_count=4,
        ),
    )

    assert session_manager.get_transcript("medical", "agent_b", law_session.id) == []
    medical_sessions = session_manager.list_user_sessions("medical", "agent_b", user_id)
    assert {session.group_id for session in medical_sessions} == {"medical"}
    assert law_session.id not in {session.id for session in medical_sessions}


def test_permissions_allow_access_only_via_own_group_and_agent(
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
            content="根据民法典分析如下",
            token_count=8,
        ),
    )

    transcript = session_manager.get_transcript("law", "agent_a", session.id)
    listed = session_manager.list_user_sessions("law", "agent_a", "u")

    assert len(transcript) == 1
    assert listed[0].id == session.id
    assert listed[0].group_id == "law"
    assert listed[0].agent_id == "agent_a"


@pytest.mark.parametrize(
    ("group_id", "agent_id"),
    [
        ("../bad", "agent"),
        ("law", "../bad"),
        ("law/evil", "agent"),
    ],
)
def test_invalid_group_or_agent_segments_raise_value_error(
    session_manager,
    group_id: str,
    agent_id: str,
) -> None:
    with pytest.raises(ValueError):
        session_manager.create_session(group_id, agent_id, "u")


def test_wrong_group_or_agent_cannot_read_session(
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
            role="user",
            content="举证责任",
            token_count=3,
        ),
    )

    assert session_manager.get_session(session.id, "medical", "agent_a") is None
    assert session_manager.get_session(session.id, "law", "agent_b") is None
    assert session_manager.get_transcript("medical", "agent_a", session.id) == []
    assert session_manager.get_transcript("law", "agent_b", session.id) == []
