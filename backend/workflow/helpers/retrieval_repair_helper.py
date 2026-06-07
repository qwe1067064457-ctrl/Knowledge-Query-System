from __future__ import annotations

from typing import Any

from workflow.types import QueryUnit, RetrievalQualityAssessment


class RetrievalRepairHelper:
    def build_repair_plan(
        self,
        *,
        query_unit: QueryUnit,
        quality: RetrievalQualityAssessment,
        current_mode: str = "raw",
    ) -> dict[str, Any]:
        if not quality.should_repair:
            return {
                "enabled": False,
                "strategy": "none",
                "next_mode": current_mode,
                "next_query_text": query_unit.text,
                "top_k": 4,
            }

        if current_mode == "raw" and query_unit.target_refs:
            return {
                "enabled": True,
                "strategy": "switch_to_bound_query",
                "next_mode": "bound",
                "next_query_text": f"{query_unit.text} {' '.join(query_unit.target_refs)}".strip(),
                "top_k": 4,
                "notes": ["reuse_target_refs_for_bound_query"],
            }

        return {
            "enabled": True,
            "strategy": "relax_soft_filters",
            "next_mode": current_mode,
            "next_query_text": query_unit.text,
            "top_k": 6,
            "notes": ["increase_top_k_for_repair"],
        }
