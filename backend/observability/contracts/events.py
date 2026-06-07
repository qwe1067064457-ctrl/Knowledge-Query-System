from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from observability.contracts.enums import EventType


@dataclass(frozen=True)
class ObservabilityEvent:
    event_type: EventType
    run_id: str
    parent_run_id: str | None
    trace_id: str
    status: str
    started_at: str
    ended_at: str
    latency_ms: int
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    error_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "trace_id": self.trace_id,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "latency_ms": self.latency_ms,
            "input_summary": dict(self.input_summary),
            "output_summary": dict(self.output_summary),
            "error_summary": self.error_summary,
            "metadata": dict(self.metadata),
        }
