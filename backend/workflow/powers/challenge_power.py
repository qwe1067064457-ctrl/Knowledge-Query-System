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
        worker_registry: Any | None = None,
        knowledge_path_filters: tuple[str, ...] = (),
    ) -> ChallengeResult:
        evidence_candidates = list(evidence_candidates or ())
        binding_contract = self._normalize_binding_result(binding_result)
        selection = self._select_targets(
            candidate_targets=candidate_targets,
            evidence_candidates=evidence_candidates,
            binding_result=binding_contract,
            worker_registry=worker_registry,
        )
        identified_targets = [dict(item) for item in selection.get("targets", ()) or ()]
        if selection.get("needs_clarification", False):
            ambiguous_targets = tuple(dict(item) for item in selection.get("clarification_targets", ()) or ())
            return self._build_clarification_result(
                query=query,
                targets=ambiguous_targets,
                used_existing_evidence=bool(evidence_candidates),
                clarification_hint=str(selection.get("clarification_hint") or "").strip(),
                review_summary={
                    "binding_contract_used": bool(selection.get("binding_contract_used", binding_contract is not None)),
                    "binding_fallback_type": selection.get("binding_fallback_type"),
                    "binding_reason": selection.get("binding_reason"),
                },
                fallback="binding_fallback",
            )
        if not identified_targets:
            return self._build_clarification_result(
                query=query,
                targets=(),
                used_existing_evidence=False,
                clarification_hint="",
                review_summary={},
                fallback=None,
            )
        targets = tuple(identified_targets)

        if review_worker is None:
            return self._build_review_fallback_result(
                targets=targets,
                used_existing_evidence=bool(evidence_candidates),
            )

        evidence_assessment = self._evidence_check(
            query=query,
            targets=targets,
            evidence_candidates=evidence_candidates,
            review_worker=review_worker,
            worker_registry=worker_registry,
        )
        evidence_assessment, evidence_candidates = self._retrieve_if_needed(
            query=query,
            rewritten_query=rewritten_query,
            targets=targets,
            evidence_candidates=evidence_candidates,
            evidence_assessment=evidence_assessment,
            review_worker=review_worker,
            retrieval_power=retrieval_power,
            worker_registry=worker_registry,
            knowledge_path_filters=knowledge_path_filters,
        )
        assessment = self._re_evaluate(
            query=query,
            targets=targets,
            evidence_assessment=evidence_assessment,
            evidence_candidates=evidence_candidates,
            review_worker=review_worker,
            worker_registry=worker_registry,
        )
        review_summary = self._review_summary_base(
            binding_contract=binding_contract,
            evidence_assessment=evidence_assessment,
        )
        if not evidence_assessment.sufficient and not evidence_assessment.partially_sufficient:
            return self._build_insufficient_evidence_result(
                query=query,
                targets=targets,
                evidence_assessment=evidence_assessment,
                review_summary=review_summary,
            )

        return self._build_finalized_result(
            query=query,
            targets=targets,
            evidence_assessment=evidence_assessment,
            assessment=assessment,
            review_summary=review_summary,
        )

    def _build_clarification_result(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        used_existing_evidence: bool,
        clarification_hint: str,
        review_summary: dict[str, Any],
        fallback: str | None,
    ) -> ChallengeResult:
        evidence_assessment = EvidenceAssessmentResult(
            sufficient=False,
            used_existing_evidence=used_existing_evidence,
            triggered_additional_retrieval=False,
            fallback=fallback,
        )
        clarification_question = clarification_hint or self.response_helper.build_clarification_question(
            query=query,
            bound_targets=targets,
        )
        return ChallengeResult.from_review_evaluation(
            targets=targets,
            evidence_assessment=evidence_assessment,
            evaluation=ReviewEvaluationResult(
                status="needs_clarification",
                review_findings=(),
                answer_constraints={
                    "must_acknowledge_uncertainty": True,
                    "clarification_question": clarification_question,
                },
            ),
            review_summary=review_summary,
        )

    def _build_review_fallback_result(
        self,
        *,
        targets: tuple[dict[str, Any], ...],
        used_existing_evidence: bool,
    ) -> ChallengeResult:
        return ChallengeResult.from_review_evaluation(
            targets=targets,
            evidence_assessment=EvidenceAssessmentResult(
                sufficient=False,
                used_existing_evidence=used_existing_evidence,
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

    def _build_insufficient_evidence_result(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        evidence_assessment: EvidenceAssessmentResult,
        review_summary: dict[str, Any],
    ) -> ChallengeResult:
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
                        evidence_refs=failed_assessment.supporting_evidence_ref_list(),
                    ),
                },
            ),
            review_summary=review_summary,
        )

    def _build_finalized_result(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        evidence_assessment: EvidenceAssessmentResult,
        assessment: ReviewEvaluationResult,
        review_summary: dict[str, Any],
    ) -> ChallengeResult:
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
            review_summary=review_summary,
        )

    def _review_summary_base(
        self,
        *,
        binding_contract: ContextBindingResult | None,
        evidence_assessment: EvidenceAssessmentResult,
    ) -> dict[str, Any]:
        return {
            "binding_contract_used": binding_contract is not None,
            "binding_fallback_type": binding_contract.fallback_type if binding_contract is not None else None,
            "binding_reason": binding_contract.reason if binding_contract is not None else None,
            "used_existing_evidence": evidence_assessment.used_existing_evidence,
            "retrieve_if_needed_needed": evidence_assessment.needs_follow_up_retrieval(),
            "retrieve_if_needed_reason": str(evidence_assessment.retrieve_if_needed.get("reason", "")),
        }

    def _select_targets(
        self,
        *,
        candidate_targets: list[dict[str, Any]],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
        binding_result: ContextBindingResult | None,
        worker_registry: Any | None,
    ) -> dict[str, Any]:
        worker = self._registry_worker(worker_registry, "challenge_target_selection")
        if worker is not None:
            return dict(
                worker(
                    candidate_targets=[dict(item) for item in candidate_targets],
                    evidence_candidates=[
                        item.to_dict() if hasattr(item, "to_dict") else dict(item)
                        for item in evidence_candidates
                    ],
                    binding_result=binding_result.to_dict() if binding_result is not None else None,
                )
            )

        identified_targets = self._identify_targets(candidate_targets, evidence_candidates)
        contract_targets = self._targets_from_binding_contract(binding_result)
        if contract_targets:
            return {
                "targets": contract_targets,
                "binding_contract_used": True,
                "needs_clarification": False,
                "binding_fallback_type": binding_result.fallback_type if binding_result is not None else None,
                "binding_reason": binding_result.reason if binding_result is not None else None,
            }
        if binding_result is not None and self._binding_requires_clarification(binding_result):
            return {
                "targets": [],
                "binding_contract_used": True,
                "needs_clarification": True,
                "clarification_targets": [dict(item) for item in binding_result.relevant_set],
                "binding_fallback_type": binding_result.fallback_type,
                "binding_reason": binding_result.reason,
                "clarification_hint": binding_result.clarification_hint,
            }
        return {
            "targets": identified_targets,
            "binding_contract_used": binding_result is not None,
            "needs_clarification": False,
            "binding_fallback_type": binding_result.fallback_type if binding_result is not None else None,
            "binding_reason": binding_result.reason if binding_result is not None else None,
        }

    def _evidence_check(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
        review_worker: Any,
        worker_registry: Any | None,
    ) -> EvidenceAssessmentResult:
        worker = self._registry_worker(worker_registry, "target_evidence_check")
        payload_candidates = [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in evidence_candidates]
        if worker is not None:
            result = worker(
                query=query,
                targets=[dict(item) for item in targets],
                evidence_candidates=payload_candidates,
            )
            return result if isinstance(result, EvidenceAssessmentResult) else EvidenceAssessmentResult.from_dict(dict(result))
        return review_worker.evidence_check(
            query=query,
            targets=list(targets),
            evidence_candidates=evidence_candidates,
        )

    def _re_evaluate(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        evidence_assessment: EvidenceAssessmentResult,
        evidence_candidates: list[EvidenceRefCandidate | dict[str, Any]],
        review_worker: Any,
        worker_registry: Any | None,
    ) -> ReviewEvaluationResult:
        worker = self._registry_worker(worker_registry, "challenge_re_evaluate")
        payload_candidates = [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in evidence_candidates]
        if worker is not None:
            result = worker(
                query=query,
                targets=[dict(item) for item in targets],
                evidence_assessment=evidence_assessment.to_dict(),
                evidence_candidates=payload_candidates,
            )
            return result if isinstance(result, ReviewEvaluationResult) else ReviewEvaluationResult.from_dict(dict(result))
        return review_worker.challenge_re_evaluate(
            query=query,
            targets=list(targets),
            evidence_assessment=evidence_assessment,
            evidence_candidates=evidence_candidates,
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
        worker_registry: Any | None,
        knowledge_path_filters: tuple[str, ...],
    ) -> tuple[EvidenceAssessmentResult, list[EvidenceRefCandidate | dict[str, Any]]]:
        planner = self._registry_worker(worker_registry, "followup_retrieval_planner")
        plan = (
            dict(planner(evidence_assessment=evidence_assessment.to_dict()))
            if planner is not None
            else {
                "needed": evidence_assessment.needs_follow_up_retrieval(),
                "target_refs": list(evidence_assessment.retrieve_target_refs()),
                "reason": str(evidence_assessment.retrieve_if_needed.get("reason", "not_needed")),
            }
        )
        if retrieval_power is None or not bool(plan.get("needed", False)):
            return evidence_assessment, evidence_candidates

        support_units = self._build_support_query_units_from_worker(
            query=rewritten_query or query,
            targets=targets,
            requested_target_refs=list(plan.get("target_refs", ()) or ()),
            worker_registry=worker_registry,
        )
        if not support_units:
            return evidence_assessment, evidence_candidates

        execute_worker = self._registry_worker(worker_registry, "retrieval_execute")
        bundle_worker = self._registry_worker(worker_registry, "retrieval_bundle")
        if execute_worker is not None:
            support_bundle = execute_worker(
                query_units=[unit.to_dict() for unit in support_units],
                path_filters=list(knowledge_path_filters),
            )
        else:
            support_bundle = retrieval_power.retrieve(
                tuple(support_units),
                path_filters=knowledge_path_filters,
            )
        if bundle_worker is not None:
            bundle_view = dict(bundle_worker(evidence_bundle=support_bundle))
            supplemental_candidates = list(bundle_view.get("evidence_candidates", ()) or ())
            source_refs = list(bundle_view.get("source_refs", ()) or ())
        else:
            supplemental_candidates = list(support_bundle.to_evidence_ref_candidates())
            source_refs = support_bundle.source_ref_list()
        merged_candidates = [*evidence_candidates, *supplemental_candidates]
        reassessed = self._evidence_check(
            query=query,
            targets=targets,
            evidence_candidates=merged_candidates,
            review_worker=review_worker,
            worker_registry=worker_registry,
        )
        follow_up = {
            "attempted": True,
            "query_units": [unit.to_dict() for unit in support_units],
            "source_refs": source_refs,
            "retrieved_evidence_count": support_bundle.merged_evidence_count(),
            "improved": reassessed.matched_target_count > evidence_assessment.matched_target_count,
        }
        updated = reassessed.with_follow_up_retrieval(
            follow_up_retrieval=follow_up,
            triggered_additional_retrieval=True,
        )
        return updated, merged_candidates

    def _build_support_query_units_from_worker(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        requested_target_refs: list[str],
        worker_registry: Any | None,
    ) -> list[QueryUnit]:
        worker = self._registry_worker(worker_registry, "challenge_support_query")
        if worker is not None:
            payload = dict(
                worker(
                    query=query,
                    targets=[dict(item) for item in targets],
                    requested_target_refs=list(requested_target_refs),
                )
            )
            return [QueryUnit(**dict(item)) for item in payload.get("query_units", ()) or ()]
        return self._build_support_query_units(
            query=query,
            targets=targets,
            requested_target_refs=requested_target_refs,
        )

    def _registry_worker(self, worker_registry: Any | None, name: str):
        if worker_registry is None or not hasattr(worker_registry, "has") or not hasattr(worker_registry, "get"):
            return None
        if not worker_registry.has(name):
            return None
        return worker_registry.get(name)

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
