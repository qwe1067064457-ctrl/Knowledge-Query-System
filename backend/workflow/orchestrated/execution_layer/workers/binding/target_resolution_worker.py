from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class TargetResolutionWorker(BaseWorker):
    name = "target_resolution"
    description = "Resolve target bindings for a unit, including rewrite and clarification fallback."

    def __init__(self, context_binding_power) -> None:
        self.context_binding_power = context_binding_power

    def run(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        working_memory: Any = None,
        recent_messages: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir: str | None = None,
        rewrite_query: bool = True,
        recent_power: str | None = None,
        recent_object_type: str | None = None,
        memory_anchors: list[dict[str, Any]] | None = None,
    ):
        return self.context_binding_power.bind(
            query,
            candidates,
            working_memory=working_memory,
            recent_messages=recent_messages,
            llm_call=llm_call,
            base_dir=Path(base_dir) if base_dir else None,
            rewrite_query=rewrite_query,
            recent_power=recent_power,
            recent_object_type=recent_object_type,
            memory_anchors=memory_anchors,
        )

