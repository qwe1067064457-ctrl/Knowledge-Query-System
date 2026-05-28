from __future__ import annotations

from typing import Any

from workflow.helpers.challenge_response_helper import ChallengeResponseHelper
from workflow.types import (
    ChallengeResult,
    ContextBindingResult,
    EvidenceAssessmentResult,
    EvidenceRefCandidate,
    QueryUnit,
    ReviewEvaluationResult,
)


class ChallengePower:
    def __init__(self, response_helper: ChallengeResponseHelper | None = None) -> None:
        self.response_helper = response_helper or ChallengeResponseHelper()

    def execute(
        self,
        *,
        query: str,
        candidate_targets: list[dict[str, Any]],
        binding_result: ContextBindingResult | dict[str, Any] | None = None,
        rewritten_query: str | None = None,
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]] | None = None,
        binding_worker: Any | None = None,
        review_worker: Any | None = None,
        retrieval_power: Any | None = None,
    ) -> ChallengeResult:
        evidence_candidates = list(evidence_candidates or ())
        binding_contract = self._normalize_binding_result(binding_result)
        identified_targets = self._identify_targets(candidate_targets, evidence_candidates)
        contract_targets = self._targets_from_binding_contract(binding_contract)
        if contract_targets:
            identified_targets = contract_targets
        elif binding_contract is not None and self._binding_requires_clarification(binding_contract):
            ambiguous_targets = tuple(dict(item) for item in binding_contract.relevant_set)
            return ChallengeResult.from_review_evaluation(
                targets=ambiguous_targets,
                evidence_assessment=EvidenceAssessmentResult(
                    sufficient=False,
                    used_existing_evidence=bool(evidence_candidates),
                    triggered_additional_retrieval=False,
                    fallback="binding_fallback",
                ),
                evaluation=ReviewEvaluationResult(
                    status="needs_clarification",
                    review_findings=(),
                    answer_constraints={
                        "must_acknowledge_uncertainty": True,
                        "clarification_question": binding_contract.clarification_hint
                        or self.response_helper.build_clarification_question(
                            query=query,
                            bound_targets=ambiguous_targets,
                        ),
                    },
                ),
                review_summary={
                    "binding_contract_used": True,
                    "binding_fallback_type": binding_contract.fallback_type,
                    "binding_reason": binding_contract.reason,
                },
            )
        if not identified_targets:
            return ChallengeResult.from_review_evaluation(
                targets=(),
                evidence_assessment=EvidenceAssessmentResult(),
                evaluation=ReviewEvaluationResult(
                    status="needs_clarification",
                    review_findings=(),
                    answer_constraints={
                        "must_acknowledge_uncertainty": True,
                        "clarification_question": self.response_helper.build_clarification_question(
                            query=query,
                            bound_targets=(),
                        ),
                    },
                ),
                review_summary={},
            )
        targets = tuple(identified_targets)

        if review_worker is None:
            return ChallengeResult.from_review_evaluation(
                targets=targets,
                evidence_assessment=EvidenceAssessmentResult(
                    sufficient=False,
                    used_existing_evidence=bool(evidence_candidates),
                    triggered_additional_retrieval=False,
                    fallback="review_fallback",
                ),
                evaluation=ReviewEvaluationResult(
                    status="failed_with_fallback",
                    review_findings=(),
                    answer_constraints={"must_acknowledge_uncertainty": True},
                ),
                review_summary={},
            )

        evidence_assessment = review_worker.evidence_check(
            query=query,
            targets=list(targets),
            evidence_candidates=evidence_candidates,
        )
        evidence_assessment, evidence_candidates = self._retrieve_if_needed(
            query=query,
            rewritten_query=rewritten_query,
            targets=targets,
            evidence_candidates=evidence_candidates,
            evidence_assessment=evidence_assessment,
            review_worker=review_worker,
            retrieval_power=retrieval_power,
        )
        assessment = review_worker.re_evaluate(
            query=query,
            targets=list(targets),
            evidence_assessment=evidence_assessment,
            evidence_candidates=evidence_candidates,
        )
        if not evidence_assessment.sufficient and not evidence_assessment.partially_sufficient:
            failed_assessment = evidence_assessment.with_fallback("evidence_fallback")
            return ChallengeResult.from_review_evaluation(
                targets=targets,
                evidence_assessment=failed_assessment,
                evaluation=ReviewEvaluationResult(
                    status="insufficient_evidence",
                    review_findings=tuple(
                        {
                            "target_ref": target.get("object_id") or target.get("content") or f"target_{index}",
                            "judgment": "insufficient_evidence",
                            "reason": "Need more evidence before a stable challenge re-evaluation.",
                            "supporting_evidence_refs": failed_assessment.supporting_evidence_ref_list(),
                        }
                        for index, target in enumerate(targets, start=1)
                    ),
                    answer_constraints={
                        "must_cite_sources": True,
                        "must_acknowledge_uncertainty": True,
                        "fallback_message": self.response_helper.build_evidence_fallback_message(
                            query=query,
                            targets=targets,
                            evidence_refs=evidence_assessment.supporting_evidence_ref_list(),
                        ),
                    },
                ),
                review_summary={
                    "binding_contract_used": binding_contract is not None,
                    "binding_fallback_type": binding_contract.fallback_type if binding_contract is not None else None,
                    "binding_reason": binding_contract.reason if binding_contract is not None else None,
                    "used_existing_evidence": failed_assessment.used_existing_evidence,
                    "retrieve_if_needed_needed": failed_assessment.needs_follow_up_retrieval(),
                    "retrieve_if_needed_reason": str(failed_assessment.retrieve_if_needed.get("reason", "")),
                },
            )

        answer_constraints = dict(assessment.answer_constraints)
        if assessment.status == "partial_success":
            answer_constraints["fallback_message"] = self.response_helper.build_evidence_fallback_message(
                query=query,
                targets=targets,
                evidence_refs=evidence_assessment.supporting_evidence_ref_list(),
            )
        finalized_assessment = assessment.with_answer_constraints(answer_constraints)
        return ChallengeResult.from_review_evaluation(
            targets=targets,
            evidence_assessment=evidence_assessment,
            evaluation=finalized_assessment,
            review_summary={
                "binding_contract_used": binding_contract is not None,
                "binding_fallback_type": binding_contract.fallback_type if binding_contract is not None else None,
                "binding_reason": binding_contract.reason if binding_contract is not None else None,
                "used_existing_evidence": evidence_assessment.used_existing_evidence,
                "retrieve_if_needed_needed": evidence_assessment.needs_follow_up_retrieval(),
                "retrieve_if_needed_reason": str(evidence_assessment.retrieve_if_needed.get("reason", "")),
            },
        )

    def _normalize_binding_result(
        self,
        binding_result: ContextBindingResult | dict[str, Any] | None,
    ) -> ContextBindingResult | None:
        if binding_result is None:
            return None
        if isinstance(binding_result, ContextBindingResult):
            return binding_result
        return ContextBindingResult.from_dict(binding_result)

    def _targets_from_binding_contract(
        self,
        binding_result: ContextBindingResult | None,
    ) -> list[dict[str, Any]]:
        if binding_result is None:
            return []
        if binding_result.bound_targets:
            return [dict(item) for item in binding_result.bound_targets]
        if not binding_result.resolved_target_ids:
            return []
        resolved = {str(item).strip() for item in binding_result.resolved_target_ids if str(item).strip()}
        if not resolved:
            return []
        return [
            dict(item)
            for item in binding_result.relevant_set
            if str(item.get("object_id") or item.get("entry_id") or "").strip() in resolved
        ]

    def _binding_requires_clarification(self, binding_result: ContextBindingResult) -> bool:
        if binding_result.needs_clarification or binding_result.binding_ambiguous:
            return True
        return str(binding_result.fallback_type or "").strip() == "needs_clarification"

    def _identify_targets(
        self,
        candidate_targets: list[dict[str, Any]],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
    ) -> list[dict[str, Any]]:
        non_evidence_targets = [
            candidate
            for candidate in candidate_targets
            if candidate.get("object_type") != "evidence_ref"
        ]
        targets = non_evidence_targets or candidate_targets
        return self._select_targets_for_query(targets)

    def _select_targets_for_query(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for candidate in candidates:
            object_id = str(candidate.get("object_id") or "")
            content = str(candidate.get("content") or "")
            key = (object_id, content)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped

    def _retrieve_if_needed(
        self,
        *,
        query: str,
        rewritten_query: str | None,
        targets: tuple[dict[str, Any], ...],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
        evidence_assessment: EvidenceAssessmentResult,
        review_worker: Any,
        retrieval_power: Any | None,
    ) -> tuple[EvidenceAssessmentResult, list[EvidenceRefCandidate | dict[str, Any]]]:
        if retrieval_power is None or not evidence_assessment.needs_follow_up_retrieval():
            return evidence_assessment, evidence_candidates

        support_units = self._build_support_query_units(
            query=rewritten_query or query,
            targets=targets,
            requested_target_refs=list(evidence_assessment.retrieve_target_refs()),
        )
        if not support_units:
            return evidence_assessment, evidence_candidates

        support_bundle = retrieval_power.retrieve(tuple(support_units))
        supplemental_candidates = list(support_bundle.to_evidence_ref_candidate_objs())
        merged_candidates = [*evidence_candidates, *supplemental_candidates]
        reassessed = review_worker.evidence_check(
            query=query,
            targets=list(targets),
            evidence_candidates=merged_candidates,
        )
        follow_up = {
            "attempted": True,
            "query_units": [unit.to_dict() for unit in support_units],
            "source_refs": support_bundle.source_ref_list(),
            "retrieved_evidence_count": support_bundle.merged_evidence_count(),
            "improved": reassessed.matched_target_count > evidence_assessment.matched_target_count,
        }
        updated = reassessed.with_follow_up_retrieval(
            follow_up_retrieval=follow_up,
            triggered_additional_retrieval=True,
        )
        return updated, merged_candidates

    def _build_support_query_units(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        requested_target_refs: list[str],
    ) -> list[QueryUnit]:
        requested = {str(ref) for ref in requested_target_refs if ref}
        units: list[QueryUnit] = []
        for index, target in enumerate(targets, start=1):
            target_id = str(target.get("object_id") or target.get("content") or f"target_{index}")
            target_refs = tuple(str(ref) for ref in target.get("refs", ()) if ref)
            candidate_refs = {target_id, *target_refs}
            if requested and requested.isdisjoint(candidate_refs):
                continue
            target_text = self._target_support_text(target, fallback=target_id)
            target_refs = target_refs or (target_id,)
            support_text = f"{query} {target_text}".strip()
            units.append(
                QueryUnit(
                    unit_id=f"challenge_support_{index}",
                    text=support_text,
                    origin="support",
                    target_refs=target_refs,
                )
            )
        return units

    def _target_support_text(self, target: dict[str, Any], *, fallback: str) -> str:
        structured = target.get("structured_payload")
        if isinstance(structured, dict):
            disputed_span = str(structured.get("disputed_span") or "").strip()
            if disputed_span:
                return disputed_span
        return str(target.get("content") or fallback).strip()
