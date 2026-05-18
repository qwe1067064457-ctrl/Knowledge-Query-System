from __future__ import annotations

import os
from dataclasses import replace
from typing import Any, Iterable, Protocol

from intent.types import IntentEvidence, IntentInput, IntentModifiers, ModelResult, TaskCandidate


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
    allowed_modifiers = IntentModifiers(soft_doubt=model_result.modifiers.soft_doubt)
    allowed_tasks = tuple(model_result.task_candidates)
    if not allowed_modifiers.soft_doubt and not allowed_tasks:
        return None

    return ModelResult(
        valid=True,
        candidate_intents=(),
        modifiers=allowed_modifiers,
        task_candidates=allowed_tasks,
        context_dependency="none",
        confidence=model_result.confidence,
        reason=model_result.reason,
    )


def _merge_task_candidates(
    rule_candidates: tuple[TaskCandidate, ...],
    model_candidates: tuple[TaskCandidate, ...],
) -> tuple[TaskCandidate, ...]:
    merged: dict[tuple[str, str], TaskCandidate] = {
        (candidate.complexity, candidate.shape): candidate for candidate in rule_candidates
    }
    for candidate in model_candidates:
        key = (candidate.complexity, candidate.shape)
        current = merged.get(key)
        if current is None or candidate.score > current.score:
            merged[key] = candidate
    return tuple(merged.values())
