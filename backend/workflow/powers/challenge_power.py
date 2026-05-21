from __future__ import annotations

import re
from typing import Any

from workflow.helpers.challenge_response_helper import ChallengeResponseHelper
from workflow.types import ChallengeResult, QueryUnit


class ChallengePower:
    _MULTI_TARGET_PATTERNS = (
        re.compile(r"前两个"),
        re.compile(r"两个"),
        re.compile(r"两条"),
        re.compile(r"多条"),
        re.compile(r"分别"),
        re.compile(r"以及"),
        re.compile(r"和"),
        re.compile(r"、"),
        re.compile(r"这些"),
        re.compile(r"以上"),
        re.compile(r"都"),
    )

    def __init__(self, response_helper: ChallengeResponseHelper | None = None) -> None:
        self.response_helper = response_helper or ChallengeResponseHelper()

    def execute(
        self,
        *,
        query: str,
        candidate_targets: list[dict[str, Any]],
        evidence_candidates: list[dict[str, Any]] | None = None,
        binding_worker: Any | None = None,
        review_worker: Any | None = None,
        retrieval_power: Any | None = None,
    ) -> ChallengeResult:
        evidence_candidates = list(evidence_candidates or ())
        identified_targets = self._identify_targets(candidate_targets, evidence_candidates)
        if not identified_targets:
            return ChallengeResult(
                status="needs_clarification",
                review_findings=(),
                evidence_assessment={},
                answer_constraints={
                    "must_acknowledge_uncertainty": True,
                    "clarification_question": self.response_helper.build_clarification_question(
                        query=query,
                        bound_targets=(),
                    ),
                },
            )
        targets = tuple(identified_targets)
        summary_targets = targets

        if binding_worker is not None:
            bound = binding_worker.bind(query=query, candidates=identified_targets)
            if bound.get("binding_ambiguous"):
                ambiguous_targets = tuple(bound.get("bound_targets", ()))
                return ChallengeResult(
                    status="needs_clarification",
                    targets=ambiguous_targets,
                    evidence_assessment={
                        "sufficient": False,
                        "used_existing_evidence": bool(evidence_candidates),
                        "triggered_additional_retrieval": False,
                        "fallback": "binding_fallback",
                    },
                    review_findings=(),
                    answer_constraints={
                        "must_acknowledge_uncertainty": True,
                        "clarification_question": self.response_helper.build_clarification_question(
                            query=query,
                            bound_targets=ambiguous_targets,
                        ),
                    },
                )
            if bound.get("bound_targets"):
                targets = tuple(bound["bound_targets"])
                summary_targets = targets

        if review_worker is None:
            return ChallengeResult(
                status="failed_with_fallback",
                targets=targets,
                evidence_assessment={
                    "sufficient": False,
                    "used_existing_evidence": bool(evidence_candidates),
                    "triggered_additional_retrieval": False,
                    "fallback": "review_fallback",
                },
                answer_constraints={"must_acknowledge_uncertainty": True},
            )

        evidence_assessment = review_worker.evidence_check(
            query=query,
            targets=list(targets),
            evidence_candidates=evidence_candidates,
        )
        evidence_assessment, evidence_candidates = self._retrieve_if_needed(
            query=query,
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
        if not evidence_assessment.get("sufficient") and not evidence_assessment.get("partially_sufficient"):
            return ChallengeResult(
                status="insufficient_evidence",
                targets=targets,
                evidence_assessment={
                    **dict(evidence_assessment),
                    "fallback": "evidence_fallback",
                },
                review_findings=tuple(
                    {
                        "target_ref": target.get("object_id") or target.get("content") or f"target_{index}",
                        "judgment": "insufficient_evidence",
                        "reason": "Need more evidence before a stable challenge re-evaluation.",
                        "supporting_evidence_refs": list(evidence_assessment.get("supporting_evidence_refs", ())),
                    }
                    for index, target in enumerate(targets, start=1)
                ),
                answer_constraints={
                    "must_cite_sources": True,
                    "must_acknowledge_uncertainty": True,
                    "fallback_message": self.response_helper.build_evidence_fallback_message(
                        query=query,
                        targets=targets,
                        evidence_refs=list(evidence_assessment.get("supporting_evidence_refs", ())),
                    ),
                },
            )

        answer_constraints = dict(assessment.get("answer_constraints", {}))
        if assessment.get("status") == "partial_success":
            answer_constraints["fallback_message"] = self.response_helper.build_evidence_fallback_message(
                query=query,
                targets=targets,
                evidence_refs=list(evidence_assessment.get("supporting_evidence_refs", ())),
            )
        return ChallengeResult(
            status=assessment.get("status", "success"),
            targets=targets,
            evidence_assessment=dict(evidence_assessment),
            review_findings=tuple(assessment.get("review_findings", ())),
            answer_constraints=answer_constraints,
        )

    def _identify_targets(
        self,
        candidate_targets: list[dict[str, Any]],
        evidence_candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        non_evidence_targets = [
            candidate
            for candidate in candidate_targets
            if candidate.get("object_type") not in {"evidence_ref", "retrieval_result_ref"}
        ]
        targets = non_evidence_targets or candidate_targets or evidence_candidates
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
        targets: tuple[dict[str, Any], ...],
        evidence_candidates: list[dict[str, Any]],
        evidence_assessment: dict[str, Any],
        review_worker: Any,
        retrieval_power: Any | None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        retrieve_if_needed = dict(evidence_assessment.get("retrieve_if_needed", {}))
        if retrieval_power is None or not retrieve_if_needed.get("needed"):
            return evidence_assessment, evidence_candidates

        support_units = self._build_support_query_units(
            query=query,
            targets=targets,
            requested_target_refs=list(retrieve_if_needed.get("target_refs", ())),
        )
        if not support_units:
            return evidence_assessment, evidence_candidates

        support_bundle = retrieval_power.retrieve(tuple(support_units))
        supplemental_candidates = self._bundle_to_evidence_candidates(support_bundle)
        merged_candidates = [*evidence_candidates, *supplemental_candidates]
        reassessed = review_worker.evidence_check(
            query=query,
            targets=list(targets),
            evidence_candidates=merged_candidates,
        )
        follow_up = {
            "attempted": True,
            "query_units": [unit.to_dict() for unit in support_units],
            "source_refs": list(support_bundle.source_refs),
            "retrieved_evidence_count": len(supplemental_candidates),
            "improved": reassessed.get("matched_target_count", 0) > evidence_assessment.get("matched_target_count", 0),
        }
        updated = dict(reassessed)
        updated["triggered_additional_retrieval"] = True
        updated["follow_up_retrieval"] = follow_up
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
            if requested and target_id not in requested:
                continue
            target_text = str(target.get("content") or target_id).strip()
            target_refs = tuple(str(ref) for ref in target.get("refs", ()) if ref) or (target_id,)
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

    def _bundle_to_evidence_candidates(self, bundle: Any) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for item in getattr(bundle, "merged_evidence_items", ()):
            refs = tuple(
                str(ref)
                for ref in (item.evidence_id, item.parent_id, item.source_path, item.locator)
                if ref
            )
            candidates.append(
                {
                    "object_id": str(item.evidence_id),
                    "object_type": "evidence_ref",
                    "content": item.snippet,
                    "refs": refs,
                    "source_type": item.source_type,
                    "channel": item.channel,
                }
            )
        return candidates
