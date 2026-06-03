from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from observability.contracts.trace_context import TraceContext


def create_trace_context(
    *,
    session_id: str,
    group_id: str,
    user_id: str,
) -> TraceContext:
    return TraceContext(
        trace_id=str(uuid4()),
        session_id=session_id,
        query_id=str(uuid4()),
        group_id=group_id,
        user_id=user_id,
        request_started_at=datetime.now().isoformat(),
    )
