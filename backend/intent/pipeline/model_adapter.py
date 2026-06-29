from __future__ import annotations

import os
from dataclasses import replace
from typing import Any, Iterable, Protocol

from intent.schema.intent_types import IntentEvidence, IntentInput, ModelResult, TaskCandidate


INTENT_MODEL_EVIDENCE_ENV = "INTENT_MODEL_EVIDENCE_ENABLED"


class IntentModelAdapter(Protocol):
    def predict(
        self,
        intent_input: IntentInput,
        history: Iterable[dict[str, Any]],
    ) -> ModelResult | None: ...


def is_model_evidence_enabled() -> bool:
    value = os.getenv(INTENT_MODEL_EVIDENCE_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def merge_model_evidence(
    evidence: IntentEvidence,
    model_result: ModelResult | None,
) -> IntentEvidence:
    """Attach model payload while keeping route choice behind the quality gate."""

    if model_result is None or not model_result.valid:
        return evidence
    if _should_skip_model_merge(evidence):
        return evidence

    sanitized = _sanitize_model_result(model_result)
    if sanitized is None:
        return evidence

    merged_task_candidates = _merge_task_candidates(evidence.task_candidates, sanitized.task_candidates)
    return replace(
        evidence,
        task_candidates=merged_task_candidates,
        model_result=sanitized,
    )


def _should_skip_model_merge(evidence: IntentEvidence) -> bool:
    if any(evidence.unsupported_signals.values()):
        return True
    return evidence.classifier_mode == "rule_only"


def _sanitize_model_result(model_result: ModelResult) -> ModelResult | None:
    if not model_result.valid:
        return None
    has_soft_payload = any(
        [
            model_result.candidate_intents,
            model_result.task_candidates,
            model_result.main_intent_probs,
            model_result.task_complexity_probs,
            model_result.task_shape_probs,
            model_result.task_topology_probs,
            model_result.context_dependency_probs,
            model_result.handling_mode_probs,
            model_result.modifier_scores,
            model_result.context_scores,
            model_result.safety_scores,
            model_result.ambiguity_scores,
        ]
    )
    if not has_soft_payload and not any(model_result.modifiers.to_dict().values()):
        return None
    return model_result


def _merge_task_candidates(
    rule_candidates: tuple[TaskCandidate, ...],
    model_candidates: tuple[TaskCandidate, ...],
) -> tuple[TaskCandidate, ...]:
    merged: dict[tuple[str, str, str], TaskCandidate] = {
        (candidate.complexity, candidate.shape, candidate.topology): candidate for candidate in rule_candidates
    }
    for candidate in model_candidates:
        key = (candidate.complexity, candidate.shape, candidate.topology)
        current = merged.get(key)
        if current is None or candidate.score > current.score:
            merged[key] = candidate
    return tuple(merged.values())

