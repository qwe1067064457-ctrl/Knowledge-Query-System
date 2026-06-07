from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MonitoringEvent:
    event_type: str
    trace_id: str
    status: str
    latency_ms: int
    started_at: str
    ended_at: str
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_summary: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MonitoringEvent":
        return cls(
            event_type=str(payload.get("event_type", "")),
            trace_id=str(payload.get("trace_id", "")),
            status=str(payload.get("status", "")),
            latency_ms=int(payload.get("latency_ms", 0) or 0),
            started_at=str(payload.get("started_at", "")),
            ended_at=str(payload.get("ended_at", "")),
            input_summary=dict(payload.get("input_summary", {}) or {}),
            output_summary=dict(payload.get("output_summary", {}) or {}),
            metadata=dict(payload.get("metadata", {}) or {}),
            error_summary=str(payload["error_summary"]) if payload.get("error_summary") is not None else None,
        )


@dataclass(frozen=True)
class RequestTimeline:
    trace_id: str
    stages: list[dict[str, Any]] = field(default_factory=list)
    branches: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "stages": list(self.stages),
            "branches": list(self.branches),
        }


@dataclass(frozen=True)
class MetricSnapshot:
    request_count: int = 0
    route_distribution: dict[str, int] = field(default_factory=dict)
    action_distribution: dict[str, int] = field(default_factory=dict)
    answer_success_rate: float = 0.0
    answer_latency_ms: dict[str, int] = field(default_factory=dict)
    retrieval_run_rate: float = 0.0
    compaction_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "route_distribution": dict(self.route_distribution),
            "action_distribution": dict(self.action_distribution),
            "answer_success_rate": self.answer_success_rate,
            "answer_latency_ms": dict(self.answer_latency_ms),
            "retrieval_run_rate": self.retrieval_run_rate,
            "compaction_rate": self.compaction_rate,
        }


@dataclass(frozen=True)
class MonitoringReport:
    timelines: list[RequestTimeline]
    metrics: MetricSnapshot
    failures: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timelines": [item.to_dict() for item in self.timelines],
            "metrics": self.metrics.to_dict(),
            "failures": dict(self.failures),
        }
