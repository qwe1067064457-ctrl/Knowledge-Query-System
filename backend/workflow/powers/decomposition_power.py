from __future__ import annotations

import re

from workflow.types import QueryUnit


class DecompositionPower:
    def split_parallel_queries(self, query: str) -> tuple[QueryUnit, ...]:
        parts = [part.strip() for part in re.split(r"[？?]\s*|\n+", query) if part.strip()]
        if len(parts) <= 1:
            return (QueryUnit(unit_id="primary", text=query.strip(), origin="primary"),)
        return tuple(
            QueryUnit(unit_id=f"q{index}", text=part, origin="primary")
            for index, part in enumerate(parts, start=1)
        )
