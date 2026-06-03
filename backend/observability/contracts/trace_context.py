from __future__ import annotations

from dataclasses import dataclass, field

from observability.contracts.events import ObservabilityEvent


@dataclass
class TraceContext:
    trace_id: str
    session_id: str
    query_id: str
    group_id: str
    user_id: str
    request_started_at: str
    workflow_run_id: str | None = None
    answer_run_id: str | None = None
    events: list[ObservabilityEvent] = field(default_factory=list)

    def record_event(self, event: ObservabilityEvent) -> None:
        self.events.append(event)
