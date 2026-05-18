from __future__ import annotations

from typing import Any

from intent.task_compat import infer_topology_from_legacy_task


def infer_context_signals_from_dependency(dependency_signals: dict[str, Any]) -> dict[str, Any]:
    ambiguity_states: list[str] = []
    missing_context_types: list[str] = []
    if dependency_signals.get("ambiguous", False):
        ambiguity_states.append("history_dependent")
        missing_context_types.append("missing_history_target")
    clarify_hint = bool(ambiguity_states)
    return {
        "history_reference": bool(dependency_signals.get("history_reference", False)),
        "needs_previous_answer": bool(dependency_signals.get("previous_answer", False)),
        "previous_answer": bool(dependency_signals.get("previous_answer", False)),
        "previous_retrieval": bool(dependency_signals.get("previous_retrieval", False)),
        "clarify_hint": clarify_hint,
        "ambiguity_states": ambiguity_states,
        "missing_context_types": missing_context_types,
        "ambiguous": clarify_hint,
        "has_reference": bool(dependency_signals.get("history_reference", False)),
        "has_previous_intent": bool(
            dependency_signals.get("history_reference", False)
            or dependency_signals.get("previous_answer", False)
            or dependency_signals.get("previous_retrieval", False)
        ),
        "has_implicit_history": "history_dependent" in ambiguity_states,
        "is_direct_followup": bool(dependency_signals.get("history_reference", False)),
    }


def infer_signal_buckets_from_v1(evidence: dict[str, Any]) -> dict[str, list[str]]:
    required_signals = list(evidence.get("required_signals", []))
    dependency_signals = evidence.get("dependency_signals", {})
    unsupported_signals = evidence.get("unsupported_signals", {})

    intent_signals = [
        signal
        for signal in required_signals
        if signal in {"qa", "chat", "system", "ask_capability", "follow_up", "ask_source", "challenge", "soft_doubt"}
    ]
    task_signals = [signal for signal in required_signals if signal in {"multi_question", "complex", "parallel_subtasks", "staged"}]
    context_signals: list[str] = []
    if dependency_signals.get("history_reference"):
        context_signals.append("history_reference")
        if "follow_up" not in intent_signals:
            intent_signals.append("follow_up")
    if dependency_signals.get("previous_answer"):
        context_signals.append("needs_previous_answer")
    if dependency_signals.get("previous_retrieval"):
        context_signals.append("previous_retrieval")
    if dependency_signals.get("ambiguous"):
        context_signals.append("clarify_hint")
    safety_signals = ["unsupported", "out_of_scope"] if any(bool(value) for value in unsupported_signals.values()) else []
    return {
        "intent": _unique(intent_signals),
        "task": _unique(task_signals),
        "context": _unique(context_signals),
        "safety": _unique(safety_signals),
    }


def serialize_evidence_v2(evidence: dict[str, Any]) -> dict[str, Any]:
    dependency_signals = evidence.get("dependency_signals", {})
    return {
        "classifier_mode": evidence.get("classifier_mode", "rule_plus_model"),
        "required_signals": list(evidence.get("required_signals", [])),
        "required_rule_ids": list(evidence.get("required_rule_ids", [])),
        "rule_expectations": dict(evidence.get("rule_expectations", {})),
        "unsupported_signals": dict(evidence.get("unsupported_signals", {})),
        "signal_buckets": evidence.get("signal_buckets") or infer_signal_buckets_from_v1(evidence),
        "context_signals": evidence.get("context_signals") or infer_context_signals_from_dependency(dependency_signals),
        "candidate_intents": list(evidence.get("candidate_intents", [])),
        "task_candidates": list(evidence.get("task_candidates", [])),
    }


def serialize_resolved_v2(resolved: dict[str, Any]) -> dict[str, Any]:
    task = dict(resolved.get("task", {}))
    modifiers = dict(resolved.get("modifiers", {}))
    context_dependency = resolved.get("context_dependency", "none")
    clarify_hint = bool(
        resolved.get("ambiguity_state", {}).get("clarify_hint")
        or context_dependency == "ambiguous"
    )
    needs_previous_answer = context_dependency == "previous_answer"
    ambiguity_states = list(resolved.get("ambiguity_state", {}).get("ambiguity_states", []))
    if context_dependency == "ambiguous" and not ambiguity_states:
        ambiguity_states.append("history_dependent")
    missing_context_types = list(resolved.get("ambiguity_state", {}).get("missing_context_types", []))
    if clarify_hint and not missing_context_types and context_dependency == "ambiguous":
        missing_context_types.append("missing_history_target")
    return {
        "main_intent": resolved.get("main_intent", "chat"),
        "modifiers": modifiers,
        "task": {
            "complexity": task.get("complexity", "simple"),
            "shape": task.get("shape", "none"),
            "topology": infer_topology_from_legacy_task(task),
        },
        "context_dependency": context_dependency,
        "ambiguity_state": {
            "clarify_hint": clarify_hint,
            "needs_previous_answer": needs_previous_answer,
            "ambiguity_states": ambiguity_states,
            "missing_context_types": missing_context_types,
        },
    }


def should_review_for_v2(row: dict[str, Any]) -> bool:
    gold = row.get("gold", row)
    resolved = gold.get("resolved", {})
    task = resolved.get("task", {})
    modifiers = resolved.get("modifiers", {})
    control = gold.get("control", {})
    ambiguity = resolved.get("ambiguity_state", {})
    return any(
        (
            task.get("shape") != "single_question",
            task.get("complexity") in {"compound", "complex"},
            bool(modifiers.get("follow_up")),
            bool(modifiers.get("ask_source")),
            bool(modifiers.get("challenge")),
            bool(ambiguity.get("clarify_hint")),
            control.get("route") in {"direct", "reject"},
            control.get("mode") == "clarify",
        )
    )


def review_reasons_for_v2(row: dict[str, Any]) -> list[str]:
    gold = row.get("gold", row)
    resolved = gold.get("resolved", {})
    task = resolved.get("task", {})
    modifiers = resolved.get("modifiers", {})
    control = gold.get("control", {})
    ambiguity = resolved.get("ambiguity_state", {})
    reasons: list[str] = []
    if task.get("shape") != "single_question":
        reasons.append("task_shape_non_single")
    if task.get("complexity") in {"compound", "complex"}:
        reasons.append(f"task_complexity_{task.get('complexity')}")
    for key in ("follow_up", "ask_source", "challenge"):
        if modifiers.get(key):
            reasons.append(f"modifier_{key}")
    if ambiguity.get("clarify_hint"):
        reasons.append("ambiguity_clarify_hint")
    if control.get("route") in {"direct", "reject"}:
        reasons.append(f"control_route_{control.get('route')}")
    if control.get("mode") == "clarify":
        reasons.append("control_mode_clarify")
    return reasons


def _unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered
