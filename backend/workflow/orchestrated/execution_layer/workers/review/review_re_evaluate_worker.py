from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class ChallengeReEvaluateWorker(BaseWorker):
    name = "challenge_re_evaluate"
    description = "Re-evaluate a target set after evidence assessment."

    def __init__(self, review_worker) -> None:
        self.review_worker = review_worker

    def run(self, query: str, targets: list[dict], evidence_assessment, evidence_candidates: list[dict]):
        return self.review_worker.challenge_re_evaluate(
            query=query,
            targets=targets,
            evidence_assessment=evidence_assessment,
            evidence_candidates=evidence_candidates,
        )


ReviewReEvaluateWorker = ChallengeReEvaluateWorker
