from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class RelevantSetWorker(BaseWorker):
    name = "relevant_set_selection"
    description = "Build a relevant set from binding candidates for a unit."

    def __init__(self, binding_worker) -> None:
        self.binding_worker = binding_worker

    def run(self, query: str, candidates: list[dict], query_style: str | None = None, max_candidates: int = 7):
        return self.binding_worker.filter_relevant_set(
            query=query,
            candidates=candidates,
            query_style=query_style,
            max_candidates=max_candidates,
        )

