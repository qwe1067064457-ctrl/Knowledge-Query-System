from __future__ import annotations

from datetime import datetime
from typing import Any

from observability.contracts.enums import EVENT_WORKFLOW_RUN
from observability.emitters._base import BaseEmitter


class WorkflowEmitter(BaseEmitter):
    def emit_workflow_run(
        self,
        *,
        started_at: datetime,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        metadata: dict[str, Any],
        status: str = "success",
        error_summary: str | None = None,
    ):
        return self._emit(
            event_type=EVENT_WORKFLOW_RUN,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata,
            error_summary=error_summary,
            started_at=started_at,
        )
