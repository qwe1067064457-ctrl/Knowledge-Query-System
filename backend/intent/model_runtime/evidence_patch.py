from __future__ import annotations

from dataclasses import dataclass, replace

from intent.schema.intent_types import IntentEvidence, ModelResult


@dataclass(frozen=True)
class EvidencePatch:
    valid: bool = True
    main_intent_probs: dict[str, float] | None = None
    task_complexity_probs: dict[str, float] | None = None
    task_shape_probs: dict[str, float] | None = None
    task_topology_probs: dict[str, float] | None = None
    context_dependency_probs: dict[str, float] | None = None
    handling_mode_probs: dict[str, float] | None = None
    modifier_scores: dict[str, float] | None = None
    context_scores: dict[str, float] | None = None
    safety_scores: dict[str, float] | None = None
    ambiguity_scores: dict[str, float] | None = None
    low_confidence: bool | None = None
    confidence: str | None = None
    reason: str = ""


def apply_evidence_patch(evidence: IntentEvidence, patch: EvidencePatch | None) -> IntentEvidence:
    if patch is None or not patch.valid:
        return evidence

    current = evidence.model_result or ModelResult(valid=True)
    merged = replace(
        current,
        main_intent_probs=_merge_scores(current.main_intent_probs, patch.main_intent_probs),
        task_complexity_probs=_merge_scores(current.task_complexity_probs, patch.task_complexity_probs),
        task_shape_probs=_merge_scores(current.task_shape_probs, patch.task_shape_probs),
        task_topology_probs=_merge_scores(current.task_topology_probs, patch.task_topology_probs),
        context_dependency_probs=_merge_scores(current.context_dependency_probs, patch.context_dependency_probs),
        handling_mode_probs=_merge_scores(current.handling_mode_probs, patch.handling_mode_probs),
        modifier_scores=_merge_scores(current.modifier_scores, patch.modifier_scores),
        context_scores=_merge_scores(current.context_scores, patch.context_scores),
        safety_scores=_merge_scores(current.safety_scores, patch.safety_scores),
        ambiguity_scores=_merge_scores(current.ambiguity_scores, patch.ambiguity_scores),
        low_confidence=current.low_confidence if patch.low_confidence is None else patch.low_confidence,
        confidence=current.confidence if patch.confidence is None else patch.confidence,
        reason=";".join(part for part in (current.reason, patch.reason) if part),
    )
    return replace(evidence, model_result=merged)


def _merge_scores(current: dict[str, float], incoming: dict[str, float] | None) -> dict[str, float]:
    merged = dict(current)
    if incoming:
        merged.update({key: float(value) for key, value in incoming.items()})
    return merged
