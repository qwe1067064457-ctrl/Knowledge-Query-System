from __future__ import annotations

from typing import Any

from workflow.types import ContextBindingResult

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class ChallengeTargetSelectionWorker(BaseWorker):
    name = "challenge_target_selection"
    description = "Select challenge review targets from candidates and binding contract."

    def run(
        self,
        candidate_targets: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        evidence_candidates: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        binding_result: ContextBindingResult | dict[str, Any] | None = None,
    ):
        del evidence_candidates
        binding_contract = self._normalize_binding_result(binding_result)
        targets = self._targets_from_binding_contract(binding_contract)
        if targets:
            return {
                "targets": targets,
                "binding_contract_used": True,
                "needs_clarification": False,
                "binding_fallback_type": binding_contract.fallback_type if binding_contract is not None else None,
                "binding_reason": binding_contract.reason if binding_contract is not None else None,
            }
        if binding_contract is not None and self._binding_requires_clarification(binding_contract):
            ambiguous_targets = [dict(item) for item in binding_contract.relevant_set]
            return {
                "targets": [],
                "binding_contract_used": True,
                "needs_clarification": True,
                "clarification_targets": ambiguous_targets,
                "binding_fallback_type": binding_contract.fallback_type,
                "binding_reason": binding_contract.reason,
                "clarification_hint": binding_contract.clarification_hint,
            }

        non_evidence_targets = [
            dict(candidate)
            for candidate in candidate_targets
            if dict(candidate).get("object_type") != "evidence_ref"
        ]
        targets = non_evidence_targets or [dict(candidate) for candidate in candidate_targets]
        return {
            "targets": self._dedupe_targets(targets),
            "binding_contract_used": binding_contract is not None,
            "needs_clarification": False,
            "binding_fallback_type": binding_contract.fallback_type if binding_contract is not None else None,
            "binding_reason": binding_contract.reason if binding_contract is not None else None,
        }

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

    def _dedupe_targets(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
