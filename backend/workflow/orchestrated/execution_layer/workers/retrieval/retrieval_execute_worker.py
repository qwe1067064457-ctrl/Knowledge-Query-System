from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker
from workflow.types import QueryUnit


class RetrievalExecuteWorker(BaseWorker):
    name = "retrieval_execute"
    description = "Execute retrieval for prepared query units."

    def __init__(self, retrieval_power) -> None:
        self.retrieval_power = retrieval_power

    def run(
        self,
        query_units: list[dict] | tuple[dict, ...],
        path_filters: list[str] | tuple[str, ...] = (),
    ):
        units = tuple(
            QueryUnit(
                unit_id=str(dict(item).get("unit_id", "")),
                text=str(dict(item).get("text", "")),
                origin=str(dict(item).get("origin", "primary")),  # type: ignore[arg-type]
                target_refs=tuple(str(ref) for ref in dict(item).get("target_refs", ()) if ref),
            )
            for item in query_units
        )
        return self.retrieval_power.retrieve(
            units,
            path_filters=tuple(str(item) for item in path_filters if item),
        )
