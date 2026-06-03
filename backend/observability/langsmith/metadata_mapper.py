from __future__ import annotations

from observability.contracts.enums import RUN_NAME_BY_EVENT_TYPE
from observability.contracts.events import ObservabilityEvent


def map_event_to_langsmith_payload(event: ObservabilityEvent) -> dict[str, object]:
    metadata = {
        "trace_id": event.trace_id,
        "status": event.status,
        "latency_ms": event.latency_ms,
        **dict(event.metadata),
    }
    return {
        "name": RUN_NAME_BY_EVENT_TYPE[event.event_type],
        "run_type": "chain",
        "inputs": dict(event.input_summary),
        "outputs": dict(event.output_summary),
        "metadata": metadata,
        "tags": _build_tags(event),
    }


def _build_tags(event: ObservabilityEvent) -> list[str]:
    tags = [f"event:{event.event_type}", f"trace:{event.trace_id}"]
    session_id = event.metadata.get("session_id")
    if session_id:
        tags.append(f"session:{session_id}")
    workflow_name = event.metadata.get("workflow_name")
    if workflow_name:
        tags.append(f"workflow:{workflow_name}")
    return tags
