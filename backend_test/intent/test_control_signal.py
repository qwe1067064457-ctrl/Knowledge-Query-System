from __future__ import annotations

from intent import build_control_signal
from intent.types import DecisionTrace, IntentModifiers, ResolvedIntent, ResolvedTask


def _resolved(
    *,
    main_intent: str = "qa",
    modifiers: IntentModifiers | None = None,
    task: ResolvedTask | None = None,
    context_dependency: str = "none",
) -> ResolvedIntent:
    return ResolvedIntent(
        main_intent=main_intent,
        modifiers=modifiers or IntentModifiers(),
        task=task or ResolvedTask(complexity="simple", shape="single_question"),
        context_dependency=context_dependency,
        decision=DecisionTrace(strength="high", source="rule", reason="test"),
    )


def test_simple_qa_routes_to_rag_with_citation() -> None:
    signal = build_control_signal(_resolved())

    assert signal.route == "rag"
    assert signal.mode == "normal"
    assert signal.rewrite is False
    assert signal.force_citation is True


def test_follow_up_qa_requires_rewrite() -> None:
    signal = build_control_signal(
        _resolved(modifiers=IntentModifiers(follow_up=True), context_dependency="history_reference")
    )

    assert signal.route == "rag"
    assert signal.rewrite is True
    assert signal.mode == "normal"


def test_challenge_forces_rag_challenge_mode() -> None:
    signal = build_control_signal(
        _resolved(modifiers=IntentModifiers(challenge=True, ask_source=True))
    )

    assert signal.route == "rag"
    assert signal.mode == "challenge"
    assert signal.rewrite is True
    assert signal.force_citation is True


def test_system_routes_to_direct_capability() -> None:
    signal = build_control_signal(_resolved(main_intent="system"))

    assert signal.route == "direct"
    assert signal.mode == "capability"


def test_complex_qa_routes_to_agent() -> None:
    signal = build_control_signal(
        _resolved(task=ResolvedTask(complexity="complex", shape="mixed", topology="staged"))
    )

    assert signal.route == "agent"
    assert signal.use_planner is True
    assert signal.decompose_query is False
    assert signal.planning_level == "full"


def test_complex_verify_uses_light_planning_without_explicit_planner() -> None:
    signal = build_control_signal(
        _resolved(task=ResolvedTask(complexity="complex", shape="verify", topology="single"))
    )

    assert signal.route == "agent"
    assert signal.use_planner is False
    assert signal.planning_level == "light"


def test_complex_verify_with_clarification_flag_is_rescued_to_agent() -> None:
    signal = build_control_signal(
        _resolved(
            modifiers=IntentModifiers(needs_clarification=True),
            task=ResolvedTask(complexity="complex", shape="verify", topology="single"),
        )
    )

    assert signal.route == "agent"
    assert signal.mode == "normal"
    assert signal.use_planner is False
    assert signal.planning_level == "light"


def test_complex_summarize_stays_agent_without_planner() -> None:
    signal = build_control_signal(
        _resolved(task=ResolvedTask(complexity="complex", shape="summarize", topology="single"))
    )

    assert signal.route == "agent"
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

    assert signal.route == "rag"
    assert signal.decompose_query is True
    assert signal.use_planner is False


def test_unsupported_routes_to_reject() -> None:
    signal = build_control_signal(
        _resolved(main_intent="unsupported", modifiers=IntentModifiers(out_of_scope=True))
    )

    assert signal.route == "reject"
    assert signal.mode == "clarify"
