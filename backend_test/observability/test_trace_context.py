from __future__ import annotations

from datetime import datetime

from observability.emitters.workflow_emitter import WorkflowEmitter
from observability.langsmith.client import LangSmithClient
from observability.runtime.run_factory import create_trace_context
from observability.runtime.trace_context_store import activate_trace_context


def test_trace_context_records_events_inside_active_scope() -> None:
    trace_context = create_trace_context(
        session_id="session_1",
        group_id="law",
        user_id="u1",
    )
    emitter = WorkflowEmitter(LangSmithClient(enabled=False))

    with activate_trace_context(trace_context):
        event = emitter.emit_workflow_run(
            started_at=datetime.now(),
            input_summary={"message": "你好"},
            output_summary={"status": "ready"},
            metadata={"workflow_name": "qa"},
        )

    assert event is not None
    assert trace_context.trace_id == event.trace_id
    assert trace_context.session_id == "session_1"
    assert len(trace_context.events) == 1
    assert trace_context.events[0].event_type == "workflow_run"


def test_emitter_without_active_trace_context_is_safe_noop() -> None:
    emitter = WorkflowEmitter(LangSmithClient(enabled=False))

    event = emitter.emit_workflow_run(
        started_at=datetime.now(),
        input_summary={"message": "你好"},
        output_summary={"status": "ready"},
        metadata={"workflow_name": "qa"},
    )

    assert event is None
