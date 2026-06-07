from __future__ import annotations

from typing import Any

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class CandidateCollectionWorker(BaseWorker):
    name = "candidate_collection"
    description = "Collect binding candidates for a unit from registry entries."

    def __init__(self, context_binding_power) -> None:
        self.context_binding_power = context_binding_power

    def run(self, entries: list[dict[str, Any]], limit: int = 20):
        return self.context_binding_power.collect_candidates(entries, limit=limit)

