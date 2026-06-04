from __future__ import annotations

from datetime import datetime

from intent import classify_intent
from observability.emitters.intent_emitter import IntentEmitter
from observability.langsmith.client import LangSmithClient
from observability.langsmith.serializers import summarize_intent_analysis
from observability.runtime.run_factory import create_trace_context
from observability.runtime.trace_context_store import activate_trace_context


def test_intent_emitter_records_classification_event_inside_active_trace() -> None:
    trace_context = create_trace_context(
        session_id="session_1",
        group_id="law",
        user_id="u1",
    )
    emitter = IntentEmitter(LangSmithClient(enabled=False))
    intent_analysis = classify_intent("帮我比较两个方案的差异", history=[])

    with activate_trace_context(trace_context):
        event = emitter.emit_intent_classification_run(
            started_at=datetime.now(),
            input_summary={"query": "帮我比较两个方案的差异"},
            output_summary=summarize_intent_analysis(intent_analysis),
            metadata={"main_intent": str(intent_analysis.main_intent)},
        )

    assert event is not None
    assert event.event_type == "intent_classification_run"
    assert event.output_summary["route"] in {"qa", "orchestrated", "chat", "reject"}
    assert len(trace_context.events) == 1


def test_intent_emitter_without_active_trace_context_is_safe_noop() -> None:
    emitter = IntentEmitter(LangSmithClient(enabled=False))
    intent_analysis = classify_intent("你好", history=[])

    event = emitter.emit_intent_classification_run(
        started_at=datetime.now(),
        input_summary={"query": "你好"},
        output_summary=summarize_intent_analysis(intent_analysis),
        metadata={"main_intent": str(intent_analysis.main_intent)},
    )

    assert event is None
