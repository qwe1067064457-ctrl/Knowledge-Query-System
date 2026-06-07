from __future__ import annotations

from context.session import DEFAULT_AGENT, SessionManager, SessionWorkingMemory, WorkingMemoryEntry, WorkingMemoryHead


def test_session_manager_round_trips_working_memory(session_manager: SessionManager) -> None:
    session = session_manager.create_session("law", DEFAULT_AGENT, "user_a")
    memory = SessionWorkingMemory(
        entries=[
            WorkingMemoryEntry(
                entry_id="turn_1:focus_task",
                entry_type="focus_task",
                turn_id="turn_1",
                source_kind="user_query",
                source_ref="turn_1:user",
                content="完成试用期依据核验",
                confidence="high",
            ),
            WorkingMemoryEntry(
                entry_id="turn_1:resolved_query",
                entry_type="resolved_query",
                turn_id="turn_1",
                source_kind="binding",
                source_ref="turn_1:binding",
                content="一年期劳动合同试用期上限",
                confidence="high",
            ),
        ],
        head=WorkingMemoryHead(
            active_entry_ids=["turn_1:focus_task", "turn_1:resolved_query"],
            current_focus_task_ids=["turn_1:focus_task"],
            latest_resolved_query_id="turn_1:resolved_query",
        ),
    )

    updated = session_manager.update_working_memory(session.id, "law", DEFAULT_AGENT, memory)
    loaded = session_manager.get_working_memory(session.id, "law", DEFAULT_AGENT)

    assert updated is not None
    assert loaded is not None
    assert len(loaded.entries) == 2
    assert loaded.head.current_focus_task_ids == ["turn_1:focus_task"]
    assert loaded.head.latest_resolved_query_id == "turn_1:resolved_query"
    assert loaded.active_entries()[0].entry_type == "focus_task"


def test_session_manager_returns_none_when_working_memory_absent(session_manager: SessionManager) -> None:
    session = session_manager.create_session("law", DEFAULT_AGENT, "user_a")

    loaded = session_manager.get_working_memory(session.id, "law", DEFAULT_AGENT)

    assert loaded is None
