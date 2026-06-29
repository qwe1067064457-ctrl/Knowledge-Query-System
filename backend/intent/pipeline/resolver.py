from __future__ import annotations

from intent.schema.intent_types import (
    AmbiguityState,
    ContextDependency,
    DecisionTrace,
    IntentEvidence,
    IntentModifiers,
    ResolvedIntent,
    ResolvedTask,
    TaskCandidate,
)
from intent.schema.evidence_types import TypedEvidence


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
    if evidence.quality_report is not None:
        return _resolve_modifiers_from_quality(evidence)

    model_modifiers = evidence.model_result.modifiers if evidence.model_result else IntentModifiers()
    model_scores = evidence.model_result.modifier_scores if evidence.model_result else {}
    handling_mode_probs = evidence.model_result.handling_mode_probs if evidence.model_result else {}
    safety_scores = evidence.model_result.safety_scores if evidence.model_result else {}
    intent_signals = set(evidence.signal_buckets.intent)
    safety_signals = set(evidence.signal_buckets.safety)
    return IntentModifiers(
        follow_up=("follow_up" in intent_signals) or model_modifiers.follow_up or float(model_scores.get("follow_up", 0.0)) >= 0.5,
        challenge=(
            ("challenge" in intent_signals)
            or model_modifiers.challenge
            or float(model_scores.get("challenge", 0.0)) >= 0.35
            or float(handling_mode_probs.get("challenge", 0.0)) >= 0.6
        ),
        soft_doubt=("soft_doubt" in intent_signals) or model_modifiers.soft_doubt or float(model_scores.get("soft_doubt", 0.0)) >= 0.3,
        ask_source=("ask_source" in intent_signals) or model_modifiers.ask_source or float(model_scores.get("ask_source", 0.0)) >= 0.2,
        ask_capability=(
            ("ask_capability" in intent_signals)
            or model_modifiers.ask_capability
            or float(model_scores.get("ask_capability", 0.0)) >= 0.45
            or float(handling_mode_probs.get("scope_info", 0.0)) >= 0.55
        ),
        out_of_scope=(
            ("out_of_scope" in safety_signals)
            or model_modifiers.out_of_scope
            or float(model_scores.get("out_of_scope", 0.0)) >= 0.4
            or float(safety_scores.get("out_of_scope", 0.0)) >= 0.4
        ),
    )


def _resolve_modifiers_from_quality(evidence: IntentEvidence) -> IntentModifiers:
    """Resolve modifiers from the final gated evidence set."""

    signals = _trusted_truthy_signals(evidence)
    handling_modes = _trusted_values(evidence, "handling_mode")
    blocked_by_missing = (
        evidence.quality_report.case_level == "blocked_by_missing_prerequisite"
        if evidence.quality_report
        else False
    )
    missing_challenge = blocked_by_missing and any(
        match.rule_id.startswith("challenge.") for match in evidence.matched_rules
    )
    return IntentModifiers(
        follow_up="follow_up" in signals,
        challenge="challenge" in signals or "challenge" in handling_modes or missing_challenge,
        soft_doubt="soft_doubt" in signals,
        ask_source="ask_source" in signals,
        ask_capability="ask_capability" in signals or "scope_info" in handling_modes,
        out_of_scope=bool({"unsupported", "out_of_scope"} & signals),
    )


def _resolve_main_intent(evidence: IntentEvidence, modifiers: IntentModifiers) -> str:
    if evidence.quality_report and evidence.quality_report.case_level == "guard_required":
        return "unsupported"
    model_result = evidence.model_result
    if evidence.quality_report is None:
        if (
            modifiers.out_of_scope
            or any(evidence.unsupported_signals.values())
            or (model_result and float(model_result.safety_scores.get("unsupported", 0.0)) >= 0.35)
        ):
            return "unsupported"
    elif modifiers.out_of_scope:
        return "unsupported"
    if modifiers.ask_capability:
        return "system"
    if modifiers.challenge or modifiers.soft_doubt or modifiers.ask_source:
        return "qa"

    quality_intent = _resolve_main_intent_from_quality(evidence)
    if quality_intent:
        return quality_intent

    if evidence.quality_report is None and evidence.candidate_intents:
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

    candidates = _build_quality_task_candidates(evidence)
    if not candidates and evidence.quality_report is None:
        candidates = list(evidence.task_candidates)
        model_candidates = _build_model_task_candidates(evidence)
        if model_candidates:
            candidates.extend(model_candidates)
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


def _resolve_main_intent_from_quality(evidence: IntentEvidence) -> str | None:
    """Resolve route from gated evidence instead of raw legacy candidates."""

    ranked: list[tuple[int, float, str]] = []
    for item, trust_rank in _trusted_quality_evidence(evidence):
        value = _route_value_from_evidence(item)
        if not value:
            continue
        ranked.append((trust_rank, float(item.score or 0.0), value))
    if not ranked:
        return None
    return max(ranked, key=lambda item: (item[0], item[1]))[2]


def _route_value_from_evidence(item: TypedEvidence) -> str | None:
    if item.signal == "main_intent" and item.value in {"qa", "chat", "system", "unsupported"}:
        return str(item.value)
    if item.signal in {"qa", "chat", "system", "unsupported"} and item.value is True:
        return item.signal
    if item.signal == "out_of_scope" and item.value is True:
        return "unsupported"
    if item.signal == "handling_mode" and item.value == "scope_info":
        return "system"
    return None


def _build_quality_task_candidates(evidence: IntentEvidence) -> list[TaskCandidate]:
    """Build task candidates only from evidence that passed the quality gate."""

    candidates: list[TaskCandidate] = []
    head_values: dict[str, tuple[object, float]] = {}
    for item, trust_rank in _trusted_quality_evidence(evidence):
        score = float(item.score or 0.0) + trust_rank
        if item.signal == "task_candidate" and isinstance(item.value, dict):
            candidates.append(_task_candidate_from_value(item.value, float(item.score or 0.0)))
        elif item.signal in {"task_complexity", "task_shape", "task_topology"}:
            current = head_values.get(item.signal)
            if current is None or score > current[1]:
                head_values[item.signal] = (item.value, score)
        elif item.signal in {"multi_question", "parallel_subtasks", "staged", "complex"} and item.value is True:
            candidates.append(_task_candidate_from_signal(item.signal, float(item.score or 0.0)))

    if "task_shape" in head_values:
        shape = str(head_values["task_shape"][0])
        if shape != "none":
            complexity = str(head_values.get("task_complexity", ("simple", 0.0))[0])
            topology = str(head_values.get("task_topology", ("single", 0.0))[0])
            if topology == "single" and shape == "multi_question":
                topology = "parallel_queries"
            score_values = [value_score for _, value_score in head_values.values()]
            candidates.append(
                TaskCandidate(
                    complexity=complexity,
                    shape=shape,
                    topology=topology,
                    score=round(sum(score_values) / len(score_values), 6),
                )
            )
    return _dedupe_task_candidates(candidates)


def _trusted_quality_evidence(evidence: IntentEvidence) -> tuple[tuple[TypedEvidence, int], ...]:
    if evidence.quality_report is None:
        return ()
    trusted: list[tuple[TypedEvidence, int]] = []
    trusted.extend((item, 2) for item in evidence.quality_report.accepted_evidence)
    trusted.extend(
        (item, 1)
        for item in evidence.quality_report.downgraded_evidence
        if _can_use_downgraded_evidence(evidence, item)
    )
    return tuple(trusted)


def _can_use_downgraded_evidence(evidence: IntentEvidence, item: TypedEvidence) -> bool:
    if evidence.adjudication_result is not None:
        return True
    if not evidence.quality_report or evidence.quality_report.case_level != "requires_adjudication":
        return True
    return not (item.source == "small_model" and item.criticality in {"route", "task_shape", "context_dependency", "safety"})


def _task_candidate_from_value(value: dict[str, object], score: float) -> TaskCandidate:
    return TaskCandidate(
        complexity=str(value.get("complexity", "simple")),
        shape=str(value.get("shape", "single_question")),
        topology=str(value.get("topology", "single")),
        score=score or float(value.get("score", 0.0) or 0.0),
    )


def _task_candidate_from_signal(signal: str, score: float) -> TaskCandidate:
    if signal == "multi_question":
        return TaskCandidate(complexity="compound", shape="multi_question", topology="parallel_queries", score=score)
    if signal == "parallel_subtasks":
        return TaskCandidate(complexity="compound", shape="multi_question", topology="parallel_subtasks", score=score)
    if signal == "staged":
        return TaskCandidate(complexity="complex", shape="single_question", topology="staged", score=score)
    if signal == "complex":
        return TaskCandidate(complexity="complex", shape="single_question", topology="single", score=score)
    return TaskCandidate(complexity="simple", shape="single_question", topology="single", score=score)


def _dedupe_task_candidates(candidates: list[TaskCandidate]) -> list[TaskCandidate]:
    deduped: dict[tuple[str, str, str], TaskCandidate] = {}
    for candidate in candidates:
        key = (candidate.complexity, candidate.shape, candidate.topology)
        current = deduped.get(key)
        if current is None or candidate.score > current.score:
            deduped[key] = candidate
    return list(deduped.values())


def _build_model_task_candidates(evidence: IntentEvidence) -> list[TaskCandidate]:
    model_result = evidence.model_result
    if model_result is None:
        return []
    if not model_result.task_shape_probs:
        return []
    complexity = _top_label(model_result.task_complexity_probs, default="simple")
    topology = _top_label(model_result.task_topology_probs, default="single")
    shape_candidates = [
        (label, score)
        for label, score in sorted(model_result.task_shape_probs.items(), key=lambda item: item[1], reverse=True)
        if label != "none" and score >= 0.12
    ]
    candidates: list[TaskCandidate] = []
    for shape, score in shape_candidates[:2]:
        normalized_topology = topology
        if normalized_topology == "single" and shape == "multi_question":
            normalized_topology = "parallel_queries"
        candidates.append(
            TaskCandidate(
                complexity=complexity,
                shape=shape,
                topology=normalized_topology,
                score=float(score),
            )
        )
    if topology == "staged" and shape_candidates:
        top_shape, top_score = shape_candidates[0]
        candidates.append(
            TaskCandidate(
                complexity="complex",
                shape=top_shape,
                topology="staged",
                score=float(max(top_score, model_result.task_topology_probs.get("staged", 0.0))),
            )
        )
    return candidates


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
        if any(item.topology == "parallel_queries" for item in candidates):
            return "parallel_queries"
        return "single"
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
        non_multi = [
            item
            for item in candidates
            if item.complexity == "compound" and item.shape != "multi_question"
        ]
        if non_multi:
            return max(non_multi, key=lambda item: item.score).shape

    best = max(candidates, key=lambda item: item.score)
    return best.shape


def _top_label(scores: dict[str, float], *, default: str) -> str:
    if not scores:
        return default
    return max(scores.items(), key=lambda item: item[1])[0]


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
    if evidence.quality_report is not None:
        return _resolve_context_dependency_from_quality(evidence, modifiers)

    context = evidence.context_signals
    model_result = evidence.model_result
    context_dependency_probs = model_result.context_dependency_probs if model_result else {}
    context_scores = model_result.context_scores if model_result else {}
    if modifiers.challenge:
        if context.needs_previous_answer:
            return "previous_answer"
        if context.ambiguous:
            return "ambiguous"
        if float(context_dependency_probs.get("global", 0.0)) >= 0.4:
            return "previous_answer"
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
    if float(context_scores.get("previous_retrieval", 0.0)) >= 0.5:
        return "previous_retrieval"
    if float(context_scores.get("needs_previous_answer", 0.0)) >= 0.25 or float(context_dependency_probs.get("global", 0.0)) >= 0.45:
        return "previous_answer"
    if float(context_scores.get("history_reference", 0.0)) >= 0.2 or float(context_dependency_probs.get("partial", 0.0)) >= 0.45:
        return "history_reference"
    if context.ambiguous or context.has_implicit_history:
        return "ambiguous"
    return "none"


def _resolve_context_dependency_from_quality(
    evidence: IntentEvidence,
    modifiers: IntentModifiers,
) -> ContextDependency:
    """Resolve context dependency from gated context evidence only."""

    signals = _trusted_truthy_signals(evidence)
    dependency_values = _trusted_values(evidence, "context_dependency")
    if modifiers.challenge:
        return "previous_answer"
    if modifiers.follow_up:
        if "previous_retrieval" in signals:
            return "previous_retrieval"
        if "needs_previous_answer" in signals or "global" in dependency_values:
            return "previous_answer"
        return "history_reference"
    if "previous_retrieval" in signals:
        return "previous_retrieval"
    if "needs_previous_answer" in signals or "global" in dependency_values:
        return "previous_answer"
    if "history_reference" in signals or "partial" in dependency_values:
        return "history_reference"
    if "clarify_hint" in signals:
        return "ambiguous"
    return "none"


def _resolve_ambiguity_state(evidence: IntentEvidence) -> AmbiguityState:
    context = evidence.context_signals
    model_result = evidence.model_result
    ambiguity_scores = model_result.ambiguity_scores if model_result else {}
    context_scores = model_result.context_scores if model_result else {}
    ambiguity_states = list(context.ambiguity_states)
    if evidence.quality_report and evidence.quality_report.case_level == "blocked_by_missing_prerequisite":
        if context.clarify_hint:
            return AmbiguityState(
                clarify_hint=context.clarify_hint,
                needs_previous_answer=context.needs_previous_answer,
                ambiguity_states=context.ambiguity_states,
                missing_context_types=context.missing_context_types,
            )
        missing_context_types = context.missing_context_types
        for missing in evidence.quality_report.missing_prerequisites:
            missing_context_types = _append_unique_tuple(missing_context_types, f"missing_{missing}")
        ambiguity_states = list(_append_unique_tuple(tuple(ambiguity_states), "evidence_prerequisite_missing"))
        return AmbiguityState(
            clarify_hint=True,
            needs_previous_answer=context.needs_previous_answer or "previous_answer" in evidence.quality_report.missing_prerequisites,
            ambiguity_states=tuple(ambiguity_states),
            missing_context_types=missing_context_types,
        )
    if float(ambiguity_scores.get("referent_ambiguity", 0.0)) >= 0.25 and "referent_ambiguity" not in ambiguity_states:
        ambiguity_states.append("referent_ambiguity")
    if float(ambiguity_scores.get("target_ambiguity", 0.0)) >= 0.2 and "target_ambiguity" not in ambiguity_states:
        ambiguity_states.append("target_ambiguity")
    if float(ambiguity_scores.get("scope_ambiguity", 0.0)) >= 0.2 and "scope_ambiguity" not in ambiguity_states:
        ambiguity_states.append("scope_ambiguity")
    if float(ambiguity_scores.get("missing_context", 0.0)) >= 0.35 and "missing_context" not in ambiguity_states:
        ambiguity_states.append("missing_context")
    return AmbiguityState(
        clarify_hint=context.clarify_hint or float(context_scores.get("clarify_hint", 0.0)) >= 0.45,
        needs_previous_answer=context.needs_previous_answer or float(context_scores.get("needs_previous_answer", 0.0)) >= 0.25,
        ambiguity_states=tuple(ambiguity_states),
        missing_context_types=context.missing_context_types,
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
    if evidence.quality_report:
        reason_parts.append(f"quality_gate={evidence.quality_report.case_level}")
    if evidence.adjudication_result:
        reason_parts.append("adjudication=" + evidence.adjudication_result.fallback_recommendation)
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


def _append_unique_tuple(values: tuple[str, ...], value: str) -> tuple[str, ...]:
    if value in values:
        return values
    return (*values, value)


def _trusted_truthy_signals(evidence: IntentEvidence) -> set[str]:
    return {
        item.signal
        for item, _ in _trusted_quality_evidence(evidence)
        if item.value is True
    }


def _trusted_values(evidence: IntentEvidence, signal: str) -> set[str]:
    return {
        str(item.value)
        for item, _ in _trusted_quality_evidence(evidence)
        if item.signal == signal and item.value
    }
