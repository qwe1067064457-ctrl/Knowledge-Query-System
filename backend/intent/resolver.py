from __future__ import annotations

from intent.types import (
    AmbiguityState,
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
    ambiguity_state = _resolve_ambiguity_state(evidence)
    decision = _resolve_decision(evidence, main_intent, task, modifiers, context_dependency)
    return ResolvedIntent(
        main_intent=main_intent,
        modifiers=modifiers,
        task=task,
        context_dependency=context_dependency,
        ambiguity_state=ambiguity_state,
        decision=decision,
    )


def _resolve_modifiers(evidence: IntentEvidence) -> IntentModifiers:
    model_modifiers = evidence.model_result.modifiers if evidence.model_result else IntentModifiers()
    intent_signals = set(evidence.signal_buckets.intent)
    safety_signals = set(evidence.signal_buckets.safety)
    context = evidence.context_signals
    clarify_candidate = context.needs_context_check or model_modifiers.clarify_candidate
    scope_question = ("scope_question" in intent_signals) or model_modifiers.scope_question
    return IntentModifiers(
        follow_up=("follow_up" in intent_signals) or model_modifiers.follow_up,
        challenge=("challenge" in intent_signals) or model_modifiers.challenge,
        soft_doubt=("soft_doubt" in intent_signals) or model_modifiers.soft_doubt,
        ask_source=("ask_source" in intent_signals) or model_modifiers.ask_source,
        ask_capability=("ask_capability" in intent_signals) or scope_question or model_modifiers.ask_capability,
        scope_question=scope_question,
        clarify_candidate=clarify_candidate,
        needs_clarification=clarify_candidate or model_modifiers.needs_clarification,
        out_of_scope=("out_of_scope" in safety_signals) or model_modifiers.out_of_scope,
    )


def _resolve_main_intent(evidence: IntentEvidence, modifiers: IntentModifiers) -> str:
    if modifiers.out_of_scope or any(evidence.unsupported_signals.values()):
        return "unsupported"
    if modifiers.ask_capability:
        return "system"
    if modifiers.challenge or modifiers.soft_doubt or modifiers.ask_source:
        return "qa"

    if evidence.candidate_intents:
        return max(evidence.candidate_intents, key=lambda item: item.score).intent

    intent_signals = set(evidence.signal_buckets.intent)
    safety_signals = set(evidence.signal_buckets.safety)
    if "qa" in intent_signals:
        return "qa"
    if "system" in intent_signals:
        return "system"
    if "unsupported" in safety_signals:
        return "unsupported"
    return "chat"


def _resolve_task(
    evidence: IntentEvidence,
    main_intent: str,
    modifiers: IntentModifiers,
) -> ResolvedTask:
    if main_intent in {"chat", "system", "unsupported"}:
        return ResolvedTask(complexity="simple", shape="none", topology="single")

    candidates = list(evidence.task_candidates)
    if modifiers.challenge:
        return ResolvedTask(
            complexity="simple",
            shape="verify",
            topology="single",
        )
    if not candidates:
        task_signals = set(evidence.signal_buckets.task)
        topology = _fallback_topology(task_signals)
        shape = "multi_question" if topology in {"parallel_queries", "parallel_subtasks"} else "single_question"
        complexity = "compound" if topology in {"parallel_queries", "parallel_subtasks"} else "simple"
        return ResolvedTask(
            complexity=complexity,
            shape=shape,
            topology=topology,
        )

    complexity = _resolve_complexity(candidates)
    topology = _resolve_topology(candidates, complexity)
    shape = _resolve_shape(candidates, complexity, topology)
    return ResolvedTask(
        complexity=complexity,
        shape=shape,
        topology=topology,
    )


def _resolve_complexity(candidates: list[TaskCandidate]) -> str:
    complex_candidates = [item for item in candidates if item.complexity == "complex"]
    parallel_candidates = [
        item for item in candidates if item.topology in {"parallel_queries", "parallel_subtasks"}
    ]
    if any(item.topology == "staged" for item in candidates):
        return "complex"
    if any(item.complexity == "complex" and item.shape in {"compare", "mixed"} for item in candidates):
        return "complex"
    if parallel_candidates and complex_candidates:
        best_complex = max(complex_candidates, key=lambda item: item.score)
        if best_complex.shape in {"verify", "extract", "summarize", "mixed"} and best_complex.score >= 0.8:
            return "complex"
        return "compound"
    if parallel_candidates:
        return "compound"
    if complex_candidates:
        return "complex"
    if any(item.complexity == "compound" for item in candidates):
        return "compound"
    return "simple"


def _resolve_topology(candidates: list[TaskCandidate], complexity: str) -> str:
    if complexity == "complex":
        if any(item.topology == "staged" for item in candidates):
            return "staged"
        return "single"
    if complexity == "compound":
        if any(item.topology == "parallel_subtasks" for item in candidates):
            return "parallel_subtasks"
        return "parallel_queries"
    return "single"


def _resolve_shape(candidates: list[TaskCandidate], complexity: str, topology: str) -> str:
    if complexity == "complex":
        non_multi = [
            item
            for item in candidates
            if item.complexity == "complex" and item.shape != "multi_question"
        ]
        if not non_multi:
            return "single_question"
        if any(item.shape == "mixed" for item in non_multi):
            return "mixed"

        shape_scores: dict[str, float] = {}
        for item in non_multi:
            shape_scores[item.shape] = max(shape_scores.get(item.shape, 0.0), item.score)

        ranked_shapes = sorted(shape_scores.items(), key=lambda item: item[1], reverse=True)
        best_shape, best_score = ranked_shapes[0]
        named_ranked = [item for item in ranked_shapes if item[0] != "single_question"]
        if len(named_ranked) >= 2:
            (_, top_named_score), (_, second_named_score) = named_ranked[0], named_ranked[1]
            if top_named_score >= 0.75 and second_named_score >= 0.75 and abs(top_named_score - second_named_score) <= 0.1:
                return "mixed"
        if best_shape == "single_question" and named_ranked and named_ranked[0][1] >= 0.7:
            return named_ranked[0][0]
        return best_shape

    if complexity == "compound":
        if topology in {"parallel_queries", "parallel_subtasks"}:
            return "multi_question"

    best = max(candidates, key=lambda item: item.score)
    return best.shape


def _fallback_topology(task_signals: set[str]) -> str:
    if "staged" in task_signals:
        return "staged"
    if "parallel_subtasks" in task_signals:
        return "parallel_subtasks"
    if "multi_question" in task_signals:
        return "parallel_queries"
    return "single"


def _resolve_context_dependency(
    evidence: IntentEvidence,
    modifiers: IntentModifiers,
) -> ContextDependency:
    context = evidence.context_signals
    if modifiers.challenge:
        if context.needs_previous_answer:
            return "previous_answer"
        if context.possibly_ambiguous or context.needs_context_check:
            return "ambiguous"
        return "previous_answer"
    if modifiers.follow_up:
        if context.previous_retrieval:
            return "previous_retrieval"
        if context.needs_previous_answer:
            return "previous_answer"
        if context.history_reference:
            return "history_reference"
        return "history_reference"

    if context.previous_retrieval:
        return "previous_retrieval"
    if context.needs_previous_answer:
        return "previous_answer"
    if context.history_reference:
        return "history_reference"
    if context.ambiguous or context.has_implicit_history:
        return "ambiguous"
    return "none"


def _resolve_ambiguity_state(evidence: IntentEvidence) -> AmbiguityState:
    context = evidence.context_signals
    return AmbiguityState(
        clarify_candidate=context.needs_context_check,
        needs_context_check=context.needs_context_check,
        needs_previous_answer=context.needs_previous_answer,
        missing_reference_target=context.missing_reference_target,
        possibly_ambiguous=context.possibly_ambiguous,
    )


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
    if evidence.rule_confidence:
        strengths.append(evidence.rule_confidence.final_level)
    if evidence.model_result:
        strengths.append(evidence.model_result.confidence)
    strength = _max_strength(strengths) if strengths else "low"

    active_modifiers = [name for name, enabled in modifiers.to_dict().items() if enabled]
    reason_parts = [
        f"main_intent={main_intent}",
        f"task={task.complexity}/{task.shape}/{task.topology}",
    ]
    if active_modifiers:
        reason_parts.append("modifiers=" + ",".join(active_modifiers))
    if context_dependency != "none":
        reason_parts.append(f"context={context_dependency}")
    if source == "rule" and evidence.matched_rules:
        reason_parts.append("rules=" + ",".join(match.rule_id for match in evidence.matched_rules[:3]))
    if evidence.rule_confidence and evidence.rule_confidence.final_signal:
        reason_parts.append(
            f"rule_confidence={evidence.rule_confidence.final_signal}/{evidence.rule_confidence.final_level}"
        )
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
