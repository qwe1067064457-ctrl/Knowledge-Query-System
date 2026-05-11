from __future__ import annotations

from intent.types import (
    CandidateIntent,
    ContextDependency,
    DecisionTrace,
    IntentEvidence,
    IntentModifiers,
    ResolvedIntent,
    ResolvedTask,
    TaskCandidate,
)


def resolve_intent(evidence: IntentEvidence) -> ResolvedIntent:
    modifiers = _resolve_modifiers(evidence)
    main_intent = _resolve_main_intent(evidence, modifiers)
    task = _resolve_task(evidence, main_intent, modifiers)
    context_dependency = _resolve_context_dependency(evidence, modifiers)
    decision = _resolve_decision(evidence, main_intent, task, modifiers, context_dependency)
    return ResolvedIntent(
        main_intent=main_intent,
        modifiers=modifiers,
        task=task,
        context_dependency=context_dependency,
        decision=decision,
    )


def _resolve_modifiers(evidence: IntentEvidence) -> IntentModifiers:
    model_modifiers = evidence.model_result.modifiers if evidence.model_result else IntentModifiers()
    raw = set(evidence.raw_signals)
    return IntentModifiers(
        follow_up=("follow_up" in raw) or model_modifiers.follow_up,
        challenge=("challenge" in raw) or model_modifiers.challenge,
        ask_source=("ask_source" in raw) or model_modifiers.ask_source,
        ask_capability=("ask_capability" in raw) or model_modifiers.ask_capability,
        needs_clarification=("needs_clarification" in raw) or model_modifiers.needs_clarification,
        out_of_scope=("out_of_scope" in raw) or model_modifiers.out_of_scope,
    )


def _resolve_main_intent(evidence: IntentEvidence, modifiers: IntentModifiers) -> str:
    if modifiers.out_of_scope or any(evidence.unsupported_signals.values()):
        return "unsupported"
    if modifiers.ask_capability:
        return "system"
    if modifiers.challenge or modifiers.ask_source:
        return "qa"

    if evidence.candidate_intents:
        return max(evidence.candidate_intents, key=lambda item: item.score).intent

    raw = set(evidence.raw_signals)
    if "qa" in raw:
        return "qa"
    if "system" in raw:
        return "system"
    if "unsupported" in raw:
        return "unsupported"
    return "chat"


def _resolve_task(
    evidence: IntentEvidence,
    main_intent: str,
    modifiers: IntentModifiers,
) -> ResolvedTask:
    if main_intent in {"chat", "system", "unsupported"}:
        return ResolvedTask(complexity="simple", shape="none")

    candidates = list(evidence.task_candidates)
    if modifiers.challenge:
        return ResolvedTask(
            complexity="simple",
            shape="verify",
            needs_query_decomposition=False,
            needs_agent_planning=False,
        )
    if not candidates:
        shape = "single_question" if "multi_question" not in evidence.raw_signals else "multi_question"
        complexity = "compound" if shape == "multi_question" else "simple"
        return ResolvedTask(
            complexity=complexity,
            shape=shape,
            needs_query_decomposition=shape == "multi_question",
            needs_agent_planning=False,
        )

    complexity = _resolve_complexity(candidates)
    shape = _resolve_shape(candidates, complexity)
    return ResolvedTask(
        complexity=complexity,
        shape=shape,
        needs_query_decomposition=complexity == "compound" and shape == "multi_question",
        needs_agent_planning=complexity == "complex",
    )


def _resolve_complexity(candidates: list[TaskCandidate]) -> str:
    order = {"simple": 0, "compound": 1, "complex": 2}
    return max(candidates, key=lambda item: (order[item.complexity], item.score)).complexity


def _resolve_shape(candidates: list[TaskCandidate], complexity: str) -> str:
    if complexity == "complex":
        non_multi = [item for item in candidates if item.shape != "multi_question"]
        if not non_multi:
            return "mixed"
        best = max(non_multi, key=lambda item: item.score)
        return "mixed" if best.shape == "single_question" else best.shape

    best = max(candidates, key=lambda item: item.score)
    return best.shape


def _resolve_context_dependency(
    evidence: IntentEvidence,
    modifiers: IntentModifiers,
) -> ContextDependency:
    if modifiers.challenge:
        return "previous_answer"
    if modifiers.follow_up:
        if evidence.dependency_signals.get("previous_retrieval"):
            return "previous_retrieval"
        if evidence.dependency_signals.get("previous_answer"):
            return "previous_answer"
        if evidence.dependency_signals.get("history_reference"):
            return "history_reference"
        return "history_reference"

    for candidate in (
        "previous_retrieval",
        "previous_answer",
        "history_reference",
        "ambiguous",
    ):
        if evidence.dependency_signals.get(candidate):
            return candidate
    return "none"


def _resolve_decision(
    evidence: IntentEvidence,
    main_intent: str,
    task: ResolvedTask,
    modifiers: IntentModifiers,
    context_dependency: ContextDependency,
) -> DecisionTrace:
    if evidence.model_result and evidence.matched_rules:
        source = "hybrid"
    elif evidence.model_result:
        source = "model"
    elif evidence.matched_rules:
        source = "rule"
    else:
        source = "fallback"

    strengths = [match.strength for match in evidence.matched_rules]
    if evidence.model_result:
        strengths.append(evidence.model_result.confidence)
    strength = _max_strength(strengths) if strengths else "low"

    active_modifiers = [name for name, enabled in modifiers.to_dict().items() if enabled]
    reason_parts = [f"main_intent={main_intent}", f"task={task.complexity}/{task.shape}"]
    if active_modifiers:
        reason_parts.append("modifiers=" + ",".join(active_modifiers))
    if context_dependency != "none":
        reason_parts.append(f"context={context_dependency}")
    if source == "rule" and evidence.matched_rules:
        reason_parts.append("rules=" + ",".join(match.rule_id for match in evidence.matched_rules[:3]))
    if source in {"model", "hybrid"} and evidence.model_result and evidence.model_result.reason:
        reason_parts.append("model=" + evidence.model_result.reason)
    return DecisionTrace(
        strength=strength,
        source=source,
        reason="; ".join(reason_parts),
    )


def _max_strength(strengths: list[str]) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return max(strengths, key=lambda item: order[item])
