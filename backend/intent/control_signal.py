from __future__ import annotations

from intent.types import ControlSignal, ControlTrace, HandlingMode, ResolvedIntent


def build_control_signal(
    resolved: ResolvedIntent,
    *,
    force_qa_citation: bool = True,
) -> ControlSignal:
    trace = _build_trace(resolved)
    handling_mode = _resolve_handling_mode(resolved)
    route = _resolve_route(resolved, handling_mode)
    capabilities = _build_capabilities(
        resolved,
        force_qa_citation=force_qa_citation,
        handling_mode=handling_mode,
    )

    return ControlSignal(route=route, handling_mode=handling_mode, capabilities=capabilities, trace=trace)


def _resolve_handling_mode(resolved: ResolvedIntent) -> HandlingMode:
    modifiers = resolved.modifiers
    if resolved.main_intent == "unsupported" or modifiers.out_of_scope:
        return "unsupported"
    if resolved.main_intent == "system" or modifiers.ask_capability:
        return "scope_info"
    if resolved.ambiguity_state.clarify_hint and not _should_rescue_complex_qa_route(resolved):
        return "clarify"
    if modifiers.challenge:
        return "challenge"
    return "normal"


def _resolve_route(resolved: ResolvedIntent, handling_mode: HandlingMode) -> str:
    if handling_mode == "unsupported":
        return "reject"
    if resolved.main_intent == "chat":
        return "chat"
    if _should_use_orchestrated_route(resolved):
        return "orchestrated"
    return "qa"


def _build_capabilities(
    resolved: ResolvedIntent,
    *,
    force_qa_citation: bool,
    handling_mode: HandlingMode,
) -> tuple[str, ...]:
    capabilities: list[str] = []
    if handling_mode in {"scope_info", "unsupported"}:
        return ()

    if force_qa_citation or resolved.modifiers.ask_source or handling_mode == "challenge":
        capabilities.append("cite_sources")

    if _should_use_context(resolved, handling_mode):
        capabilities.append("use_context")
    return tuple(capabilities)


def _build_trace(resolved: ResolvedIntent) -> ControlTrace:
    return ControlTrace(
        main_intent=resolved.main_intent,
        modifiers=resolved.modifiers,
        task_complexity=resolved.task.complexity,
        task_shape=resolved.task.shape,
        task_topology=resolved.task.topology,
        context_dependency=resolved.context_dependency,
        ambiguity_states=resolved.ambiguity_state.ambiguity_states,
        missing_context_types=resolved.ambiguity_state.missing_context_types,
        decision_strength=resolved.decision.strength,
        decision_source=resolved.decision.source,
        decision_reason=resolved.decision.reason,
    )


def _should_rescue_complex_qa_route(resolved: ResolvedIntent) -> bool:
    if resolved.main_intent != "qa" or not resolved.ambiguity_state.clarify_hint:
        return False
    task = resolved.task
    return task.complexity == "complex" and task.shape in {"verify", "compare", "mixed"}


def _should_use_orchestrated_route(resolved: ResolvedIntent) -> bool:
    if resolved.main_intent != "qa":
        return False
    task = resolved.task
    if task.topology == "staged":
        return True
    if task.complexity != "complex":
        return False
    return task.shape in {"compare", "mixed", "verify"}


def _should_use_context(resolved: ResolvedIntent, handling_mode: HandlingMode) -> bool:
    if handling_mode == "challenge":
        return True
    return resolved.context_dependency != "none" or resolved.modifiers.follow_up
