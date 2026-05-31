from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class RetrievalQualityWorker(BaseWorker):
    name = "retrieval_quality"
    description = "Assess retrieval quality for a unit evidence bundle."

    def __init__(self, review_worker) -> None:
        self.review_worker = review_worker

    def run(self, evidence_bundle):
        return self.review_worker.retrieval_quality_check(evidence_bundle=evidence_bundle)

