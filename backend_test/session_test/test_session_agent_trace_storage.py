from __future__ import annotations

from api.session_views import build_session_record


def test_agent_trace_is_persisted_separately_from_transcript(session_manager, make_entry) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    assistant_entry = make_entry(
        session_id=session.id,
        group_id="law",
        role="assistant",
        content="这是回答。",
        token_count=5,
    )
    session_manager.append_entry("law", "agent_a", assistant_entry)
    session_manager.append_agent_trace(
        "law",
        "agent_a",
        session.id,
        {
            "entry_id": assistant_entry.id,
            "session_id": session.id,
            "intent_trace": {"input": {"query": "试用期依据"}},
            "workflow_trace": {"plan": {"route": "qa"}},
            "execution_events": [{"stage": "route_payload_ready"}],
        },
    )

    transcript_path = (
        session_manager.base_storage_path
        / "groups"
        / "law"
        / "users"
        / "u"
        / "sessions"
        / "transcripts"
        / f"{session.id}.jsonl"
    )
    trace_path = (
        session_manager.base_storage_path
        / "groups"
        / "law"
        / "users"
        / "u"
        / "sessions"
        / "agent_traces"
        / f"{session.id}.jsonl"
    )

    transcript_text = transcript_path.read_text(encoding="utf-8")
    trace_text = trace_path.read_text(encoding="utf-8")

    assert "intent_trace" not in transcript_text
    assert "workflow_trace" not in transcript_text
    assert "execution_events" not in transcript_text
    assert "intent_trace" in trace_text
    assert "workflow_trace" in trace_text
    assert "execution_events" in trace_text


def test_session_record_rehydrates_trace_fields_from_agent_trace_file(session_manager, make_entry) -> None:
    session = session_manager.create_session("law", "agent_a", "u")
    user_entry = make_entry(
        session_id=session.id,
        group_id="law",
        role="user",
        content="试用期依据是什么",
        token_count=4,
    )
    assistant_entry = make_entry(
        session_id=session.id,
        group_id="law",
        role="assistant",
        content="依据劳动合同法第19条。",
        token_count=6,
    )

    session_manager.append_entry("law", "agent_a", user_entry)
    session_manager.append_entry("law", "agent_a", assistant_entry)
    session_manager.append_agent_trace(
        "law",
        "agent_a",
        session.id,
        {
            "entry_id": assistant_entry.id,
            "session_id": session.id,
            "intent_trace": {"resolved": {"main_intent": "qa"}},
            "workflow_trace": {"plan": {"route": "qa", "handling_mode": "normal"}},
            "execution_events": [{"stage": "route_payload_ready", "payload": {"action": "respond"}}],
        },
    )

    record = build_session_record(session_manager, session.id, group_id="law", agent_id="agent_a")

    assert len(record["messages"]) == 2
    assert "intent_trace" not in record["messages"][0]
    assert record["messages"][1]["intent_trace"]["resolved"]["main_intent"] == "qa"
    assert record["messages"][1]["workflow_trace"]["plan"]["route"] == "qa"
    assert record["messages"][1]["execution_events"][0]["stage"] == "route_payload_ready"
