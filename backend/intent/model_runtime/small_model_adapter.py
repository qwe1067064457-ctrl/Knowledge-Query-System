from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from intent.model_runtime.local_multitask_runtime import LocalMultitaskRuntime, RuntimePrediction
from intent.schema.intent_types import CandidateIntent, IntentModifiers, ModelResult, TaskCandidate


@dataclass
class LocalIntentModelAdapter:
    runtime: LocalMultitaskRuntime
    thresholds: dict[str, dict[str, float]]

    def predict(self, intent_input, history: Iterable[dict[str, object]]) -> ModelResult | None:
        prediction = self.runtime.predict(intent_input.user_query)
        return build_model_result(prediction=prediction, thresholds=self.thresholds)


def build_model_result(
    *,
    prediction: RuntimePrediction,
    thresholds: dict[str, dict[str, float]],
) -> ModelResult:
    main_intent_probs = prediction.multiclass_probs.get("main_intent", {})
    task_complexity_probs = prediction.multiclass_probs.get("task_complexity", {})
    task_shape_probs = prediction.multiclass_probs.get("task_shape", {})
    task_topology_probs = prediction.multiclass_probs.get("task_topology", {})
    context_dependency_probs = prediction.multiclass_probs.get("context_dependency", {})
    handling_mode_probs = prediction.multiclass_probs.get("handling_mode", {})
    modifier_scores = prediction.multilabel_scores.get("modifiers", {})
    context_scores = prediction.multilabel_scores.get("context", {})
    safety_scores = prediction.multilabel_scores.get("safety", {})
    ambiguity_scores = prediction.multilabel_scores.get("ambiguity_states", {})

    modifiers = IntentModifiers(
        follow_up=_passes_threshold(modifier_scores, thresholds, "modifiers", "follow_up"),
        challenge=_passes_threshold(modifier_scores, thresholds, "modifiers", "challenge"),
        soft_doubt=_passes_threshold(modifier_scores, thresholds, "modifiers", "soft_doubt"),
        ask_source=_passes_threshold(modifier_scores, thresholds, "modifiers", "ask_source"),
        ask_capability=_passes_threshold(modifier_scores, thresholds, "modifiers", "ask_capability"),
        out_of_scope=_passes_threshold(safety_scores, thresholds, "safety", "out_of_scope"),
    )

    candidate_intents = tuple(
        CandidateIntent(intent=label, score=score)
        for label, score in _top_items(main_intent_probs, limit=2)
        if score >= 0.1
    )
    task_candidates = _build_task_candidates(
        task_complexity_probs=task_complexity_probs,
        task_shape_probs=task_shape_probs,
        task_topology_probs=task_topology_probs,
    )
    top_k = {
        "main_intent": _top_items(main_intent_probs),
        "task_complexity": _top_items(task_complexity_probs),
        "task_shape": _top_items(task_shape_probs),
        "task_topology": _top_items(task_topology_probs),
        "context_dependency": _top_items(context_dependency_probs),
        "handling_mode": _top_items(handling_mode_probs),
    }
    margins = {
        name: _margin(items)
        for name, items in top_k.items()
    }
    low_confidence = _is_low_confidence(
        top_k=top_k,
        margins=margins,
        handling_mode_probs=handling_mode_probs,
        task_shape_probs=task_shape_probs,
        task_topology_probs=task_topology_probs,
        ambiguity_scores=ambiguity_scores,
        modifier_scores=modifier_scores,
    )

    return ModelResult(
        valid=True,
        candidate_intents=candidate_intents,
        modifiers=modifiers,
        task_candidates=task_candidates,
        context_dependency=_map_context_dependency(context_dependency_probs, context_scores),
        main_intent_probs=main_intent_probs,
        task_complexity_probs=task_complexity_probs,
        task_shape_probs=task_shape_probs,
        task_topology_probs=task_topology_probs,
        context_dependency_probs=context_dependency_probs,
        handling_mode_probs=handling_mode_probs,
        modifier_scores=modifier_scores,
        context_scores=context_scores,
        safety_scores=safety_scores,
        ambiguity_scores=ambiguity_scores,
        top_k=top_k,
        margins=margins,
        low_confidence=low_confidence,
        confidence=_confidence_level(top_k=top_k, margins=margins, low_confidence=low_confidence),
        reason=_build_reason(top_k=top_k, low_confidence=low_confidence),
    )


def _build_task_candidates(
    *,
    task_complexity_probs: dict[str, float],
    task_shape_probs: dict[str, float],
    task_topology_probs: dict[str, float],
) -> tuple[TaskCandidate, ...]:
    complexity_top = _top_items(task_complexity_probs, limit=2)
    shape_top = [item for item in _top_items(task_shape_probs, limit=3) if item[0] != "none" and item[1] >= 0.12]
    topology_top = [item for item in _top_items(task_topology_probs, limit=2) if item[1] >= 0.12]
    if not complexity_top or not shape_top or not topology_top:
        return ()

    candidates: list[TaskCandidate] = []
    for complexity_label, complexity_score in complexity_top[:1]:
        for shape_label, shape_score in shape_top[:2]:
            for topology_label, topology_score in topology_top[:2]:
                if topology_label == "single" and shape_label == "multi_question":
                    topology_label = "parallel_queries"
                combined = round((complexity_score + shape_score + topology_score) / 3, 6)
                candidates.append(
                    TaskCandidate(
                        complexity=complexity_label,
                        shape=shape_label,
                        topology=topology_label,
                        score=combined,
                    )
                )
    deduped: dict[tuple[str, str, str], TaskCandidate] = {}
    for candidate in candidates:
        key = (candidate.complexity, candidate.shape, candidate.topology)
        current = deduped.get(key)
        if current is None or candidate.score > current.score:
            deduped[key] = candidate
    ranked = sorted(deduped.values(), key=lambda item: item.score, reverse=True)
    return tuple(ranked[:4])


def _passes_threshold(scores: dict[str, float], thresholds: dict[str, dict[str, float]], head: str, label: str) -> bool:
    return float(scores.get(label, 0.0)) >= float(thresholds.get(head, {}).get(label, 0.5))


def _top_items(scores: dict[str, float], limit: int = 2) -> tuple[tuple[str, float], ...]:
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return tuple((label, float(score)) for label, score in ranked[:limit])


def _margin(items: tuple[tuple[str, float], ...]) -> float:
    if len(items) < 2:
        return items[0][1] if items else 0.0
    return float(items[0][1] - items[1][1])


def _map_context_dependency(
    context_dependency_probs: dict[str, float],
    context_scores: dict[str, float],
) -> str:
    top = _top_items(context_dependency_probs, limit=1)
    if not top:
        return "none"
    label = top[0][0]
    if label == "global":
        return "previous_answer"
    if label == "partial":
        if float(context_scores.get("previous_retrieval", 0.0)) >= 0.5:
            return "previous_retrieval"
        if float(context_scores.get("needs_previous_answer", 0.0)) >= float(context_scores.get("history_reference", 0.0)):
            return "previous_answer"
        return "history_reference"
    return "none"


def _is_low_confidence(
    *,
    top_k: dict[str, tuple[tuple[str, float], ...]],
    margins: dict[str, float],
    handling_mode_probs: dict[str, float],
    task_shape_probs: dict[str, float],
    task_topology_probs: dict[str, float],
    ambiguity_scores: dict[str, float],
    modifier_scores: dict[str, float],
) -> bool:
    critical_heads = ("task_shape", "task_topology", "handling_mode", "context_dependency")
    for head in critical_heads:
        best = top_k.get(head, ())
        if not best or best[0][1] < 0.55 or margins.get(head, 0.0) < 0.12:
            return True
    if float(handling_mode_probs.get("scope_info", 0.0)) >= 0.25 and margins.get("handling_mode", 0.0) < 0.2:
        return True
    if float(task_shape_probs.get("compare", 0.0)) >= 0.2 and margins.get("task_shape", 0.0) < 0.2:
        return True
    if float(task_shape_probs.get("mixed", 0.0)) >= 0.2 and margins.get("task_shape", 0.0) < 0.2:
        return True
    if float(task_topology_probs.get("staged", 0.0)) >= 0.15 and margins.get("task_topology", 0.0) < 0.25:
        return True
    if max(ambiguity_scores.values(), default=0.0) >= 0.2:
        return True
    if float(modifier_scores.get("ask_source", 0.0)) >= 0.15 and float(modifier_scores.get("challenge", 0.0)) >= 0.15:
        return True
    return False


def _confidence_level(
    *,
    top_k: dict[str, tuple[tuple[str, float], ...]],
    margins: dict[str, float],
    low_confidence: bool,
) -> str:
    if low_confidence:
        return "low"
    min_top = min((items[0][1] for items in top_k.values() if items), default=0.0)
    min_margin = min((score for score in margins.values()), default=0.0)
    if min_top >= 0.75 and min_margin >= 0.25:
        return "high"
    return "medium"


def _build_reason(*, top_k: dict[str, tuple[tuple[str, float], ...]], low_confidence: bool) -> str:
    fragments: list[str] = []
    for head in ("main_intent", "task_shape", "task_topology", "handling_mode"):
        items = top_k.get(head, ())
        if items:
            fragments.append(f"{head}={items[0][0]}:{items[0][1]:.2f}")
    if low_confidence:
        fragments.append("fallback_candidate=true")
    return ";".join(fragments)
