from __future__ import annotations

from monitoring.core.types import MonitoringEvent, RequestTimeline


_STAGE_NAME_BY_EVENT_TYPE = {
    "intent_classification_run": "intent",
    "context_assembly_run": "context",
    "workflow_run": "workflow",
    "answer_model_run": "answer",
}

_BRANCH_NAME_BY_EVENT_TYPE = {
    "retrieval_run": "retrieval",
    "compaction_run": "compaction",
    "pre_compaction_extraction_run": "pre_compaction_extraction",
}


def assemble_timeline(events: list[MonitoringEvent]) -> RequestTimeline:
    trace_id = events[0].trace_id if events else ""
    stages: list[dict[str, object]] = []
    branches: list[dict[str, object]] = []
    for event in events:
        if event.event_type in _STAGE_NAME_BY_EVENT_TYPE:
            stages.append(
                {
                    "name": _STAGE_NAME_BY_EVENT_TYPE[event.event_type],
                    "event_type": event.event_type,
                    "status": event.status,
                    "latency_ms": event.latency_ms,
                    "metadata": dict(event.metadata),
                    "output_summary": dict(event.output_summary),
                }
            )
        elif event.event_type in _BRANCH_NAME_BY_EVENT_TYPE:
            branches.append(
                {
                    "name": _BRANCH_NAME_BY_EVENT_TYPE[event.event_type],
                    "event_type": event.event_type,
                    "status": event.status,
                    "latency_ms": event.latency_ms,
                    "metadata": dict(event.metadata),
                    "output_summary": dict(event.output_summary),
                }
            )
    return RequestTimeline(trace_id=trace_id, stages=stages, branches=branches)
