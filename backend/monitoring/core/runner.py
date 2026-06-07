from __future__ import annotations

from monitoring.core.failure_classifier import classify_failures
from monitoring.core.finalizer import finalize_report
from monitoring.core.metric_aggregator import aggregate_metrics
from monitoring.core.timeline_assembler import assemble_timeline
from monitoring.core.trace_loader import load_trace_events


def run_monitoring(events) -> dict[str, object]:
    loaded_events = load_trace_events(events)
    events_by_trace: dict[str, list[object]] = {}
    for event in loaded_events:
        events_by_trace.setdefault(event.trace_id, []).append(event)
    timelines = [assemble_timeline(trace_events) for trace_events in events_by_trace.values()]
    metrics = aggregate_metrics(timelines)
    failures = classify_failures(timelines)
    return finalize_report(timelines=timelines, metrics=metrics, failures=failures).to_dict()
