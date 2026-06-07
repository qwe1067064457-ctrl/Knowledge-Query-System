from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from observability.contracts.events import ObservabilityEvent
from observability.langsmith.client import LangSmithClient
from observability.runtime.trace_context_store import get_current_trace_context


class BaseEmitter:
    def __init__(self, client: LangSmithClient | None = None) -> None:
        self.client = client or LangSmithClient()

    def _emit(
        self,
        *,
        event_type,
        status: str,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        error_summary: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        parent_run_id: str | None = None,
    ) -> ObservabilityEvent | None:
        trace_context = get_current_trace_context()
        if trace_context is None:
            return None

        started = started_at or datetime.now()
        ended = ended_at or datetime.now()
        latency_ms = max(0, int((ended - started).total_seconds() * 1000))
        payload_metadata = {
            "session_id": trace_context.session_id,
            "query_id": trace_context.query_id,
            "group_id": trace_context.group_id,
            "user_id": trace_context.user_id,
            **dict(metadata or {}),
        }
        event = ObservabilityEvent(
            event_type=event_type,
            run_id=str(uuid4()),
            parent_run_id=parent_run_id,
            trace_id=trace_context.trace_id,
            status=status,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            latency_ms=latency_ms,
            input_summary=dict(input_summary or {}),
            output_summary=dict(output_summary or {}),
            error_summary=error_summary,
            metadata=payload_metadata,
        )
        trace_context.record_event(event)
        self.client.record_event(event)
        return event
