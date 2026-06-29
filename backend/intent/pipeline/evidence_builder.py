from __future__ import annotations

from intent.schema.evidence_types import (
    AdjudicationResult,
    CalibrationQuality,
    EvidenceSource,
    SignalCriticality,
    TypedEvidence,
)
from intent.schema.intent_types import (
    CandidateIntent,
    IntentEvidence,
    IntentInput,
    IntentModifiers,
    ModelResult,
    RuleMatch,
    TaskCandidate,
)


ROUTE_SIGNALS = {"qa", "chat", "system", "unsupported", "out_of_scope"}
MODIFIER_SIGNALS = {
    "follow_up",
    "challenge",
    "soft_doubt",
    "ask_source",
    "ask_capability",
}
CONTEXT_SIGNALS = {
    "history_reference",
    "needs_previous_answer",
    "previous_retrieval",
    "clarify_hint",
}
SAFETY_SIGNALS = {"unsupported", "out_of_scope"}


def build_typed_evidence(
    evidence: IntentEvidence,
    intent_input: IntentInput,
) -> tuple[TypedEvidence, ...]:
    """Convert legacy rule/model outputs into structured evidence objects."""

    typed: list[TypedEvidence] = []
    typed.extend(_from_rule_matches(evidence.matched_rules, intent_input))
    typed.extend(_from_rule_candidates(evidence.candidate_intents))
    typed.extend(_from_task_candidates(evidence.task_candidates, source="surface_trigger"))
    typed.extend(_from_context_signals(evidence, intent_input))
    if evidence.model_result and evidence.model_result.valid:
        typed.extend(_from_model_result(evidence.model_result, intent_input))
    if evidence.adjudication_result is not None:
        return _merge_adjudicated_evidence(tuple(typed), evidence.adjudication_result)
    return tuple(typed)


def _merge_adjudicated_evidence(
    original: tuple[TypedEvidence, ...],
    result: AdjudicationResult,
) -> tuple[TypedEvidence, ...]:
    """Build the final evidence set after LLM adjudicates disputed signals."""

    rejected_keys = {_evidence_key(item) for item in result.rejected_evidence}
    kept = [item for item in original if _evidence_key(item) not in rejected_keys]
    kept.extend(result.accepted_evidence)
    kept.extend(result.corrected_evidence)
    return tuple(kept)


def _evidence_key(item: TypedEvidence) -> tuple[str, str, str]:
    return (item.signal, str(item.value), item.source)


def _from_rule_matches(matches: tuple[RuleMatch, ...], intent_input: IntentInput) -> list[TypedEvidence]:
    items: list[TypedEvidence] = []
    for match in matches:
        criticality = _criticality_for_signal(match.signal)
        prerequisites = _prerequisites_for_signal(match.signal)
        missing = _missing_prerequisites(prerequisites, intent_input)
        threshold = _threshold_for_rule(match)
        items.append(
            TypedEvidence(
                signal=match.signal,
                value=True,
                source="surface_trigger",
                score=match.score,
                threshold=threshold,
                margin=round(match.score - threshold, 4),
                calibration_quality="unknown",
                prerequisites=prerequisites,
                missing_prerequisites=missing,
                criticality=criticality,
                rationale=f"surface_trigger:{match.rule_id}",
            )
        )
    return items


def _from_rule_candidates(candidates: tuple[CandidateIntent, ...]) -> list[TypedEvidence]:
    return [
        TypedEvidence(
            signal="main_intent",
            value=candidate.intent,
            source="surface_trigger",
            score=candidate.score,
            threshold=0.6,
            margin=round(candidate.score - 0.6, 4),
            calibration_quality="unknown",
            prerequisites=(),
            missing_prerequisites=(),
            criticality="route",
            rationale="legacy_rule_candidate",
        )
        for candidate in candidates
    ]


def _from_task_candidates(
    candidates: tuple[TaskCandidate, ...],
    *,
    source: EvidenceSource,
) -> list[TypedEvidence]:
    calibration: CalibrationQuality = "weak" if source == "small_model" else "unknown"
    return [
        TypedEvidence(
            signal="task_candidate",
            value=candidate.to_dict(),
            source=source,
            score=candidate.score,
            threshold=0.65,
            margin=round(candidate.score - 0.65, 4),
            calibration_quality=calibration,
            prerequisites=(),
            missing_prerequisites=(),
            criticality="task_shape",
            rationale=f"{source}_task_candidate",
        )
        for candidate in candidates
    ]


def _from_context_signals(evidence: IntentEvidence, intent_input: IntentInput) -> list[TypedEvidence]:
    context = evidence.context_signals
    active = {
        "history_reference": context.history_reference,
        "needs_previous_answer": context.needs_previous_answer,
        "previous_retrieval": context.previous_retrieval,
        "clarify_hint": context.clarify_hint,
    }
    items: list[TypedEvidence] = []
    for signal, enabled in active.items():
        if not enabled:
            continue
        prerequisites = _prerequisites_for_signal(signal)
        items.append(
            TypedEvidence(
                signal=signal,
                value=True,
                source="context_state",
                score=0.9,
                threshold=0.75,
                margin=0.15,
                calibration_quality="good",
                prerequisites=prerequisites,
                missing_prerequisites=_missing_prerequisites(prerequisites, intent_input),
                criticality=_criticality_for_signal(signal),
                rationale="derived_context_signal",
            )
        )
    return items


def _from_model_result(model_result: ModelResult, intent_input: IntentInput) -> list[TypedEvidence]:
    items: list[TypedEvidence] = []
    for candidate in model_result.candidate_intents:
        items.append(
            TypedEvidence(
                signal="main_intent",
                value=candidate.intent,
                source="small_model",
                score=candidate.score,
                threshold=0.6,
                margin=round(candidate.score - 0.6, 4),
                calibration_quality=_model_calibration(model_result),
                prerequisites=(),
                missing_prerequisites=(),
                criticality="route",
                rationale=model_result.reason or "small_model_candidate",
            )
        )
    items.extend(_from_model_probability_heads(model_result, intent_input))
    items.extend(_from_model_modifiers(model_result.modifiers, model_result, intent_input))
    items.extend(_from_task_candidates(model_result.task_candidates, source="small_model"))
    return items


def _from_model_probability_heads(model_result: ModelResult, intent_input: IntentInput) -> list[TypedEvidence]:
    """Expose SFT head probabilities to the quality gate as typed evidence."""

    items: list[TypedEvidence] = []
    items.extend(_top_prob_evidence(model_result, "main_intent", model_result.main_intent_probs, "route"))
    items.extend(_top_prob_evidence(model_result, "task_complexity", model_result.task_complexity_probs, "task_shape"))
    items.extend(_top_prob_evidence(model_result, "task_shape", model_result.task_shape_probs, "task_shape"))
    items.extend(_top_prob_evidence(model_result, "task_topology", model_result.task_topology_probs, "task_shape"))
    items.extend(_top_prob_evidence(model_result, "context_dependency", model_result.context_dependency_probs, "context_dependency"))
    items.extend(_top_prob_evidence(model_result, "handling_mode", model_result.handling_mode_probs, "modifier"))
    items.extend(_score_evidence(model_result, model_result.modifier_scores, intent_input))
    items.extend(_score_evidence(model_result, model_result.context_scores, intent_input))
    items.extend(_score_evidence(model_result, model_result.safety_scores, intent_input))
    items.extend(_score_evidence(model_result, model_result.ambiguity_scores, intent_input, criticality="diagnostic"))
    return items


def _top_prob_evidence(
    model_result: ModelResult,
    head: str,
    scores: dict[str, float],
    criticality: SignalCriticality,
) -> list[TypedEvidence]:
    if not scores:
        return []
    label, score = max(scores.items(), key=lambda item: item[1])
    threshold = 0.55
    margin = model_result.margins.get(head, score - threshold)
    return [
        TypedEvidence(
            signal=head,
            value=label,
            source="small_model",
            score=float(score),
            threshold=threshold,
            margin=round(float(margin), 4),
            calibration_quality=_model_calibration(model_result),
            prerequisites=(),
            missing_prerequisites=(),
            criticality=criticality,
            rationale=model_result.reason or f"small_model_{head}",
        )
    ]


def _score_evidence(
    model_result: ModelResult,
    scores: dict[str, float],
    intent_input: IntentInput,
    *,
    criticality: SignalCriticality | None = None,
) -> list[TypedEvidence]:
    items: list[TypedEvidence] = []
    for signal, score in scores.items():
        threshold = _threshold_for_model_score(signal)
        if float(score) < min(0.15, threshold):
            continue
        prerequisites = _prerequisites_for_signal(signal)
        items.append(
            TypedEvidence(
                signal=signal,
                value=True,
                source="small_model",
                score=float(score),
                threshold=threshold,
                margin=round(float(score) - threshold, 4),
                calibration_quality=_model_calibration(model_result),
                prerequisites=prerequisites,
                missing_prerequisites=_missing_prerequisites(prerequisites, intent_input),
                criticality=criticality or _criticality_for_signal(signal),
                rationale=model_result.reason or "small_model_score",
            )
        )
    return items


def _from_model_modifiers(
    modifiers: IntentModifiers,
    model_result: ModelResult,
    intent_input: IntentInput,
) -> list[TypedEvidence]:
    items: list[TypedEvidence] = []
    for signal, enabled in modifiers.to_dict().items():
        if not enabled:
            continue
        prerequisites = _prerequisites_for_signal(signal)
        score = _score_for_strength(model_result.confidence)
        threshold = 0.6
        items.append(
            TypedEvidence(
                signal=signal,
                value=True,
                source="small_model",
                score=score,
                threshold=threshold,
                margin=round(score - threshold, 4),
                calibration_quality=_model_calibration(model_result),
                prerequisites=prerequisites,
                missing_prerequisites=_missing_prerequisites(prerequisites, intent_input),
                criticality=_criticality_for_signal(signal),
                rationale=model_result.reason or "small_model_modifier",
            )
        )
    return items


def _criticality_for_signal(signal: str) -> SignalCriticality:
    if signal in SAFETY_SIGNALS:
        return "safety"
    if signal in ROUTE_SIGNALS or signal == "main_intent":
        return "route"
    if signal in CONTEXT_SIGNALS:
        return "context_dependency"
    if signal in MODIFIER_SIGNALS:
        return "modifier"
    if signal in {"task_candidate", "task_complexity", "task_shape", "task_topology", "multi_question", "parallel_subtasks", "staged", "complex"}:
        return "task_shape"
    if signal in {"context_dependency", "referent_ambiguity", "target_ambiguity", "scope_ambiguity", "missing_context"}:
        return "context_dependency"
    return "diagnostic"


def _prerequisites_for_signal(signal: str) -> tuple[str, ...]:
    if signal in {"challenge", "soft_doubt", "ask_source", "needs_previous_answer"}:
        return ("previous_answer",)
    if signal in {"follow_up", "history_reference"}:
        return ("history",)
    return ()


def _missing_prerequisites(prerequisites: tuple[str, ...], intent_input: IntentInput) -> tuple[str, ...]:
    missing: list[str] = []
    context = intent_input.context_state
    if "history" in prerequisites and not context.has_history:
        missing.append("history")
    if "previous_answer" in prerequisites and not context.has_previous_answer:
        missing.append("previous_answer")
    return tuple(missing)


def _threshold_for_rule(match: RuleMatch) -> float:
    return {
        "high": 0.85,
        "medium": 0.6,
        "low": 0.6,
    }[match.strength]


def _score_for_strength(strength: str) -> float:
    return {
        "high": 0.9,
        "medium": 0.7,
        "low": 0.55,
    }.get(strength, 0.55)


def _model_calibration(model_result: ModelResult) -> CalibrationQuality:
    if model_result.low_confidence:
        return "weak"
    return "good" if model_result.confidence == "high" else "weak"


def _threshold_for_model_score(signal: str) -> float:
    if signal in {"unsupported"}:
        return 0.35
    if signal in {"out_of_scope"}:
        return 0.4
    if signal in {"ask_source", "soft_doubt", "history_reference", "referent_ambiguity", "target_ambiguity", "scope_ambiguity"}:
        return 0.2
    if signal in {"challenge", "missing_context"}:
        return 0.35
    if signal in {"needs_previous_answer"}:
        return 0.25
    return 0.5
