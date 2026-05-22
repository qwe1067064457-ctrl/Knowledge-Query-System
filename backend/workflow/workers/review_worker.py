from __future__ import annotations

from typing import Any

from workflow.types import EvidenceAssessmentResult, EvidenceRefCandidate, ReviewEvaluationResult


class ReviewWorker:
    def evidence_check(
        self,
        *,
        query: str,
        targets: list[dict[str, Any]],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> EvidenceAssessmentResult:
        evidence_refs = self._collect_evidence_refs(evidence_candidates)
        matched_targets = 0
        per_target_assessment = []
        for target in targets:
            target_refs = self._target_refs(target)
            target_id = str(target.get("object_id") or target.get("content") or f"target_{len(per_target_assessment) + 1}")
            matched_refs = sorted(target_refs & evidence_refs) if target_refs else []
            matched = False
            if target_refs:
                if matched_refs:
                    matched_targets += 1
                    matched = True
            elif evidence_candidates:
                matched_targets += 1
                matched = True
                matched_refs = sorted(evidence_refs)

            per_target_assessment.append(
                {
                    "target_ref": target_id,
                    "matched": matched,
                    "matched_evidence_refs": matched_refs,
                }
            )

        sufficient = bool(targets) and matched_targets == len(targets)
        partially_sufficient = bool(targets) and 0 < matched_targets < len(targets)
        matched_target_refs = [
            str(item.get("target_ref"))
            for item in per_target_assessment
            if item.get("matched")
        ]
        unsupported_target_refs = [
            str(item.get("target_ref"))
            for item in per_target_assessment
            if not item.get("matched")
        ]
        return EvidenceAssessmentResult(
            sufficient=sufficient,
            partially_sufficient=partially_sufficient,
            used_existing_evidence=bool(evidence_candidates),
            triggered_additional_retrieval=not sufficient,
            matched_target_count=matched_targets,
            target_count=len(targets),
            coverage_ratio=(matched_targets / len(targets)) if targets else 0.0,
            supporting_evidence_refs=tuple(sorted(evidence_refs)),
            matched_target_refs=tuple(matched_target_refs),
            unsupported_target_refs=tuple(unsupported_target_refs),
            needs_more_evidence_targets=tuple(unsupported_target_refs),
            retrieve_if_needed={
                "needed": bool(targets) and matched_targets < len(targets),
                "target_refs": unsupported_target_refs,
                "reason": "insufficient_target_coverage" if unsupported_target_refs else "not_needed",
            },
            per_target_assessment=tuple(per_target_assessment),
            evidence_notes=() if sufficient else ("existing_evidence_not_enough",),
        )

    def re_evaluate(
        self,
        *,
        query: str,
        targets: list[dict[str, Any]],
        evidence_assessment: EvidenceAssessmentResult | dict[str, Any],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> ReviewEvaluationResult:
        assessment_result = (
            evidence_assessment
            if isinstance(evidence_assessment, EvidenceAssessmentResult)
            else EvidenceAssessmentResult.from_dict(evidence_assessment)
        )
        supporting_refs = list(assessment_result.supporting_evidence_refs)
        sufficient = assessment_result.sufficient
        partially_sufficient = assessment_result.partially_sufficient
        findings = []
        for index, target in enumerate(targets, start=1):
            target_ref = target.get("object_id") or target.get("content") or f"target_{index}"
            matched_refs = assessment_result.matched_evidence_refs_for(str(target_ref))
            if assessment_result.target_is_matched(str(target_ref)):
                judgment = "supported"
                reason = "Existing evidence candidates cover the current challenge target."
            else:
                judgment = "insufficient_evidence"
                reason = "Existing evidence candidates do not yet cover the current challenge target."
            findings.append(
                {
                    "target_ref": target_ref,
                    "judgment": judgment,
                    "reason": reason,
                    "supporting_evidence_refs": matched_refs or supporting_refs,
                }
            )

        status = "success" if sufficient else "partial_success" if partially_sufficient else "insufficient_evidence"
        return ReviewEvaluationResult(
            status=status,
            review_findings=tuple(findings),
            answer_constraints={
                "must_cite_sources": True,
                "must_acknowledge_uncertainty": not sufficient,
            },
        )

    def review(
        self,
        *,
        query: str,
        targets: list[dict[str, Any]],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        evidence_candidates = list(evidence_candidates or ())
        evidence_assessment = self.evidence_check(
            query=query,
            targets=targets,
            evidence_candidates=evidence_candidates,
        )
        reevaluation = self.re_evaluate(
            query=query,
            targets=targets,
            evidence_assessment=evidence_assessment,
            evidence_candidates=evidence_candidates,
        )
        return {
            "status": reevaluation.status,
            "evidence_assessment": evidence_assessment.to_dict(),
            "review_findings": reevaluation.review_findings,
            "answer_constraints": reevaluation.answer_constraints,
        }

    def _collect_evidence_refs(self, evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]]) -> set[str]:
        refs: set[str] = set()
        for evidence in evidence_candidates:
            if isinstance(evidence, EvidenceRefCandidate):
                refs.update(evidence.all_refs())
                continue
            object_id = evidence.get("object_id")
            if object_id:
                refs.add(str(object_id))
            for ref in evidence.get("refs", ()):
                refs.add(str(ref))
        return refs

    def _target_refs(self, target: dict[str, Any]) -> set[str]:
        refs: set[str] = set()
        object_id = target.get("object_id")
        if object_id:
            refs.add(str(object_id))
        for ref in target.get("refs", ()):
            refs.add(str(ref))
        return refs
