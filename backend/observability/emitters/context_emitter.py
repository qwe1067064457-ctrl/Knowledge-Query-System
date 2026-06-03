from __future__ import annotations

from datetime import datetime
from typing import Any

from observability.contracts.enums import (
    EVENT_COMPACTION_RUN,
    EVENT_CONTEXT_ASSEMBLY_RUN,
    EVENT_PRE_COMPACTION_EXTRACTION_RUN,
)
from observability.emitters._base import BaseEmitter


class ContextEmitter(BaseEmitter):
    def emit_context_assembly_run(
        self,
        *,
        started_at: datetime,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        metadata: dict[str, Any],
        status: str = "success",
    ):
        return self._emit(
            event_type=EVENT_CONTEXT_ASSEMBLY_RUN,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata,
            started_at=started_at,
        )

    def emit_pre_compaction_extraction_run(
        self,
        *,
        started_at: datetime,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        metadata: dict[str, Any],
        status: str,
        error_summary: str | None = None,
    ):
        return self._emit(
            event_type=EVENT_PRE_COMPACTION_EXTRACTION_RUN,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata,
            error_summary=error_summary,
            started_at=started_at,
        )

    def emit_compaction_run(
        self,
        *,
        started_at: datetime,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        metadata: dict[str, Any],
        status: str,
        error_summary: str | None = None,
    ):
        return self._emit(
            event_type=EVENT_COMPACTION_RUN,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata,
            error_summary=error_summary,
            started_at=started_at,
        )
