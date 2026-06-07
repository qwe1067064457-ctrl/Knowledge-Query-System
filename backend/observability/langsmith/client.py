from __future__ import annotations

import os

try:
    from langsmith.run_helpers import trace as langsmith_trace
except Exception:  # pragma: no cover - optional dependency guard
    langsmith_trace = None

from observability.contracts.events import ObservabilityEvent
from observability.langsmith.metadata_mapper import map_event_to_langsmith_payload


class LangSmithClient:
    def __init__(self, *, enabled: bool | None = None) -> None:
        self.enabled = self._resolve_enabled() if enabled is None else enabled

    def _resolve_enabled(self) -> bool:
        raw = str(
            os.getenv("LANGSMITH_TRACING")
            or os.getenv("LANGCHAIN_TRACING_V2")
            or ""
        ).strip().lower()
        if raw in {"", "0", "false", "no", "off"}:
            return False
        return bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))

    def record_event(self, event: ObservabilityEvent) -> None:
        if not self.enabled or langsmith_trace is None:
            return

        payload = map_event_to_langsmith_payload(event)
        try:
            with langsmith_trace(
                name=payload["name"],
                run_type=payload["run_type"],
                inputs=payload["inputs"],
                tags=payload["tags"],
                metadata=payload["metadata"],
                run_id=event.run_id,
            ) as run_tree:
                run_tree.end(
                    outputs=payload["outputs"],
                    error=event.error_summary,
                    metadata=payload["metadata"],
                )
        except Exception:
            return
