from __future__ import annotations

from context.session import DEFAULT_AGENT, SessionManager, SessionWorkingMemory


def test_session_manager_round_trips_working_memory(session_manager: SessionManager) -> None:
    session = session_manager.create_session("law", DEFAULT_AGENT, "user_a")
    memory = SessionWorkingMemory(
        current_goal="完成试用期依据核验",
        rewritten_query="一年期劳动合同试用期上限",
        unresolved_questions=["是否存在例外"],
        key_intermediate_conclusions=["已经拿到第19条证据"],
        supporting_evidence_refs=["evidence_1"],
        next_step_hint="检查历史案例",
    )

    updated = session_manager.update_working_memory(session.id, "law", DEFAULT_AGENT, memory)
    loaded = session_manager.get_working_memory(session.id, "law", DEFAULT_AGENT)

    assert updated is not None
    assert loaded is not None
    assert loaded.current_goal == "完成试用期依据核验"
    assert loaded.supporting_evidence_refs == ["evidence_1"]
    assert "focus_question_object_id" not in loaded.to_dict()


def test_session_manager_returns_none_when_working_memory_absent(session_manager: SessionManager) -> None:
    session = session_manager.create_session("law", DEFAULT_AGENT, "user_a")

    loaded = session_manager.get_working_memory(session.id, "law", DEFAULT_AGENT)

    assert loaded is None
