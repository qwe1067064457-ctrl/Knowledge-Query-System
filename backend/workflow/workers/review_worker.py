from __future__ import annotations

from typing import Any


class ReviewWorker:
    def review(self, *, query: str, targets: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "status": "success",
            "evidence_assessment": {
                "sufficient": bool(targets),
                "used_existing_evidence": bool(targets),
                "triggered_additional_retrieval": False,
            },
            "review_findings": tuple(
                {
                    "target_ref": target.get("object_id") or target.get("content") or f"target_{index}",
                    "judgment": "insufficient_evidence",
                    "reason": "Review worker placeholder result.",
                    "supporting_evidence_refs": [],
                }
                for index, target in enumerate(targets, start=1)
            ),
            "answer_constraints": {
                "must_cite_sources": True,
                "must_acknowledge_uncertainty": True,
            },
        }
