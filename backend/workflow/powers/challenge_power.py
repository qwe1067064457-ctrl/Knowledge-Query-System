from __future__ import annotations

from typing import Any

from workflow.types import ChallengeResult


class ChallengePower:
    def execute(
        self,
        *,
        query: str,
        candidate_targets: list[dict[str, Any]],
        binding_worker: Any | None = None,
        review_worker: Any | None = None,
    ) -> ChallengeResult:
        if not candidate_targets:
            return ChallengeResult(
                status="needs_clarification",
                answer_constraints={"must_acknowledge_uncertainty": True},
            )

        target = candidate_targets[-1]
        targets = (target,)

        if binding_worker is not None:
            bound = binding_worker.bind(query=query, candidates=candidate_targets)
            if bound.get("binding_ambiguous"):
                return ChallengeResult(
                    status="needs_clarification",
                    targets=tuple(bound.get("bound_targets", ())),
                    answer_constraints={"must_acknowledge_uncertainty": True},
                )
            if bound.get("bound_targets"):
                targets = tuple(bound["bound_targets"])

        if review_worker is None:
            return ChallengeResult(
                status="insufficient_evidence",
                targets=targets,
                evidence_assessment={"sufficient": False, "triggered_additional_retrieval": False},
                answer_constraints={"must_acknowledge_uncertainty": True},
            )

        assessment = review_worker.review(query=query, targets=list(targets))
        return ChallengeResult(
            status=assessment.get("status", "success"),
            targets=targets,
            evidence_assessment=dict(assessment.get("evidence_assessment", {})),
            review_findings=tuple(assessment.get("review_findings", ())),
            answer_constraints=dict(assessment.get("answer_constraints", {})),
        )
