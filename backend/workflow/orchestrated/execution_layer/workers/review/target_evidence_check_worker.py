from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class TargetEvidenceCheckWorker(BaseWorker):
    name = "target_evidence_check"
    description = "Check whether evidence supports selected targets."

    def __init__(self, review_worker) -> None:
        self.review_worker = review_worker

    def run(self, query: str, targets: list[dict], evidence_candidates: list[dict]):
        return self.review_worker.evidence_check(
            query=query,
            targets=targets,
            evidence_candidates=evidence_candidates,
        )

