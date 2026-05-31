from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker
from workflow.types import QueryUnit


class RetrievalQueryBuilderWorker(BaseWorker):
    name = "retrieval_query_builder"
    description = "Build retrieval query units for a unit execution."

    def run(self, unit_id: str, query: str, target_refs: list[str] | tuple[str, ...] = (), origin: str = "primary"):
        query_unit = QueryUnit(
            unit_id=unit_id,
            text=query.strip(),
            origin=origin,  # type: ignore[arg-type]
            target_refs=tuple(str(item) for item in target_refs if item),
        )
        return {"query_units": [query_unit.to_dict()]}

