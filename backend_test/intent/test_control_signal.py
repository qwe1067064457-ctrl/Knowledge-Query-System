from __future__ import annotations

from intent import build_control_signal
from intent.types import AmbiguityState, DecisionTrace, IntentModifiers, ResolvedIntent, ResolvedTask


def _resolved(
    *,
    main_intent: str = "qa",
    modifiers: IntentModifiers | None = None,
    task: ResolvedTask | None = None,
    context_dependency: str = "none",
    ambiguity_state: AmbiguityState | None = None,
) -> ResolvedIntent:
    return ResolvedIntent(
        main_intent=main_intent,
        modifiers=modifiers or IntentModifiers(),
        task=task or ResolvedTask(complexity="simple", shape="single_question"),
        context_dependency=context_dependency,
        ambiguity_state=ambiguity_state or AmbiguityState(),
        decision=DecisionTrace(strength="high", source="rule", reason="test"),
    )


def test_simple_qa_routes_to_rag_with_citation() -> None:
    signal = build_control_signal(_resolved())

    assert signal.route == "qa"
    assert signal.handling_mode == "normal"
    assert signal.mode == "normal"
    assert signal.capabilities == ("cite_sources",)
    assert signal.force_citation is True


def test_follow_up_qa_requires_rewrite() -> None:
    signal = build_control_signal(
        _resolved(modifiers=IntentModifiers(follow_up=True), context_dependency="history_reference")
    )

    assert signal.route == "qa"
    assert signal.capabilities == ("cite_sources", "use_context")
    assert signal.mode == "normal"


def test_challenge_forces_rag_challenge_mode() -> None:
    signal = build_control_signal(
        _resolved(modifiers=IntentModifiers(challenge=True, ask_source=True))
    )

    assert signal.route == "qa"
    assert signal.handling_mode == "challenge"
    assert signal.mode == "challenge"
    assert signal.capabilities == ("cite_sources", "use_context")
    assert signal.force_citation is True


def test_system_routes_to_direct_capability() -> None:
    signal = build_control_signal(_resolved(main_intent="system"))

    assert signal.route == "qa"
    assert signal.handling_mode == "scope_info"
    assert signal.mode == "capability"
    assert signal.capabilities == ()


def test_complex_qa_routes_to_agent() -> None:
    signal = build_control_signal(
        _resolved(task=ResolvedTask(complexity="complex", shape="mixed", topology="staged"))
    )

    assert signal.route == "orchestrated"
    assert signal.use_planner is True
    assert signal.decompose_query is False
    assert signal.planning_level == "full"


def test_complex_verify_uses_light_planning_without_explicit_planner() -> None:
    signal = build_control_signal(
        _resolved(task=ResolvedTask(complexity="complex", shape="verify", topology="single"))
    )

    assert signal.route == "orchestrated"
    assert signal.use_planner is False
    assert signal.planning_level == "light"


def test_complex_verify_with_clarification_flag_is_rescued_to_agent() -> None:
    signal = build_control_signal(
        _resolved(
            task=ResolvedTask(complexity="complex", shape="verify", topology="single"),
            ambiguity_state=AmbiguityState(
                clarify_hint=True,
                ambiguity_states=("history_dependent",),
                missing_context_types=("missing_history_target",),
            ),
        )
    )

    assert signal.route == "orchestrated"
    assert signal.mode == "normal"
    assert signal.use_planner is False
    assert signal.planning_level == "light"


def test_complex_summarize_stays_agent_without_planner() -> None:
    signal = build_control_signal(
        _resolved(task=ResolvedTask(complexity="complex", shape="summarize", topology="single"))
    )

    assert signal.route == "qa"
    assert signal.use_planner is False
    assert signal.planning_level == "none"


def test_compound_multi_question_routes_to_rag_with_decomposition() -> None:
    signal = build_control_signal(
        _resolved(
            task=ResolvedTask(
                complexity="compound",
                shape="multi_question",
                topology="parallel_queries",
            )
        )
    )

    assert signal.route == "qa"
    assert signal.decompose_query is True
    assert signal.use_planner is False


def test_unsupported_routes_to_reject() -> None:
    signal = build_control_signal(
        _resolved(main_intent="unsupported", modifiers=IntentModifiers(out_of_scope=True))
    )

    assert signal.route == "reject"
    assert signal.handling_mode == "unsupported"
    assert signal.mode == "clarify"


def test_clarify_keeps_qa_route_but_switches_handling_mode() -> None:
    signal = build_control_signal(
        _resolved(
            ambiguity_state=AmbiguityState(
                clarify_hint=True,
                ambiguity_states=("fact_missing",),
                missing_context_types=("missing_fact_bundle",),
            )
        )
    )

    assert signal.route == "qa"
    assert signal.handling_mode == "clarify"
    assert signal.capabilities == ("cite_sources",)
